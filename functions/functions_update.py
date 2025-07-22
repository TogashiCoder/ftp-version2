import os
import warnings
from pathlib import Path
import time

from utils import *
from functions.functions_FTP import * 
from config.logging_config import logger
from config.config_path_variables import *
from config.temporary_data_list import current_dataFiles
from functions.functions_check_ready_files import *

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


def update_plateforme(df_platform, df_fournisseurs, name_platform, name_fournisseur): 
    os.makedirs(VERIFIED_FILES_PATH, exist_ok=True)
    try:

        # Nettoyage du stock fournisseur
        df_fournisseurs[QUANTITY] = df_fournisseurs[QUANTITY].apply(process_stock_value)

        # Ajouter le suffixe _fournisseur après merge sur ID_PRODUCT
        # df_merged = df_platform.merge(df_fournisseurs, on=ID_PRODUCT, how='left', suffixes=('', '_fournisseur'))
        
        # Sauvegarde des différences de quantités
        # df_merged.to_csv(f'{VERIFIED_FILES_PATH}/{name_platform}-{name_fournisseur}_valeurs_différentes.csv', index=False)
         
        df_platform = df_platform.merge(
            df_fournisseurs[[ID_PRODUCT, QUANTITY]],
            on=ID_PRODUCT,
            how='left',
            suffixes=('', '_fournisseur')
        )
                
        df_platform[QUANTITY] = df_platform[f'{QUANTITY}_fournisseur'].combine_first(df_platform[QUANTITY])
        df_platform.drop(columns=[f'{QUANTITY}_fournisseur'], inplace=True)

        # Sauvegarde finale des données corrigées
        # df_platform.to_csv(f'{VERIFIED_FILES_PATH}/{name_platform}-{name_fournisseur}_valeurs_identiques.csv', index=False)

        return df_platform
    except Exception as e:
        logger.error(f"-- -- ❌ -- --  Erreur lors de la mise à jour de fichier...: {e}")


# =========================================================================================
   

def mettre_a_jour_Stock_old(valide_fichiers_platforms, valide_fichiers_fournisseurs):
    
    logger.info('--------------------- Mettre A Jour le Stock -------------------')
    if len(valide_fichiers_platforms) > 0 and len(valide_fichiers_fournisseurs)> 0:
    
        try: 
            for name_p, data_p in valide_fichiers_platforms.items():
                chemin_fichier_p = data_p['chemin_fichier']
                nom_reference_p = data_p[YAML_REFERENCE_NAME]
                quantite_stock_p = data_p[YAML_QUANTITY_NAME]

                df_p_info = read_dataset_file(file_name=chemin_fichier_p, usecols=[nom_reference_p, quantite_stock_p])
                df_p = df_p_info['dataset']
                sep_p = df_p_info['sep']                # used for saving 
                encoding_p = df_p_info['encoding']
                
                df_p.columns = [ID_PRODUCT, QUANTITY]

                for name_f, data_f in valide_fichiers_fournisseurs.items():
                    chemin_fichier_f = data_f['chemin_fichier']
                    nom_reference_f = data_f[YAML_REFERENCE_NAME]
                    quantite_stock_f = data_f[YAML_QUANTITY_NAME]

                    df_f_info = read_dataset_file(file_name=chemin_fichier_f, usecols=[nom_reference_f, quantite_stock_f])
                    df_f = df_f_info['dataset']
                    
                    df_f.columns = [ID_PRODUCT, QUANTITY]

                    df_updated = update_plateforme(df_p, df_f, name_p, name_f)
                    df_p = df_updated    # df_p = df_updated.copy()

                df_info_origin_platform = read_dataset_file(file_name=chemin_fichier_p)
                df_origin_platform = df_info_origin_platform['dataset']
                
                # d_update = dict(zip(df_origin_platform[ID_PRODUCT], df_origin_platform[QUANTITY]))
                map_quantites = dict(zip(df_p[ID_PRODUCT], df_p[QUANTITY]))
            
                # Appliquer la mise à jour des quantités dans le fichier cible
                df_origin_platform[quantite_stock_p] = df_origin_platform[nom_reference_p].map(map_quantites).fillna(df_origin_platform[quantite_stock_p])

            
                os.makedirs(UPDATED_FILES_PATH, exist_ok=True)
            
                # save_file(df_origin_platform, file_name=f'UPDATED_FILES/{path_p}')
                save_file(file_name=f'{UPDATED_FILES_PATH_RACINE}/{Path(chemin_fichier_p).name}', df=df_origin_platform,  encoding=encoding_p, sep=sep_p)
                
                logger.info(f"-- -- ✅ -- --  Mise à jour effectuée : {name_p}")
            logger.info('---------------------------------------------------------------')
        
            logger.info('================================================================')
        
            return True
        except Exception as e:
            logger.error(f"-- -- ❌ -- --  Mise à jour n'est pas effectuée pour {name_p}: {e}")
            return False
    else:
        logger.info(f"Nombre des Fournisseurs: {len(valide_fichiers_fournisseurs)}")
        logger.info(f"Nombre des Plateformes: {len(valide_fichiers_platforms)}")
        logger.error(f"-- -- ❌ -- --  Mise à jour n'est pas effectuée")



