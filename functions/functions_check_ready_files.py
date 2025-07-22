import os

from utils import *
from ftplib import FTP
from dotenv import dotenv_values
from functions.functions_FTP import *
from config.logging_config import logger
from config.config_path_variables import *
from utils import get_entity_mappings, YAML_REFERENCE_NAME, YAML_QUANTITY_NAME

# ----------------------------------------------------------------------
#            Lire les info de l'FTP stockées en fichier .env
# ----------------------------------------------------------------------
# Remove get_info_ftp_env and separer_fournisseurs_et_plateformes


# ------------------------------------------------------------------------------
#          Only file that column Ref & Qte are identified in yaml file
# ------------------------------------------------------------------------------
def keep_data_with_header_specified(list_fichiers):
    '''
    list_fichiers ==> dict('FOURNISSEUR_A': chemin fichierA , 'FOURNISSEUR_B': chemin fichierB,... )
    Returns:
        Dict avec fournisseurs valides et info associée:
        { fournisseur: {
              'chemin_fichier': str,
              YAML_REFERENCE_NAME: str,
              YAML_QUANTITY_NAME: str,
              'no_header': bool
          }, ...
        }
    '''
    items_valides = {}
    for item, chemin in list_fichiers.items():
        mappings, no_header = get_entity_mappings(item)
        nom_ref = next((m['source'] for m in mappings if m['target'] == YAML_REFERENCE_NAME), None)
        qte_stock = next((m['source'] for m in mappings if m['target'] == YAML_QUANTITY_NAME), None)
        if not nom_ref or not qte_stock:
            logger.error(f"-- ⚠️ --  {item} mapping missing nom_reference or quantite_stock")
            continue
        items_valides[item] = {
            'chemin_fichier': chemin,
            YAML_REFERENCE_NAME: nom_ref,
            YAML_QUANTITY_NAME: qte_stock,
            'no_header': no_header
        }
    return items_valides


# ------------------------------------------------------------------------------
#                       Si les fichiers existent vraiment
# ------------------------------------------------------------------------------
def verifier_fichiers_existent(list_files):
    item_valides = {}
    
    for item_file, infos in list_files.items():
        chemin = infos.get("chemin_fichier")
        if chemin and os.path.isfile(chemin):
            item_valides[item_file] = infos
        else:
            logger.error(f"-- ⚠️ --  Fichier introuvable pour {item_file} → '{chemin}' → supprimé.")
    
    return item_valides


def check_ready_files(title_files, downloaded_files, report_gen=None):
    logger.info(f'------------ Vérifiez si tous les fichiers {title_files} sont prêts--------------')
    files_with_header = keep_data_with_header_specified(downloaded_files)
    files_valides = verifier_fichiers_existent(files_with_header)
    if len(files_valides) > 0:
        logger.info(f'{len(files_valides)} fichiers sont prêts')
    else:
        logger.info(f'Aucun fichier trouvé')
        if report_gen:
            report_gen.add_warning(f"Aucun fichier trouvé pour {title_files}")
    # Log missing columns or files
    for key, data in files_with_header.items():
        if key not in files_valides:
            if report_gen:
                report_gen.add_warning(f"Fichier manquant ou colonnes non conformes: {key}")
    logger.info('---------------------------------------------------------------')
    return files_valides
