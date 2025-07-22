import os
import re
import sys
import yaml
import pandas as pd
import smtplib
import chardet
import socket
from ftplib import FTP

from pathlib import Path
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.logging_config import logger

from config.config_path_variables import (
    YAML_ENCODING_SEP_FILE_PATH, YAML_REFERENCE_NAME, YAML_QUANTITY_NAME,
    CONFIG
)

# Charger les variables du fichier .env
load_dotenv()


# ------------------------------------------------------------------------------
#           Envoi d'une notification par email (Success / Failure)
# ------------------------------------------------------------------------------
def send_email_notification(subject: str, body: str, to_emails: list[str])-> None:
    from_email = os.getenv("EMAIL_ADDRESS") 
    password = os.getenv("EMAIL_PASSWORD")
    
    if not from_email or not password:
        logger.error("-- ❌ --  Email ou mot de passe non trouvés!")
        return  

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_emails 
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        # with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        # no need server.starttls() delete it
        with smtplib.SMTP("smtp.office365.com", 587) as server:
            server.starttls()
            server.login(from_email, password)
            server.send_message(msg)
        logger.info("📧 Email envoyé avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email : {e}")


def load_yaml_config(file_path):
    """Charge un fichier de configuration YAML."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Fichier de configuration introuvable : {file_path}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la lecture de {file_path}: {e}")
        return None

def save_yaml_config(data, file_path):
    """Sauvegarde les données dans un fichier de configuration YAML."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, allow_unicode=True)
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de {file_path}: {e}")
        return False

def send_test_email(smtp_user, smtp_password, recipients):
    """Sends a simple test email to a list of recipients."""
    
    if '@gmail.com' in smtp_user:
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
    elif any(domain in smtp_user for domain in ['@outlook.com', '@hotmail.com', '@office365.com']):
        smtp_server = 'smtp.office365.com'
        smtp_port = 587
    else:
        return False, "Fournisseur de messagerie non pris en charge. Utilisez Gmail, Outlook, ou Office365."

    subject = "Email de Test - FTP Inventory Pipeline"
    body = "Ceci est un email de test pour vérifier vos paramètres de notification."

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info(f"Email de test envoyé avec succès à {', '.join(recipients)}.")
        return True, "Email de test envoyé avec succès !"
    except smtplib.SMTPAuthenticationError:
        logger.error("Erreur d'authentification SMTP. Vérifiez l'utilisateur et le mot de passe.")
        return False, "Erreur d'authentification. Vérifiez votre email et mot de passe. Si vous utilisez Gmail, vous pourriez avoir besoin d'un 'mot de passe d'application'."
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email de test : {e}")
        return False, f"Erreur inattendue : {e}"

# ------------------------------------------------------------------------------
#                         Lecture d'un fichier YAML
# ------------------------------------------------------------------------------
def read_yaml_file(yaml_path: Path) -> dict:
    if not yaml_path.is_file():
        logger.error(f"-- ❌ --  Fichier introuvable : {yaml_path}")
        raise FileNotFoundError(f"Fichier introuvable : {yaml_path}")

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                logger.error("-- ❌ --  Le contenu YAML doit être un dictionnaire.")
                raise ValueError("Le fichier YAML ne contient pas un dictionnaire valide.")
            return data
    except yaml.YAMLError as e:
        logger.exception("-- ❌ --  Erreur de parsing YAML.")
        raise ValueError(f"Erreur de parsing YAML : {e}")
    except Exception as e:
        logger.exception("-- ❌ --  Erreur inattendue lors du chargement du fichier YAML.")
        raise ValueError("Erreur inattendue lors du chargement du fichier YAML.")


