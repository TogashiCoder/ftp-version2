import os

from utils import *
from ftplib import FTP
from utils import load_fournisseurs_config, load_plateformes_config
from config.logging_config import logger
from config.config_path_variables import *
from functions.functions_check_ready_files import *
from utils import get_entity_mappings

# ------------------------------------------------------------------------------
#                           FTP Configuration
# ------------------------------------------------------------------------------
def create_ftp_config(keys, is_fournisseur=True):
    """
    keys: ["FOURNISSEUR_A", ...] or ["PLATFORM_A", ...]
    is_fournisseur: True for suppliers, False for platforms
    """
    config = {}
    all_creds = load_fournisseurs_config() if is_fournisseur else load_plateformes_config()
    for key in keys:
        creds = all_creds.get(key, {})
        host = creds.get('host')
        user = creds.get('username')
        password = creds.get('password')
        if not all([host, user, password]):
            logger.error(f'-- ❌ --  FTP config missing for {key}')
            raise ValueError(f"FTP config missing for {key}")
        config[key] = {
            "host": host,
            "user": user,
            "password": password
        }
    return config


# ------------------------------------------------------------------------------
#                           Download File via FTP
# ------------------------------------------------------------------------------
def download_file_from_ftp(ftp, remote_file, local_file):
    """
    Charger le fichier du serveur FTP ==> puis créer une copie localement
    """
    try:
        with open(local_file, "wb") as local_f:
            ftp.retrbinary("RETR " + remote_file, local_f.write)
        logger.info(f" -- ✅ --  Téléchargement terminé : {remote_file}")
        return True

    except Exception as e:
        logger.error(f"-- ❌ --  Error de téléchargement: {remote_file}: {e}")
        return False
    

# ------------------------------------------------------------------------------
#                 Fonction pour télécharger tous les fichiers FTP
# ------------------------------------------------------------------------------
def download_files_from_all_servers(ftp_servers, output_dir):    
    '''
    Args: 
        ftp_servers:
            {'FOURNISSEUR_A': {'host': 'ftp.fournisseur-a.com', 'user': 'user_a', 'password': 'pass_a'}, 
              'FOURNISSEUR_B': {'host': 'ftp.fournisseur-b.com', 'user': 'user_b', 'password': 'pass_b'}, 
              ...}
              & Same same for Platforms

        output_dir: fichiers_fournisseurs ou fichiers_platforms
    return: 
        list_fichiers ==> dict('FOURNISSEUR_A': chemin fichierA , 
                               'FOURNISSEUR_B': chemin fichierB,... )

    '''
    
    os.makedirs(output_dir, exist_ok=True)

    downloaded_files = {}

    for name, config in ftp_servers.items():      # sachant que: create_ftp_config <==> FTP_SERVERS_FOURNISSEURS = {"FOURNISSEUR_A": {"host": "ftp_host_FOURNISSEUR_A", "user": os.getenv("FTP_USER_FOURNISSEUR_A"), "password": os.getenv("FTP_PASS_FOURNISSEUR_A")},...}
        try:
            ftp = FTP(config["host"])
            ftp.login(config["user"], config["password"])
            logger.info(f"-- ✅ --  Bien connecté à l'FTP de {name}")

            filenames = ftp.nlst()       # pour récupérer la liste des fichiers et répertoires dans le répertoire courant du serveur FTP
            ftp_file = next((f for f in filenames if f.endswith(('.csv', '.xls', '.xlsx', '.txt'))), None)    # retourn le premier fichier de ces extension

            if ftp_file:
                extension = os.path.splitext(ftp_file)[1]  # exemple : '.csv'
                local_path = os.path.join(output_dir, f"{name}-{extension}")
                success = download_file_from_ftp(ftp, ftp_file, local_path)
                if success:
                    downloaded_files[name] = local_path 
                logger.info(f" -- ✅ --  Téléchargement terminé pour {name}: {ftp_file} → {local_path}")

            else:
                logger.exception(f"-- ⚠️ --  Aucun fichier valide trouvé pour {name}")

            ftp.quit()

        except Exception as e:
            logger.error(f"-- ❌ --  Erreur connexion FTP pour {name} : {e}")

    return downloaded_files



