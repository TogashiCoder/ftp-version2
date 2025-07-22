from functions.functions_check_ready_files import *
from functions.functions_update import *

import pandas as pd
from utils import * 
fichiers_fournisseurs = {'FOURNISSEUR_H': './fichiers_fournisseurs/1210021_SBShop-Artikelstamm-Gekürzt_1747871859797.csv',
                         'FOURNISSEUR_D': './fichiers_fournisseurs/export (67)(Récupération automatique).csv',
                         'FOURNISSEUR_J': './fichiers_fournisseurs/rad_01.csv',
                         'FOURNISSEUR_K': './fichiers_fournisseurs/rad_02.csv',}
    
    
pret_fichiers_fournisseurs = keep_data_with_header_specified(fichiers_fournisseurs)
valide_fichiers_fournisseurs = verifier_fichiers_existent(pret_fichiers_fournisseurs)



def read_data_and_save_params(index, data_f):
    print('\n\n ===============================')
    chemin = data_f['chemin_fichier']
    # Get mapping and no_header flag
    mappings, no_header = get_entity_mappings(index)
    nom_ref = next((m['source'] for m in mappings if m['target'] == YAML_REFERENCE_NAME), None)
    nom_qte = next((m['source'] for m in mappings if m['target'] == YAML_QUANTITY_NAME), None)
    print(f'chemin {chemin}, ref {nom_ref}, qte {nom_qte}')
    header = None if no_header else 'infer'
    # Lecture du fichier
    df_info = read_dataset_file(file_name=chemin, header=header)
    pd.set_option('display.max_columns', None) 
    print('\n\n data: ', df_info['dataset'].head())
    df = df_info['dataset'].copy()
    # Use new helper for mapping by index or name
    ref_col = get_column_by_mapping(df, nom_ref)
    qty_col = get_column_by_mapping(df, nom_qte)
    print('This', df[df[ref_col]== 'BM91518H'])
    print(df.head())
    print(df[qty_col].dtype)
    print('This is row original', df[df[ref_col]== 'BM91518H'])
    print('This is reduced qte row original processed', df[df[ref_col] == 'BM91518H'])
    df[qty_col] = df[qty_col].apply(process_stock_value)  
    print('This is row original processed', df[df[ref_col] == 'BM91518H'])
    print('*** *** ', df.head())
    # Renommer et nettoyer les colonnes
    reduced_cols_df = df[[ref_col, qty_col]].copy()
    reduced_cols_df[qty_col] = reduced_cols_df[qty_col].astype(int)
    reduced_cols_df.columns = [ID_PRODUCT, QUANTITY]
    print('This is reduced row original processed', reduced_cols_df[reduced_cols_df[ID_PRODUCT] == 'BM91518H'])
    return {
        'Chemin': chemin,
        'ref': ref_col,
        'qte': qty_col,
        'main_data': df,  # données brutes
        'reduced_data': reduced_cols_df,  # données nettoyées
        'sep': df_info['sep'],
        'encoding': df_info['encoding']
    }


data_fournisseurs = {}
for i, (name, data_f) in enumerate(valide_fichiers_fournisseurs.items(), 1):
    data_fournisseurs[f'Fournisseur{i}'] = read_data_and_save_params(i, data_f)

print('\n\nhere \n', data_fournisseurs['Fournisseur1']['reduced_data'].head())


list_df = []
for key, item in data_fournisseurs.items():
    list_df.append(item['reduced_data'])
    print('-->This is reduced row original processed', item['reduced_data'][item['reduced_data'][ID_PRODUCT] == 'BM91518H'])

    print(len(item['reduced_data']))

df_all_fournisseus = pd.concat(list_df, ignore_index=True)


print('df_all_fournisseus\n', df_all_fournisseus.head())
print(df_all_fournisseus.shape)

df_all_fournisseus = df_all_fournisseus.sort_values(by=ID_PRODUCT, ascending=True)
print('-``->This is reduced row original processed', df_all_fournisseus[df_all_fournisseus[ID_PRODUCT] == 'BM91518H'])


#print('\n avant', df_all_fournisseus.head(200))
df_cumule = df_all_fournisseus.groupby(ID_PRODUCT, as_index=False)[QUANTITY].sum()
print('-**``**->cumule', df_cumule[df_cumule[ID_PRODUCT] == 'BM91518H'])



for fournisseur, infos in data_fournisseurs.items():
    df = infos['main_data']
    print('***columns: ', df.columns)
    # On fait un merge pour ajouter la colonne de quantité cumulée
    #df = df.merge(df_cumule, on=ID_PRODUCT, how='left', suffixes=('', '_qte_cumulee'))

    #df.drop(columns=[f'{QUANTITY}_qte_cumulee'], inplace=True)

    print('-Youpi*->cumule', df[df[infos['ref']] == 'BM91518H'])





    df_merged = df.merge(df_cumule, left_on=infos['ref'], right_on=ID_PRODUCT, how='left')
    print('new columns: ', df_merged.columns)
    print('-Youpi*->merged', df_merged[df_merged[infos['ref']] == 'BM91518H'])


    # Remplacer qte par quantity
    df_merged[infos['qte']] = df_merged[QUANTITY]

    print('-Youpi*->quantity',  df_merged[QUANTITY][df_merged[infos['ref']] == 'BM91518H'])
    print('-Youpi*->quantity merged',  df_merged[df_merged[infos['ref']] == 'BM91518H'])


    # Supprimer la colonne inutile 'ref' et 'quantity'
    df_final = df_merged.drop(columns=[ID_PRODUCT, QUANTITY])
    print('last columns: ', df_final.columns)
    print('-Youpi*->final',  df_final[df_final[infos['ref']] == 'BM91518H'])


    # Mise à jour du DataFrame dans le dictionnaire
    infos['main_data'] = df_final
    print('final cols', infos['main_data'].columns)
    print('final ds', infos['main_data'].head())
    save_file(infos['Chemin'], infos['main_data'],infos['encoding'], infos['sep'])


'''

pyinstaller gui_app.gui_main.py --noconfirm --icon=img/DROX-Logo.ico --onefile `
--add-data "config;config" `
--add-data "img;img" `
--add-data ".env;." `
--add-data "logs;logs" `
--add-data "fichiers_fournisseurs;fichiers_fournisseurs" `
--add-data "fichiers_platforms;fichiers_platforms" `
--add-data "UPDATED_FILES;UPDATED_FILES" `
--add-data "Verifier;Verifier"
--add-data "Verifier;Verifier"

--add-data "gui_app;gui_app"

'''