# ------------------------------------------------------------------------------
#                      Enregistrement d'un fichier DataFrame 
# ------------------------------------------------------------------------------
def save_file(file_name: str, df: pd.DataFrame, encoding: str = 'utf-8', sep: str= ',') -> pd.DataFrame:
    try:
        ext = Path(file_name).suffix.lower()
        if ext in {'.csv', '.txt'}:
            df.to_csv(file_name, encoding=encoding, sep=sep, index=False)
        elif ext in {'.xls', '.xlsx'}:
            df.to_excel(file_name, index=False)
        else:
            raise ValueError(f"Extension de fichier non supportée: {file_name}")
        
        logger.info(f"-- ✅ -- Fichier enregistré en : {file_name} - avec ({len(df)} lignes)")
        return df
    
    except Exception as e:
        logger.exception(f"-- ❌ -- Erreur lors de l'enregistrement de {file_name}: {e}")
        return pd.DataFrame()  # Retourne un DataFrame vide en cas d'erreur


# ------------------------------------------------------------------------
#                        Détection rapide de l'encodage
# ------------------------------------------------------------------------
def detect_encoding_fast(file_path: str, size_bytes: int = 2048) -> str:
    with open(file_path, 'rb') as f:
        raw_data = f.read(size_bytes)
        result = chardet.detect(raw_data)
    return result['encoding'] if result['encoding'] else 'utf-8'


# ------------------------------------------------------------------------
#               Vérification:  si le fichier n'a pas d'entête 
# ------------------------------------------------------------------------
def has_valid_header(df: pd.DataFrame) -> bool:
    col_names = list(df.columns)
    
    # Si les noms sont tous alphanumériques courts (ex: 'RAD', '000057'), suspect
    if all(isinstance(col, str) and (col.isupper() or col.isdigit() or col.strip().isnumeric()) for col in col_names):
        return False
    
    # Si tous les noms sont numériques ou Unnamed
    if all(str(col).startswith("Unnamed") or str(col).isdigit() for col in col_names):
        return False

    return True


# ------------------------------------------------------------------------
#     Lecture robuste de CSV avec test d'encodages/séparateurs & header
# ------------------------------------------------------------------------
def try_read_csv(file_path: str, sep: str, encoding: str, usecols=None) -> pd.DataFrame | None:
    try:
        temp_df = pd.read_csv(file_path, sep=sep, encoding=encoding, nrows=4)
        header_option = 0 if has_valid_header(temp_df) else None
        df = pd.read_csv(file_path, sep=sep, encoding=encoding, header=header_option, usecols=usecols)
        return df
    except Exception:
        return None


def read_csv_file_checking_encodings_sep(
    file_path: str,
    usecols=None,
    yaml_encoding_sep_path: Path = Path(YAML_ENCODING_SEP_FILE_PATH)
    ) -> tuple[pd.DataFrame, str, str]:
    
    yaml_info = read_yaml_file(yaml_encoding_sep_path)
    encodings, separators = yaml_info['encodings'], yaml_info['separators']

    # Test rapide avec chardet
    detected_encoding = detect_encoding_fast(file_path)

    for encoding in [detected_encoding] + encodings:
        for sep in separators:
            df = try_read_csv(file_path, sep, encoding, usecols)
            if df is not None and df.shape[1] >= 2:
                return df, encoding, sep

    logger.error("❌ Échec de lecture : aucun encodage ou séparateur ne fonctionne.")
    raise ValueError("Échec de lecture du fichier CSV.")


# ------------------------------------------------------------------------------
#                   Open Files of differents formats
# ------------------------------------------------------------------------------
def read_dataset_file(file_name: str, usecols=None) -> dict:
    logger.info(f"📥 Tentative de lecture du fichier : {file_name}  ...")

    try:
        ext = Path(file_name).suffix.lower()
        if ext in {'.csv', '.txt'}:
            df,  encoding, sep = read_csv_file_checking_encodings_sep(file_name, usecols=usecols, yaml_encoding_sep_path=YAML_ENCODING_SEP_FILE_PATH)
            logger.info(f"📄 Fichier lu : {file_name} -- avec ({len(df)} lignes)")
            return {'dataset':df, 'encoding':encoding, 'sep':sep}
        
        elif ext in {'.xls', '.xlsx'}:
            #df = pd.read_excel(file_name, usecols=usecols)
            temp_df = pd.read_excel(file_name,  nrows=4,  header=0)
            header_option = 0 if has_valid_header(temp_df) else None
            df = pd.read_excel(file_name, header=header_option, usecols=usecols)
            logger.info(f"📄 Fichier lu : {file_name} -- avec ({len(df)} lignes)")
            return {'dataset':df, 'encoding':'', 'sep':''}
       
        else:
            raise ValueError(f"Extension de fichier non supportée: {file_name}")
    except Exception as e:
        logger.error(f"-- ❌ --  Erreur lors de la lecture de {file_name}: {e}")
        return {'dataset':pd.DataFrame(), 'encoding':'', 'sep':''}  # Retourne un DataFrame vide en cas d'erreur


