import sys
from pathlib import Path
from dotenv import load_dotenv


if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys.executable).parent          # On est dans l'exécutable .exe
else:
    ROOT_DIR = Path(__file__).resolve().parents[1]      # On est dans main.py

# Charger les variables d'environnement (.env)
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

# Dossiers importants
LOG_FOLDER = ROOT_DIR / "logs"
CONFIG =  ROOT_DIR / "config"
IMG_SRC = ROOT_DIR / "img"
DOSSIER_FOURNISSEURS =  ROOT_DIR / "fichiers_fournisseurs"
DOSSIER_PLATFORMS =  ROOT_DIR / "fichiers_platforms"
UPDATED_FILES_PATH_RACINE = ROOT_DIR / "UPDATED_FILES"
UPDATED_FILES_PATH = ROOT_DIR / "UPDATED_FILES" / "fichiers_platforms"
VERIFIED_FILES_PATH = ROOT_DIR / "Verifier" 
BACKUP_LOCAL_PATH = ROOT_DIR / "backup"

# Fichiers YAML
HEADER_PLATFORMS_YAML = CONFIG / "header_platforms.yaml"
HEADER_FOURNISSEURS_YAML = CONFIG / "header_fournisseurs.yaml"
YAML_ENCODING_SEP_FILE_PATH = CONFIG / "config_encodings_separateurs.yaml"

# Constantes
YAML_REFERENCE_NAME = 'nom_reference'
YAML_QUANTITY_NAME = 'quantite_stock'
ID_PRODUCT = 'ID_Product'
QUANTITY = 'Quantity'

TO_EMAIL = "amal@gmail.com"