# ------------------------------------------------------------------------------
#       Load all/few Fournisseurs/ platforms existed in env file             
# ------------------------------------------------------------------------------
def load_fournisseurs_ftp(list_fournisseurs, report_gen=None):
    f_data_ftp = create_ftp_config(list_fournisseurs, is_fournisseur=True)
    downloaded_files_F = {}
    for name, config in f_data_ftp.items():
        try:
            # Check if this supplier is multi_file
            _, _, multi_file = get_entity_mappings(name)
            ftp = FTP(config["host"])
            ftp.login(config["user"], config["password"])
            logger.info(f"-- ✅ --  Bien connecté à l'FTP de {name}")
            filenames = ftp.nlst()
            valid_files = [f for f in filenames if f.endswith((".csv", ".xls", ".xlsx", ".txt"))]
            if multi_file:
                local_paths = []
                for ftp_file in valid_files:
                    extension = os.path.splitext(ftp_file)[1]
                    local_path = os.path.join(DOSSIER_FOURNISSEURS, f"{name}-{ftp_file}")
                    success = download_file_from_ftp(ftp, ftp_file, local_path)
                    if success:
                        local_paths.append(local_path)
                        if report_gen:
                            report_gen.add_supplier_processed(name)
                            report_gen.add_file_result(local_path, success=True)
                    else:
                        if report_gen:
                            report_gen.add_file_result(local_path, success=False, error_msg=f"Échec du téléchargement pour {name}")
                if local_paths:
                    downloaded_files_F[name] = local_paths
                else:
                    logger.exception(f"-- ⚠️ --  Aucun fichier valide trouvé pour {name}")
                    if report_gen:
                        report_gen.add_file_result(f"Aucun fichier pour {name}", success=False, error_msg="Aucun fichier valide trouvé")
            else:
                ftp_file = next((f for f in valid_files), None)
                if ftp_file:
                    extension = os.path.splitext(ftp_file)[1]
                    local_path = os.path.join(DOSSIER_FOURNISSEURS, f"{name}-{extension}")
                    success = download_file_from_ftp(ftp, ftp_file, local_path)
                    if success:
                        downloaded_files_F[name] = local_path
                        if report_gen:
                            report_gen.add_supplier_processed(name)
                            report_gen.add_file_result(local_path, success=True)
                    else:
                        if report_gen:
                            report_gen.add_file_result(local_path, success=False, error_msg=f"Échec du téléchargement pour {name}")
                else:
                    logger.exception(f"-- ⚠️ --  Aucun fichier valide trouvé pour {name}")
                    if report_gen:
                        report_gen.add_file_result(f"Aucun fichier pour {name}", success=False, error_msg="Aucun fichier valide trouvé")
            ftp.quit()
        except Exception as e:
            logger.error(f"-- ❌ --  Erreur connexion FTP pour {name} : {e}")
            if report_gen:
                report_gen.add_file_result(f"FTP {name}", success=False, error_msg=str(e))
                report_gen.add_error(f"Erreur FTP fournisseur {name}: {e}")
    return downloaded_files_F


def load_platforms_ftp(list_platforms, report_gen=None):
    p_data_ftp = create_ftp_config(list_platforms, is_fournisseur=False)
    downloaded_files_P = {}
    for name, config in p_data_ftp.items():
        try:
            ftp = FTP(config["host"])
            ftp.login(config["user"], config["password"])
            logger.info(f"-- ✅ --  Bien connecté à l'FTP de {name}")
            filenames = ftp.nlst()
            ftp_file = next((f for f in filenames if f.endswith((".csv", ".xls", ".xlsx", ".txt"))), None)
            if ftp_file:
                extension = os.path.splitext(ftp_file)[1]
                local_path = os.path.join(DOSSIER_PLATFORMS, f"{name}-{extension}")
                success = download_file_from_ftp(ftp, ftp_file, local_path)
                if success:
                    downloaded_files_P[name] = local_path
                    if report_gen:
                        report_gen.add_platform_processed(name)
                        report_gen.add_file_result(local_path, success=True)
                else:
                    if report_gen:
                        report_gen.add_file_result(local_path, success=False, error_msg=f"Échec du téléchargement pour {name}")
            else:
                logger.exception(f"-- ⚠️ --  Aucun fichier valide trouvé pour {name}")
                if report_gen:
                    report_gen.add_file_result(f"Aucun fichier pour {name}", success=False, error_msg="Aucun fichier valide trouvé")
            ftp.quit()
        except Exception as e:
            logger.error(f"-- ❌ --  Erreur connexion FTP pour {name} : {e}")
            if report_gen:
                report_gen.add_file_result(f"FTP {name}", success=False, error_msg=str(e))
                report_gen.add_error(f"Erreur FTP plateforme {name}: {e}")
    return downloaded_files_P