# ------------------------------------------------------------------------------
#                       Adapter les chemins pour .exe
# ------------------------------------------------------------------------------
def get_resource_path(relative_path: str) -> str:    # used for creating .exe (managing paths)
    try:
        # PyInstaller crée un dossier temporaire _MEIxxx
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ------------------------------------------------------------------------------
#          Remove >= from Stock & change 'AVAILABLE' by 3 & 'N/A', -1 by 0
# ------------------------------------------------------------------------------
def process_stock_value(value):
    """Nettoie et convertit une valeur de stock en entier.
    Gère les valeurs textuelles et numériques de manière intelligente."""

    # Convertir en chaîne propre
    value = str(value).strip().upper()

    # Dictionnaire de correspondance pour les textes courants
    text_mappings = {
        "AVAILABLE": 3,
        "IN STOCK": 3,
        "EN STOCK": 3,
        "VERFÜGBAR": 3,
        "DISPONIBLE": 3,
        "YES": 1,
        "OUI": 1,
        "JA": 1,
        "Y": 1,
        "N/A": 0,
        "NONE": 0,
        "NO": 0,
        "NON": 0,
        "NEIN": 0,
        "N": 0,
        "DISCONTINUED": 0,
        "ÉPUISÉ": 0,
        "AUSVERKAUFT": 0,
        "OUT OF STOCK": 0,
        "RUPTURE": 0,
        "BACKORDER": 1,
        "PRE-ORDER": 1,
        "LIMITED": 2,
    }

    # Vérifier les correspondances textuelles
    for pattern, stock_value in text_mappings.items():
        if pattern in value:
            return stock_value

    # Supprimer les symboles ambigus
    value = re.sub(r"[<>~=±≃≅]", "", value)

    # Remplacer les virgules par des points (12,5 → 12.5)
    value = value.replace(",", ".")     

    # Gérer les valeurs négatives explicites        
    if value.startswith('-'):
        value = '0'
    
    # Gérer les ranges (e.g., "5-10" -> prendre la valeur minimale)
    if '-' in value:
        try:
            return int(float(value.split('-')[0].strip()))
        except ValueError:
            pass

    # Gérer les pourcentages
    if '%' in value:
        try:
            percent = float(value.replace('%', ''))
            return int(percent / 100 * 10)  # Scale 0-100% to 0-10
        except ValueError:
            pass
    
    # Essayer de convertir proprement float → int
    try:
        int_value = int(float(value))
        return max(int_value, 0)
    except ValueError:
        pass

    # En dernier recours : extraire tous les chiffres
    cleaned_value = re.sub(r"[^0-9]", "", value)
    if not cleaned_value:
        return 0

    try:
        int_value = int(cleaned_value)
        return max(int_value, 0)
    except ValueError:
        return 0


# ------------------------------------------------------------------------------
#         Remove spaces before/after '='  + avoid '' or "" in the env file
# ------------------------------------------------------------------------------
def clean_env_file(path_env):
    '''
    replace .env after cleaning
    '''
    print('path_env', path_env)
    with open(path_env, "r") as f:
        lines = f.readlines()

    cleaned_lines = []
    for line in lines:
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            cleaned_lines.append(f"{key}={value}\n")
        else:
            cleaned_lines.append(line)

    with open(path_env, "w") as f:
        f.writelines(cleaned_lines)