def read_fournisseur(data_f):
    chemin_fichier_f = data_f['chemin_fichier']
    nom_reference_f = data_f[YAML_REFERENCE_NAME]    # nom_ref
    quantite_stock_f = data_f[YAML_QUANTITY_NAME]       # nom_qte
    no_header = data_f.get('no_header', False)
    header = None if no_header else 'infer'
    df_f_info = read_dataset_file(file_name=chemin_fichier_f, header=header)   # df_info
    pd.set_option('display.max_columns', None) 
    df_f = df_f_info['dataset'].copy()  # df
    # Use new helper for mapping by index or name
    ref_col = get_column_by_mapping(df_f, nom_reference_f)
    qty_col = get_column_by_mapping(df_f, quantite_stock_f)
    df_f[qty_col] = df_f[qty_col].apply(process_stock_value)   # df[nom_qte]
    reduced_cols_df = df_f[[ref_col, qty_col]].copy()
    reduced_cols_df[qty_col] = reduced_cols_df[qty_col].astype(int)
    reduced_cols_df.columns = [ID_PRODUCT, QUANTITY]
    return {
        'Chemin': chemin_fichier_f,
        'ref': ref_col,
        'qte': qty_col,
        'main_data': df_f,  # données brutes
        'reduced_data': reduced_cols_df,  # données nettoyées
        'sep': df_f_info['sep'],
        'encoding': df_f_info['encoding']
    }
       

def read_all_fournisseurs(valide_fichiers_fournisseurs):
    data_fournisseurs = {}
    for i, (_, data_f) in enumerate(valide_fichiers_fournisseurs.items(), 1):
        data_fournisseurs[f'Fournisseur{i}'] = read_fournisseur(data_f)

    #print('\n\nhere \n', data_fournisseurs['Fournisseur1']['reduced_data'].head())
    return data_fournisseurs


def cumule_fournisseurs(data_fournisseurs):

    '''data_fournisseurs {'Fournisseur1': {'Chemin': './fichiers_fournisseurs/1210021_SBShop-Artikelstamm-Gekürzt_1747871859797.csv', 
                                        'ref': 'Article number', 
                                        'qte': 'Supplier stock', 
                                        'main_data':       Internal Number Article number     Brand name  Brand ID  ... Country of origin  Weight in kg     RRP MOQ
                                        'reduced_data':       ID_Product  Quantity
                                        'sep': ';', 'encoding': 'utf-8'}
    '''
    list_df = []
    for key, item in data_fournisseurs.items():
        list_df.append(item['reduced_data'])

        #print('-->This is reduced row original processed', item['reduced_data'][item['reduced_data'][ID_PRODUCT] == 'BM91518H'])
        #print(len(item['reduced_data']))


    df_all_fournisseus = pd.concat(list_df, ignore_index=True)
    #print('df_all_fournisseus\n', df_all_fournisseus.head())
    #print(df_all_fournisseus.shape)

    df_all_fournisseus = df_all_fournisseus.sort_values(by=ID_PRODUCT, ascending=True)
    #print('-``->This is reduced row original processed', df_all_fournisseus[df_all_fournisseus[ID_PRODUCT] == 'BM91518H'])

    df_cumule = df_all_fournisseus.groupby(ID_PRODUCT, as_index=False)[QUANTITY].sum()

    #print('-**``**->cumule', df_cumule[df_cumule[ID_PRODUCT] == 'BM91518H'])
    #print(df_cumule.columns)
    #print('\\\\\\\\\\ hna pass')
    # ------ Sauvgarde pour validation ------
    for fournisseur, infos in data_fournisseurs.items():
        df = infos['reduced_data']
        df_merged = df.merge(df_cumule, left_on=df[ID_PRODUCT], right_on=ID_PRODUCT, how='left', suffixes=('', '_Fourniss_After_Cumule'))
        #print('merged:', df_merged.columns)
        df_merged[infos['qte']] = df_merged[QUANTITY+'_Fourniss_After_Cumule']
        df_final = df_merged.drop(columns=[ID_PRODUCT+'_Fourniss_After_Cumule'])
        infos['reduced_data'] = df_final
        VERIFIED_FILES_PATH.mkdir(parents=True, exist_ok=True)

        #print('********* Save verified **********', f"{Path(VERIFIED_FILES_PATH) / Path(infos['Chemin']).name}")
        logger.info('---------- Juste pour Verifier (Cumule) -----------')
        save_file(f"{Path(VERIFIED_FILES_PATH) / Path(infos['Chemin']).name}", infos['reduced_data'],infos['encoding'], infos['sep'])
    
    return df_cumule # data_fournisseurs