# ------------------------------------------------------------------------------
#         Upload updated marketplace files to their respective FTP servers
# ------------------------------------------------------------------------------
def find_latest_file_for_platform(platform_dir, platform_name):
    """
    Helper to find the latest file for a platform. Prefer <PLATFORM_NAME>-latest.csv, else pick the most recent timestamped file.
    """
    import glob
    import os
    from pathlib import Path
    latest_file = platform_dir / f"{platform_name}-latest.csv"
    if latest_file.exists():
        return latest_file
    # Fallback: find most recent timestamped file
    files = list(platform_dir.glob(f"{platform_name}-*.csv"))
    files = [f for f in files if '-latest' not in f.name]
    if files:
        return max(files, key=lambda f: f.stat().st_mtime)
    return None


def upload_updated_files_to_marketplace(dry_run=False):
    """
    Uploads the <PLATFORM_NAME>-latest.csv file for each platform in UPDATED_FILES/fichiers_platforms/<PLATFORM_NAME>/ to its FTP server.
    If dry_run is True, only log actions without uploading.
    """
    import time
    from ftplib import error_perm
    from dotenv import load_dotenv
    load_dotenv()

    upload_root = UPDATED_FILES_PATH
    if not upload_root.exists() or not upload_root.is_dir():
        logger.error(f"[ERROR]: Upload directory {upload_root} does not exist or is not a directory.")
        return

    plateformes_creds = load_plateformes_config()
    for platform_dir in upload_root.iterdir():
        if not platform_dir.is_dir():
            continue
        platform_name = platform_dir.name
        file_path = find_latest_file_for_platform(platform_dir, platform_name)
        if not file_path or not file_path.exists():
            logger.warning(f"[WARNING]: No latest file found for {platform_name} in {platform_dir}. Skipping upload.")
            continue
        creds = plateformes_creds.get(platform_name, {})
        host = creds.get('host')
        user = creds.get('username')
        password = creds.get('password')
        if not all([host, user, password]):
            logger.error(f"[ERROR]: FTP credentials missing for {platform_name}. Skipping upload for {file_path.name}.")
            continue
        logger.info(f"[INFO]: Preparing to upload {file_path.name} for {platform_name} to FTP.")
        if dry_run:
            logger.info(f"[DRY RUN]: Would upload {file_path} to FTP for {platform_name}.")
            continue
        success = False
        for attempt in range(1, 4):  # 3 retries
            try:
                with FTP(host) as ftp:  # type: ignore
                    ftp.login(user, password)  # type: ignore
                    logger.info(f"[INFO]: Connected to FTP for {platform_name} (attempt {attempt}).")
                    with open(file_path, "rb") as f:
                        ftp.storbinary(f"STOR {file_path.name}", f)
                    logger.info(f"[INFO]: Uploaded updated file for {platform_name} to FTP successfully.")
                    success = True
                    break
            except Exception as e:
                logger.error(f"[ERROR]: Failed to upload file {file_path.name} to FTP for {platform_name} (attempt {attempt}): {e}")
                time.sleep(2)  # Wait before retry
        if not success and not dry_run:
            logger.error(f"[ERROR]: Failed to upload file {file_path.name} to FTP for {platform_name} after 3 attempts.")