def load_fournisseurs_config():
    # First try current working directory
    current_dir = Path.cwd()
    path = current_dir / 'config' / 'fournisseurs_connexions.yaml'
    
    # If not found, try the directory containing this script
    if not path.exists():
        path = Path(__file__).resolve().parent / 'config' / 'fournisseurs_connexions.yaml'
    
    print(f"Loading fournisseurs config from: {path}")
    print(f"Path exists: {path.exists()}")
    
    if not path.exists():
        print("Fournisseurs config file not found!")
        return {}
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            print(f"Loaded {len(config)} fournisseurs")
            print(f"Fournisseurs: {list(config.keys())}")
            return config
    except Exception as e:
        print(f"Error loading fournisseurs config: {e}")
        return {}

def load_plateformes_config():
    # First try current working directory
    current_dir = Path.cwd()
    path = current_dir / 'config' / 'plateformes_connexions.yaml'
    
    # If not found, try the directory containing this script
    if not path.exists():
        path = Path(__file__).resolve().parent / 'config' / 'plateformes_connexions.yaml'
    
    print(f"Loading plateformes config from: {path}")
    print(f"Path exists: {path.exists()}")
    
    if not path.exists():
        print("Plateformes config file not found!")
        return {}
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            print(f"Loaded {len(config)} plateformes")
            print(f"Plateformes: {list(config.keys())}")
            return config
    except Exception as e:
        print(f"Error loading plateformes config: {e}")
        return {}

def get_valid_fournisseurs(timeout=5):
    """
    Tests FTP connections for all configured suppliers of type 'ftp' and returns only those with valid connections.
    Args:
        timeout (int): Connection timeout in seconds
    Returns:
        list: List of supplier names with valid FTP connections
    """
    valid = []
    invalid = []
    fournisseurs = load_fournisseurs_config()
    # Only keep those with type 'ftp'
    fournisseurs = {k: v for k, v in fournisseurs.items() if str(v.get('type', '')).lower() == 'ftp'}
    print(f"\nTesting FTP connections for {len(fournisseurs)} fournisseurs (type=ftp)...")
    for name, info in fournisseurs.items():
        try:
            with FTP() as ftp:
                ftp.connect(
                    host=info['host'],
                    port=int(info.get('port', 21)),
                    timeout=timeout
                )
                ftp.login(
                    user=info['username'],
                    passwd=info['password']
                )
                valid.append(name)
                print(f"✅ {name}: Connection successful")
        except Exception as e:
            invalid.append((name, str(e)))
            print(f"❌ {name}: Connection failed - {str(e)}")
            logger.warning(f"Fournisseur {name} FTP connection failed: {e}")
    if invalid:
        print("\nInvalid FTP connections:")
        for name, error in invalid:
            print(f"- {name}: {error}")
    print(f"\nValid FTP connections: {len(valid)}/{len(fournisseurs)}")
    return valid

def get_valid_platforms(timeout=5):
    """
    Tests FTP connections for all configured platforms of type 'ftp' and returns only those with valid connections.
    Args:
        timeout (int): Connection timeout in seconds
    Returns:
        list: List of platform names with valid FTP connections
    """
    valid = []
    invalid = []
    platforms = load_plateformes_config()
    # Only keep those with type 'ftp'
    platforms = {k: v for k, v in platforms.items() if str(v.get('type', '')).lower() == 'ftp'}
    print(f"\nTesting FTP connections for {len(platforms)} platforms (type=ftp)...")
    for name, info in platforms.items():
        try:
            with FTP() as ftp:
                ftp.connect(
                    host=info['host'],
                    port=int(info.get('port', 21)),
                    timeout=timeout
                )
                ftp.login(
                    user=info['username'],
                    passwd=info['password']
                )
                valid.append(name)
                print(f"✅ {name}: Connection successful")
        except Exception as e:
            invalid.append((name, str(e)))
            print(f"❌ {name}: Connection failed - {str(e)}")
            logger.warning(f"Platform {name} FTP connection failed: {e}")
    if invalid:
        print("\nInvalid FTP connections:")
        for name, error in invalid:
            print(f"- {name}: {error}")
    print(f"\nValid FTP connections: {len(valid)}/{len(platforms)}")
    return valid