def mettre_a_jour_Stock(valide_fichiers_platforms, valide_fichiers_fournisseurs, report_gen=None):
    logger.info('--------------------- Mettre A Jour le Stock -------------------')
    if len(valide_fichiers_platforms) > 0 and len(valide_fichiers_fournisseurs)> 0:
        try: 
            data_fournisseurs = read_all_fournisseurs(valide_fichiers_fournisseurs)
            logger.info('----------- Calcule de cumule ------------------')
            data_fournisseurs_cumule = cumule_fournisseurs(data_fournisseurs)
            for name_p, data_p in valide_fichiers_platforms.items():
                try:
                    chemin_fichier_p = data_p['chemin_fichier']
                    nom_reference_p = data_p[YAML_REFERENCE_NAME]
                    quantite_stock_p = data_p[YAML_QUANTITY_NAME]
                    df_p_info = read_dataset_file(file_name=chemin_fichier_p)
                    df_p = df_p_info['dataset']
                    sep_p = df_p_info['sep']
                    encoding_p = df_p_info['encoding']
                    reduced_data_p = df_p[[nom_reference_p, quantite_stock_p]].copy()
                    reduced_data_p.columns = [ID_PRODUCT, QUANTITY]
                    df_updated = update_plateforme(reduced_data_p, data_fournisseurs_cumule, name_p, 'cumule')
                    reduced_data_p = df_updated
                    map_quantites = dict(zip(reduced_data_p[ID_PRODUCT], reduced_data_p[QUANTITY]))
                    df_p[quantite_stock_p] = df_p[nom_reference_p].map(map_quantites).fillna(df_p[quantite_stock_p])
                    platform_dir = UPDATED_FILES_PATH / name_p
                    platform_dir.mkdir(parents=True, exist_ok=True)
                    timestamp = time.strftime('%Y%m%d-%H%M%S')
                    latest_file = platform_dir / f"{name_p}-latest.csv"
                    archive_file = platform_dir / f"{name_p}-{timestamp}.csv"
                    save_file(str(latest_file), df_p, encoding=encoding_p, sep=sep_p)
                    save_file(str(archive_file), df_p, encoding=encoding_p, sep=sep_p)
                    logger.info(f"-- -- ✅ -- --  Mise à jour effectuée et fichiers sauvegardés pour : {name_p}")
                    if report_gen:
                        report_gen.add_platform_processed(name_p)
                        report_gen.add_file_result(str(latest_file), success=True)
                        # Count unique product references updated
                        if report_gen:
                            unique_refs_updated = reduced_data_p[ID_PRODUCT].nunique()
                            report_gen.add_products_count(unique_refs_updated)
                except Exception as e:
                    logger.error(f"Erreur lors de la mise à jour de la plateforme {name_p}: {e}")
                    if report_gen:
                        report_gen.add_file_result(str(latest_file) if 'latest_file' in locals() else name_p, success=False, error_msg=str(e))
                        report_gen.add_error(f"Erreur mise à jour plateforme {name_p}: {e}")
            logger.info('---------------------------------------------------------------')
            logger.info('================================================================')
            return True
        except Exception as e:
            logger.error(f"-- -- ❌ -- --  Mise à jour n'est pas effectuée: {e}")
            if report_gen:
                report_gen.add_error(f"Erreur globale mise à jour: {e}")
            return False
    else:
        logger.info(f"Nombre des Fournisseurs: {len(valide_fichiers_fournisseurs)}")
        logger.info(f"Nombre des Plateformes: {len(valide_fichiers_platforms)}")
        logger.error(f"-- -- ❌ -- --  Mise à jour n'est pas effectuée")
        if report_gen:
            report_gen.add_error("Aucun fichier fournisseur ou plateforme valide.")