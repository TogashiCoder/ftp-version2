import io
import sys
import time 
import logging
from pathlib import Path
from datetime import datetime
from config.config_path_variables import LOG_FOLDER
# ------------------------------------------------------------------------------
#                  Delete the Log files created '1' day before 
# ------------------------------------------------------------------------------
def delete_old_logs(log_dir: Path, max_age_days: int = 1):
    """Supprime les fichiers logs plus vieux que `max_age_days`."""
    now = time.time()
    max_age_seconds = max_age_days * 86400  # 86400 secondes = 1 jour

    for file in log_dir.glob("*.log"):
        if file.is_file():
            file_age = now - file.stat().st_mtime  # dernière modification
            if file_age > max_age_seconds:
                try:
                    file.unlink()
                    print(f"-- 🗑️ -- Ancien log supprimé : {file.name}")
                except Exception as e:
                    print(f"-- ❌ -- Erreur suppression log {file.name} : {e}")


# Forcer stdout à UTF-8 (pour éviter l'erreur UnicodeEncodeError sur Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Logging format
LOGGING_FORMAT = '[%(asctime)s]: %(levelname)s: %(module)s: %(message)s.'

# Log directory and file setup
LOG_FILE = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}_running_logs.log"
LOG_FILEPATH = LOG_FOLDER / LOG_FILE

# Create log directory if it does not exist
LOG_FOLDER.mkdir(parents=True, exist_ok=True)

# Supprimer les logs anciens (>1 jour)
delete_old_logs(LOG_FOLDER, max_age_days=1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOGGING_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILEPATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Logger name
LOGGER_NAME = 'MAJ_Fournisseurs_Plateforms'
logger = logging.getLogger(LOGGER_NAME)

