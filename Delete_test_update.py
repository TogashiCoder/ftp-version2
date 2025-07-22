from functions.functions_update import *

fichiers_fournisseurs, fichiers_platforms = current_dataFiles()

            # ---------------------- Loding Data via FTP ---------------------
           
fournisseurs_files_valides = check_ready_files(title_files='Fournisseurs', downloaded_files=fichiers_fournisseurs)
platforms_files_valides = check_ready_files(title_files='Plateformes', downloaded_files=fichiers_platforms)

#data_fournisseurs = read_all_fournisseurs(fournisseurs_files_valides)
#print("--------- data_fournisseurs   ", data_fournisseurs)

            # ------------------- Mettre A Jour le stock ---------------------
is_store_updated = mettre_a_jour_Stock(platforms_files_valides, fournisseurs_files_valides)
