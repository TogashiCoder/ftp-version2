from functions.functions_FTP import *
from config.config_path_variables import *
from functions.functions_check_ready_files import *
from config.temporary_data_list import current_dataFiles

key_FOURNISSEURS = ["FOURNISSEUR_A", "FOURNISSEUR_B"] #, ...]
key_PLATFORMS = ["PLATFORM_A", "PLATFORM_B"] #, ...]

F_data_ftp = create_ftp_config(key_FOURNISSEURS)
P_data_ftp = create_ftp_config(key_PLATFORMS)

print('\n ---',  F_data_ftp)
print('\n ---',  P_data_ftp)

"""
    keys: ["FOURNISSEUR_A", "FOURNISSEUR_B", ...]     # Same Same for Platforms

    return:  {'FOURNISSEUR_A': {'host': 'ftp.fournisseur-a.com', 'user': 'user_a', 'password': 'pass_a'}, 
              'FOURNISSEUR_B': {'host': 'ftp.fournisseur-b.com', 'user': 'user_b', 'password': 'pass_b'}, 
              ...}                       
"""


os.makedirs('test_output', exist_ok=True)
downloaded_files_F = download_files_from_all_servers(F_data_ftp, 'test_output')   # output_dir: fichiers_fournisseurs ou fichiers_platforms
downloaded_files_P = download_files_from_all_servers(P_data_ftp, 'test_output')  

print('downloaded_files_F = ', downloaded_files_F)
print('downloaded_files_P = ', downloaded_files_P)

'''
list_fichiers ==> dict('FOURNISSEUR_A': chemin fichierA , 
                       'FOURNISSEUR_B': chemin fichierB,... )
'''


# ==========================================================================
#               Read ENV end get All "Fournisseurs"/ "Platforms"
# ==========================================================================
# Remove any remaining references or comments about .env-based FTP config. Ensure all FTP access is YAML-based only.

fournis, platf = separer_fournisseurs_et_plateformes(data_env)
print('fournis: ', fournis)
print('platf: ', platf)
'''
    return: 
        liste_fournisseurs = ['FOURNISSEUR_A', 'FOURNISSEUR_B', ...]
        liste_plateformes = ['PLATFORM_A', 'PLATFORM_B', ...]
'''

# ==========================================================================


# ==========================================================================
#                               Check with Local Data
# ==========================================================================

downloaded_files_F, downloaded_files_P = current_dataFiles()

# ==========================================================================
#        Remove Fournisseurs/ Platforms with no column identification
# ==========================================================================

'''
input : list_fichiers ==> dict('FOURNISSEUR_A': chemin fichierA , 
                               'FOURNISSEUR_B': chemin fichierB,... )
'''
keep_fournisseurs = keep_data_with_header_specified(downloaded_files_F)
keep_platforms = keep_data_with_header_specified(downloaded_files_P)
'''
Returns:
        Dict avec fournisseurs valides et info associée:
        { fournisseur: {
              'chemin_fichier': str,
              YAML_REFERENCE_NAME: str,
              YAML_QUANTITY_NAME: str
          }, ...
        }
'''


fournisseurs_valides = verifier_fichiers_existent(keep_fournisseurs)
platforms_valides = verifier_fichiers_existent(keep_platforms)

print('fournisseurs_valides', fournisseurs_valides)
print('platforms_valides', platforms_valides)