import yaml
def get_header_mappings_path():
    # First try current working directory
    current_dir = Path.cwd()
    path = current_dir / 'config' / 'header_mappings.yaml'
    
    # If not found, try relative to this script
    if not path.exists():
        path = Path(__file__).resolve().parent.parent / 'config' / 'header_mappings.yaml'
    
    return path

HEADER_MAPPINGS_PATH = get_header_mappings_path()

ALLOWED_TARGETS = ['nom_reference', 'quantite_stock']

def load_header_mappings():
    print("\n=== DEBUG: load_header_mappings START ===")
    print(f"DEBUG: Looking for header mappings at: {HEADER_MAPPINGS_PATH}")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    print(f"DEBUG: File exists: {HEADER_MAPPINGS_PATH.exists()}")
    print(f"DEBUG: File is absolute path: {HEADER_MAPPINGS_PATH.is_absolute()}")
    print(f"DEBUG: Parent directory exists: {HEADER_MAPPINGS_PATH.parent.exists()}")
    
    if not HEADER_MAPPINGS_PATH.exists():
        print("DEBUG: header_mappings.yaml file not found!")
        return {}
        
    try:
        with open(HEADER_MAPPINGS_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"DEBUG: Raw file content (first 100 chars): {content[:100]}")
            data = yaml.safe_load(content) or {}
            print(f"DEBUG: Loaded mappings keys: {list(data.keys())}")
            return data
    except Exception as e:
        print(f"DEBUG: Error loading mappings: {str(e)}")
        return {}
    finally:
        print("=== DEBUG: load_header_mappings END ===\n")

def save_header_mappings(mappings):
    with open(HEADER_MAPPINGS_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(mappings, f, allow_unicode=True)

def get_entity_mappings(entity):
    print("\n=== DEBUG: get_entity_mappings START ===")
    print(f"DEBUG: Working directory: {os.getcwd()}")
    print(f"DEBUG: utils.py location: {__file__}")
    print(f"DEBUG: Mappings file location: {HEADER_MAPPINGS_PATH}")
    mappings = load_header_mappings()
    if not entity:
        print("DEBUG: Entity is empty!")
        return []
    print(f"DEBUG: Looking for mappings for entity: '{entity}'")
    print(f"DEBUG: Available mapping keys: {list(mappings.keys())}")
    print(f"DEBUG: Type of entity: {type(entity)}")
    print(f"DEBUG: Length of entity: {len(entity)}")
    print(f"DEBUG: Entity bytes: {entity.encode()}")
    result = mappings.get(entity, [])
    print(f"DEBUG: Found mappings: {result}")
    print("=== DEBUG: get_entity_mappings END ===\n")
    return result

def set_entity_mappings(entity, mapping_list):
    mappings = load_header_mappings()
    mappings[entity] = [m for m in mapping_list if m.get('target') in ALLOWED_TARGETS]
    save_header_mappings(mappings)

def delete_entity_mappings(entity):
    mappings = load_header_mappings()
    if entity in mappings:
        del mappings[entity]
        save_header_mappings(mappings)

def cleanup_orphan_mappings():
    mappings = load_header_mappings()
    fournisseurs = set(load_fournisseurs_config().keys())
    platforms = set(load_plateformes_config().keys())
    valid_entities = fournisseurs | platforms
    cleaned = {k: v for k, v in mappings.items() if k in valid_entities}
    if cleaned != mappings:
        save_header_mappings(cleaned)

# Helper to resolve column by mapping (index or name)
def get_column_by_mapping(df, mapping):
    if isinstance(mapping, int):
        return df.columns[mapping]
    if isinstance(mapping, str) and mapping.isdigit():
        idx = int(mapping)
        return df.columns[idx]
    return mapping
