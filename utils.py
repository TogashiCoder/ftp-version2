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
        return {}
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data is None or data == []:
                return {}
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
def save_file(file_name: str, df: pd.DataFrame, encoding: str = 'utf-8', sep: str= ',', force_excel: bool = False) -> pd.DataFrame:
    try:
        ext = Path(file_name).suffix.lower()
        # Always use CSV for intermediate/verification saves unless force_excel is True
        if ext in {'.csv', '.txt'} or (ext in {'.xls', '.xlsx'} and not force_excel):
            # If .xls/.xlsx but not forced, save as .csv instead and log a warning
            if ext in {'.xls', '.xlsx'} and not force_excel:
                csv_file_name = str(Path(file_name).with_suffix('.csv'))
                logger.warning(f"Requested Excel save for {file_name}, but force_excel is False. Saving as CSV: {csv_file_name}")
                file_name = csv_file_name
            # Ensure sep is a valid 1-character string
            if sep is None or not isinstance(sep, str) or len(sep) != 1:
                sep = ','
            df.to_csv(file_name, encoding=encoding, sep=sep, index=False)
        elif ext in {'.xls', '.xlsx'} and force_excel:
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


def robust_read_csv(file_path, usecols=None, header='infer', encodings=None, separators=None):
    if encodings is None:
        encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin1', 'iso-8859-1']
    if separators is None:
        separators = [',', ';', '|', '\t', ' ']
    # Try chardet first
    with open(file_path, 'rb') as f:
        raw = f.read(100000)
        guess = chardet.detect(raw)['encoding']
        if guess and guess not in encodings:
            encodings = [guess] + encodings
    for encoding in encodings:
        for sep in separators:
            try:
                df = pd.read_csv(file_path, encoding=encoding, sep=sep, usecols=usecols, header=header)
                if df is not None and df.shape[1] >= 2:
                    return df, encoding, sep
            except Exception as e:
                logger.warning(f"Attempt to read with encoding {encoding}, separator {sep} failed: {e}")
    raise ValueError(f"Could not read {file_path} with tried encodings: {encodings}")


def read_csv_file_checking_encodings_sep(
    file_path: str,
    usecols=None,
    yaml_encoding_sep_path: Path = Path(YAML_ENCODING_SEP_FILE_PATH),
    header='infer'
    ) -> tuple[pd.DataFrame, str, str]:
    """
    Reads a CSV file, trying different encodings and separators. Accepts header argument for pandas.
    """
    yaml_info = read_yaml_file(yaml_encoding_sep_path)
    encodings, separators = yaml_info['encodings'], yaml_info['separators']
    # Use robust_read_csv for better detection
    return robust_read_csv(file_path, usecols=usecols, header=header, encodings=encodings, separators=separators)


# ------------------------------------------------------------------------------
#                   Open Files of differents formats
# ------------------------------------------------------------------------------
def read_dataset_file(file_name: str, usecols=None, header='infer') -> dict:
    """
    Reads a dataset file with optional usecols and header arguments.
    header: 'infer' (default) for files with header, None for files without header.
    """
    logger.info(f"📥 Tentative de lecture du fichier : {file_name}  ...")

    try:
        ext = Path(file_name).suffix.lower()
        if ext in {'.csv', '.txt'}:
            df,  encoding, sep = read_csv_file_checking_encodings_sep(file_name, usecols=usecols, header=header)
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
    """
    Convert stock value to integer:
    - '>10' -> 10
    - '<10' -> 10
    - 'AVAILABLE' -> 100 (or adjust as needed)
    - 'N/A', 'NA', 'NONE', '' -> 0
    - numeric strings -> int
    - float -> int
    - NaN/None -> 0
    - fallback: 0
    """
    import pandas as pd
    if pd.isna(value):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    value_str = str(value).strip().upper()
    if value_str in ["N/A", "NA", "NONE", ""]:
        return 0
    if value_str == "AVAILABLE":
        return 100  # or adjust as needed
    if value_str.startswith(">"):
        try:
            return int(value_str[1:])
        except Exception:
            return 0
    if value_str.startswith("<"):
        try:
            return int(value_str[1:])
        except Exception:
            return 0
    # Try to parse as integer
    try:
        return int(float(value_str))
    except Exception:
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
    """
    Loads header mappings from YAML. Supports both old (list) and new (dict with no_header/columns/multi_file) formats.
    Returns a dict: {entity: {'no_header': bool, 'multi_file': bool, 'columns': list}}
    """
    path = get_header_mappings_path()
    data = read_yaml_file(path)
    result = {}
    for entity, value in data.items():
        if isinstance(value, dict):
            no_header = value.get('no_header', False)
            multi_file = value.get('multi_file', False)
            columns = value.get('columns', [])
        else:
            no_header = False
            multi_file = False
            columns = value
        result[entity] = {'no_header': no_header, 'multi_file': multi_file, 'columns': columns}
    return result


def get_entity_mappings(entity):
    """
    Returns (columns, no_header, multi_file) for the given entity.
    If not found, returns ([], False, False).
    """
    mappings_dict = load_header_mappings()
    entry = mappings_dict.get(entity, {})
    if isinstance(entry, dict):
        return entry.get('columns', []), entry.get('no_header', False), entry.get('multi_file', False)
    else:
        return entry, False, False


def set_entity_mappings(entity, mapping_data):
    """
    Save the mapping for an entity.
    mapping_data can be:
      - a list of mappings (old format)
      - a dict with keys: columns (list), no_header (bool), multi_file (bool) (new format)
    """
    mappings = load_header_mappings()
    if isinstance(mapping_data, dict):
        # New format
        mappings[entity] = mapping_data
    else:
        # Old format (list)
        mappings[entity] = [m for m in mapping_data if m.get('target') in ALLOWED_TARGETS]
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

def save_header_mappings(mappings):
    """
    Save the header mappings to the YAML file.
    """
    path = get_header_mappings_path()
    import yaml
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(mappings, f, allow_unicode=True)
