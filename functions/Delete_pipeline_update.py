from config.config_path_variables import HEADER_FOURNISSEURS_YAML, HEADER_PLATFORMS_YAML
from functions.functions_FTP import *
from functions.functions_update import *

# --------------------- All Fournisseurs / Platforms ----------------------
# Remove usage of get_all_fournisseurs_env and get_all_platforms_env

# ------------------ Few Checked Fournisseurs / Platforms -----------------
list_fournisseurs = ["FOURNISSEUR_A", "FOURNISSEUR_B"] #, ...]
list_platforms = ["PLATFORM_A", "PLATFORM_B"] #, ...]

# ---------------------- Load data From FTP to Local ----------------------


downloaded_files_F =  load_fournisseurs_ftp(list_fournisseurs)
                                    #  dict('FOURNISSEUR_A': chemin fichierA , 
                                    #       'FOURNISSEUR_B': chemin fichierB,... )

downloaded_files_P = load_platforms_ftp(list_platforms)


fournisseurs_files_valides = check_ready_files(title_files='Fournisseurs', downloaded_files=downloaded_files_F)
platforms_files_valides = check_ready_files(title_files='Plateformes', downloaded_files=downloaded_files_P)

