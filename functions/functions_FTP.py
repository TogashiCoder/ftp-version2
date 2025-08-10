import os

from utils import *
from ftplib import FTP
from utils import load_fournisseurs_config, load_plateformes_config
from config.logging_config import logger
from config.config_path_variables import *
from functions.functions_check_ready_files import *
from utils import get_entity_mappings, load_yaml_config

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
    # Clean old downloaded files (>5h) before fetching new ones
    try:
        os.makedirs(DOSSIER_FOURNISSEURS, exist_ok=True)
        delete_old_files(DOSSIER_FOURNISSEURS, max_age_hours=5, extensions=(".csv", ".xls", ".xlsx", ".txt"))
    except Exception as _cleanup_err:
        logger.warning(f"[WARNING]: Cleanup fournisseurs folder failed: {_cleanup_err}")
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
    # Clean old downloaded platform files (>5h)
    try:
        os.makedirs(DOSSIER_PLATFORMS, exist_ok=True)
        delete_old_files(DOSSIER_PLATFORMS, max_age_hours=5, extensions=(".csv", ".xls", ".xlsx", ".txt"))
    except Exception as _cleanup_err:
        logger.warning(f"[WARNING]: Cleanup platforms folder failed: {_cleanup_err}")
    p_data_ftp = create_ftp_config(list_platforms, is_fournisseur=False)
    downloaded_files_P = {}
    for name, config in p_data_ftp.items():
        try:
            ftp = FTP(config["host"])
            ftp.login(config["user"], config["password"])
            logger.info(f"-- ✅ --  Bien connecté à l'FTP de {name}")
            filenames = ftp.nlst()
            # Choose platform file with priority: canonical (not platform-prefixed and not -latest), then prefixed, then -latest, else any
            supported_exts = (".csv", ".xls", ".xlsx", ".txt")
            candidates = [f for f in filenames if f.lower().endswith(supported_exts)]
            canonical = [f for f in candidates if (not f.lower().startswith(f"{name.lower()}-")) and ("-latest" not in f.lower())]
            prefixed = [f for f in candidates if f.lower().startswith(f"{name.lower()}-") and ("-latest" not in f.lower())]
            latests = [f for f in candidates if f.lower().startswith(f"{name.lower()}-latest")]
            ftp_file = None
            if canonical:
                ftp_file = canonical[0]
            elif prefixed:
                ftp_file = prefixed[0]
            elif latests:
                ftp_file = latests[0]
            elif candidates:
                ftp_file = candidates[0]
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
                    logger.debug(f"[DEBUG]: Candidates on FTP for {name}: {candidates}")
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
    Helper to find the latest updated file for a platform.
    Prefer <PLATFORM_NAME>-latest.<ext> for ext in {csv,xlsx,xls,txt},
    else pick the most recent timestamped file across supported extensions.
    """
    supported_exts = ('.csv', '.xlsx', '.xls', '.txt')
    # Prefer latest by extension priority
    for ext in supported_exts:
        latest_path = platform_dir / f"{platform_name}-latest{ext}"
        if latest_path.exists():
            return latest_path
    # Fallback to most recent timestamped file across supported exts
    candidates = []
    for ext in supported_exts:
        candidates.extend([f for f in platform_dir.glob(f"{platform_name}-*{ext}") if '-latest' not in f.name])
    if candidates:
        return max(candidates, key=lambda f: f.stat().st_mtime)
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
    # Load optional S3 backup settings
    s3_settings = load_yaml_config(CONFIG / "aws_backup.yaml") or {}
    s3_enabled = bool(s3_settings.get("enabled", False))
    s3_bucket = s3_settings.get("bucket")
    s3_prefix = s3_settings.get("prefix", "backups/platforms")
    s3_region = s3_settings.get("region")
    s3_access_key = s3_settings.get("access_key_id")
    s3_secret_key = s3_settings.get("secret_access_key")
    s3_session_token = s3_settings.get("session_token")
    s3_endpoint_url = s3_settings.get("endpoint_url")
    s3_client = None
    if s3_enabled and s3_bucket:
        try:
            import boto3  # type: ignore
            client_kwargs = {}
            if s3_region:
                client_kwargs["region_name"] = s3_region
            if s3_access_key and s3_secret_key:
                client_kwargs["aws_access_key_id"] = s3_access_key
                client_kwargs["aws_secret_access_key"] = s3_secret_key
            if s3_session_token:
                client_kwargs["aws_session_token"] = s3_session_token
            if s3_endpoint_url:
                client_kwargs["endpoint_url"] = s3_endpoint_url
            s3_client = boto3.client("s3", **client_kwargs)
            logger.info(f"[INFO]: S3 backup enabled. Bucket='{s3_bucket}', Prefix='{s3_prefix}'")
        except Exception as e:
            logger.error(f"[ERROR]: Failed to initialize S3 client: {e}")
            s3_client = None
    
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
                    from datetime import datetime
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M')
                    # Prepare local backup directory under project
                    try:
                        local_backup_dir = BACKUP_LOCAL_PATH / timestamp / platform_name
                        local_backup_dir.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        logger.warning(f"[WARNING]: Could not create local backup dir: {e}")

                    # Determine existing remote files and back them up (any supported ext)
                    remote_candidates = []
                    backed_up_count = 0
                    try:
                        filenames = ftp.nlst()
                        supported_exts = ('.csv', '.xls', '.xlsx', '.txt')
                        remote_candidates = [f for f in filenames if f.lower().endswith(supported_exts)]
                        for fname in remote_candidates:
                            try:
                                from io import BytesIO
                                buf = BytesIO()
                                ftp.retrbinary(f"RETR {fname}", buf.write)
                                buf.seek(0)
                                # 1) Always save a local backup copy in project backup folder
                                try:
                                    local_copy_path = local_backup_dir / fname  # type: ignore
                                    with open(local_copy_path, 'wb') as lf:
                                        lf.write(buf.getvalue())
                                    backed_up_count += 1
                                    logger.info(f"[INFO]: Local backup saved: {local_copy_path}")
                                except Exception as e:
                                    logger.warning(f"[WARNING]: Could not save local backup for '{fname}': {e}")
                                # 2) Optional S3 backup
                                if s3_client is not None:
                                    s3_key = f"{s3_prefix}/{timestamp}/{platform_name}/{fname}"
                                    s3_client.put_object(Bucket=s3_bucket, Key=s3_key, Body=buf.getvalue())
                                    logger.info(f"[INFO]: Backed up remote file '{fname}' to s3://{s3_bucket}/{s3_key}")
                            except Exception as e:
                                logger.warning(f"[WARNING]: Failed to back up remote file '{fname}' for {platform_name}: {e}")
                    except Exception as e:
                        logger.warning(f"[WARNING]: Could not list remote files for {platform_name}: {e}")

                    # If there were remote files and none were backed up, do not overwrite
                    if len(remote_candidates) > 0 and backed_up_count == 0:
                        logger.error(f"[ERROR]: Backup verification failed for {platform_name}. Aborting upload.")
                        raise Exception("Backup verification failed")

                    # Choose the target remote filename to replace
                    upload_ext = file_path.suffix.lower()
                    target_remote_name = None
                    # Build categorized lists
                    latest_candidates = [f for f in remote_candidates if f.lower().startswith(f"{platform_name.lower()}-latest") and f.lower().endswith(upload_ext)]
                    prefix_candidates = [f for f in remote_candidates if f.lower().startswith(f"{platform_name.lower()}-") and f not in latest_candidates and f.lower().endswith(upload_ext)]
                    # Canonical: any supported file that is NOT '-latest' and NOT starting with platform prefix
                    canonical_candidates = [f for f in remote_candidates if (not f.lower().startswith(f"{platform_name.lower()}-")) and ("-latest" not in f.lower()) and f.lower().endswith(upload_ext)]

                    # Priority 1: canonical file (likely marketplace original)
                    if canonical_candidates:
                        target_remote_name = canonical_candidates[0]
                    # Priority 2: prefixed file without '-latest'
                    elif prefix_candidates:
                        target_remote_name = prefix_candidates[0]
                    # Priority 3: existing '-latest'
                    elif latest_candidates:
                        target_remote_name = latest_candidates[0]
                    # Priority 4: any supported file
                    elif remote_candidates:
                        target_remote_name = remote_candidates[0]
                    else:
                        # Default to our latest file name
                        target_remote_name = file_path.name

                    # Proceed with upload using temp + rename for atomic replace
                    logger.info(f"[INFO]: Connected to FTP for {platform_name} (attempt {attempt}).")
                    temp_name = f"{target_remote_name}.tmp"
                    with open(file_path, "rb") as f:
                        ftp.storbinary(f"STOR {temp_name}", f)
                    try:
                        ftp.rename(temp_name, target_remote_name)
                    except Exception as e:
                        logger.warning(f"[WARNING]: Atomic rename failed, attempting direct overwrite: {e}")
                        with open(file_path, "rb") as f:
                            ftp.storbinary(f"STOR {target_remote_name}", f)

                    logger.info(f"[INFO]: Uploaded and replaced file for {platform_name}: {target_remote_name}")

                    # Cleanup: remove other old remote files for this platform to avoid duplicates
                    try:
                        filenames = ftp.nlst()
                        for fname in filenames:
                            if fname == target_remote_name:
                                continue
                            lower_name = fname.lower()
                            # Remove '-latest' files and platform-prefixed variants
                            if (lower_name.startswith(f"{platform_name.lower()}-") or '-latest' in lower_name) and lower_name.endswith(supported_exts):
                                try:
                                    ftp.delete(fname)
                                    logger.info(f"[INFO]: Removed old remote file: {fname}")
                                except Exception as e:
                                    logger.warning(f"[WARNING]: Could not delete remote file '{fname}': {e}")
                    except Exception as e:
                        logger.warning(f"[WARNING]: Cleanup listing failed for {platform_name}: {e}")
                    success = True
                    break
            except Exception as e:
                logger.error(f"[ERROR]: Failed to upload file {file_path.name} to FTP for {platform_name} (attempt {attempt}): {e}")
                time.sleep(2)  # Wait before retry
        if not success and not dry_run:
            logger.error(f"[ERROR]: Failed to upload file {file_path.name} to FTP for {platform_name} after 3 attempts.")

