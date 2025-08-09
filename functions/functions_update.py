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


def update_plateforme(df_platform, df_fournisseurs, name_platform, name_fournisseur, supplier_details=None): 
    os.makedirs(VERIFIED_FILES_PATH, exist_ok=True)
    stock_changes = []  # Track actual changes
    try:
        # Keep original quantities for comparison
        df_platform_original = df_platform.copy()
        
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
        
        # Track changes before updating
        mask = df_platform[f'{QUANTITY}_fournisseur'].notna()
        changed_products = df_platform[mask].copy()
        
        # Compare old and new values
        for idx, row in changed_products.iterrows():
            old_qty = row[QUANTITY]
            new_qty = row[f'{QUANTITY}_fournisseur']
            if pd.notna(new_qty) and old_qty != new_qty:
                change_data = {
                    'product_id': row[ID_PRODUCT],
                    'old_quantity': int(old_qty) if pd.notna(old_qty) else 0,
                    'new_quantity': int(new_qty),
                    'platform': name_platform
                }
                
                # Add supplier details if provided
                if supplier_details and row[ID_PRODUCT] in supplier_details:
                    change_data['supplier_details'] = supplier_details[row[ID_PRODUCT]]
                
                stock_changes.append(change_data)
                
        df_platform[QUANTITY] = df_platform[f'{QUANTITY}_fournisseur'].combine_first(df_platform[QUANTITY])
        df_platform.drop(columns=[f'{QUANTITY}_fournisseur'], inplace=True)

        # Sauvegarde finale des données corrigées
        # df_platform.to_csv(f'{VERIFIED_FILES_PATH}/{name_platform}-{name_fournisseur}_valeurs_identiques.csv', index=False)

        return df_platform, stock_changes
    except Exception as e:
        logger.error(f"-- -- ❌ -- --  Erreur lors de la mise à jour de fichier...: {e}")
        return None, []


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

                    df_updated, _ = update_plateforme(df_p, df_f, name_p, name_f)
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
    multi_file = data_f.get('multi_file', False)
    header = None if no_header else 'infer'
    if multi_file and isinstance(chemin_fichier_f, list):
        # Process all files, concatenate, and sum stock per reference
        dfs = []
        for file_path in chemin_fichier_f:
            df_f_info = read_dataset_file(file_name=file_path, header=header)
            df_f = df_f_info['dataset'].copy()
            ref_col = get_column_by_mapping(df_f, nom_reference_f)
            qty_col = get_column_by_mapping(df_f, quantite_stock_f)
            df_f[qty_col] = df_f[qty_col].apply(process_stock_value)
            reduced_cols_df = df_f[[ref_col, qty_col]].copy()
            reduced_cols_df[qty_col] = reduced_cols_df[qty_col].astype(int)
            reduced_cols_df.columns = [ID_PRODUCT, QUANTITY]
            dfs.append(reduced_cols_df)
        if dfs:
            all_data = pd.concat(dfs, ignore_index=True)
            # Sum stock per reference
            reduced_cols_df = all_data.groupby(ID_PRODUCT, as_index=False)[QUANTITY].sum()
        else:
            reduced_cols_df = pd.DataFrame(columns=[ID_PRODUCT, QUANTITY])
        return {
            'Chemin': chemin_fichier_f,
            'ref': ID_PRODUCT,
            'qte': QUANTITY,
            'main_data': reduced_cols_df,  # données brutes
            'reduced_data': reduced_cols_df,  # données nettoyées
            'sep': None,
            'encoding': None
        }
    else:
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

    # Force ID_PRODUCT to string
    df_all_fournisseus[ID_PRODUCT] = df_all_fournisseus[ID_PRODUCT].astype(str)
    logger.debug(f"[DEBUG] ID_PRODUCT dtype: {df_all_fournisseus[ID_PRODUCT].dtype}, unique: {df_all_fournisseus[ID_PRODUCT].unique()[:10]}")
    # Debug before sort/groupby
    logger.debug(f"[DEBUG] cumule_fournisseurs: df_all_fournisseus[QUANTITY] dtype: {df_all_fournisseus[QUANTITY].dtype}, unique values: {df_all_fournisseus[QUANTITY].unique()[:10]}")
    try:
        df_all_fournisseus = df_all_fournisseus.sort_values(by=ID_PRODUCT, ascending=True)
        df_cumule = df_all_fournisseus.groupby(ID_PRODUCT, as_index=False)[QUANTITY].sum()
    except Exception as e:
        logger.error(f"[DEBUG] Error during aggregation in cumule_fournisseurs: {e}")
        logger.error(f"[DEBUG] Problematic values: {df_all_fournisseus[QUANTITY].unique()[:20]}")
        raise
    # Debug after groupby
    logger.debug(f"[DEBUG] cumule_fournisseurs: df_cumule[QUANTITY] dtype: {df_cumule[QUANTITY].dtype}, unique values: {df_cumule[QUANTITY].unique()[:10]}")
    # ------ Sauvgarde pour validation ------
    for fournisseur, infos in data_fournisseurs.items():
        df = infos['reduced_data']
        try:
            chemin = infos['Chemin']
            if isinstance(chemin, list):
                chemin_for_name = chemin[0]
            else:
                chemin_for_name = chemin
            # Force ID_PRODUCT to string for merge
            df[ID_PRODUCT] = df[ID_PRODUCT].astype(str)
            df_merged = df.merge(df_cumule, left_on=df[ID_PRODUCT], right_on=ID_PRODUCT, how='left', suffixes=('', '_Fourniss_After_Cumule'))
            df_merged[infos['qte']] = df_merged[QUANTITY+'_Fourniss_After_Cumule']
            df_final = df_merged.drop(columns=[ID_PRODUCT+'_Fourniss_After_Cumule'])
            infos['reduced_data'] = df_final
            VERIFIED_FILES_PATH.mkdir(parents=True, exist_ok=True)
            logger.info('---------- Juste pour Verifier (Cumule) -----------')
            save_file(f"{Path(VERIFIED_FILES_PATH) / Path(chemin_for_name).name}", infos['reduced_data'],infos['encoding'], infos['sep'])
        except Exception as e:
            logger.error(f"[DEBUG] Error during merge in cumule_fournisseurs for {fournisseur}: {e}")
            logger.error(f"[DEBUG] Problematic df: {df.head()} | df_cumule: {df_cumule.head()}")
            raise
    return df_cumule # data_fournisseurs


def collect_supplier_details(data_fournisseurs):
    """Collects individual supplier stock for each product"""
    supplier_details = {}
    for name, data in data_fournisseurs.items():
        for _, row in data['reduced_data'].iterrows():
            product_id = str(row[ID_PRODUCT])
            quantity = row[QUANTITY]
            if product_id not in supplier_details:
                supplier_details[product_id] = {}
            supplier_details[product_id][name] = quantity
    return supplier_details

def mettre_a_jour_Stock(valide_fichiers_platforms, valide_fichiers_fournisseurs, report_gen=None):
    logger.info('--------------------- Mettre A Jour le Stock -------------------')
    if len(valide_fichiers_platforms) > 0 and len(valide_fichiers_fournisseurs)> 0:
        try: 
            data_fournisseurs = read_all_fournisseurs(valide_fichiers_fournisseurs)
            supplier_details = collect_supplier_details(data_fournisseurs)
            
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
                    # Handle NaN/None before processing
                    df_p[quantite_stock_p] = df_p[quantite_stock_p].fillna(0)
                    df_p[quantite_stock_p] = df_p[quantite_stock_p].apply(process_stock_value)
                    logger.debug(f"[DEBUG] Platform '{name_p}' stock column dtype: {df_p[quantite_stock_p].dtype}, unique values: {df_p[quantite_stock_p].unique()[:10]}")
                    reduced_data_p = df_p[[nom_reference_p, quantite_stock_p]].copy()
                    reduced_data_p.columns = [ID_PRODUCT, QUANTITY]
                    logger.debug(f"[DEBUG] reduced_data_p[QUANTITY] dtype: {reduced_data_p[QUANTITY].dtype}, unique values: {reduced_data_p[QUANTITY].unique()[:10]}")
                    # Ensure ID_PRODUCT columns are string before merging
                    reduced_data_p[ID_PRODUCT] = reduced_data_p[ID_PRODUCT].astype(str)
                    data_fournisseurs_cumule[ID_PRODUCT] = data_fournisseurs_cumule[ID_PRODUCT].astype(str)
                    try:
                        df_updated, stock_changes = update_plateforme(reduced_data_p, data_fournisseurs_cumule, name_p, 'cumule', supplier_details=supplier_details)
                    except Exception as merge_exc:
                        logger.error(f"[MERGE ERROR] Platform {name_p}: {merge_exc}")
                        if report_gen:
                            report_gen.add_file_result(str(latest_file) if 'latest_file' in locals() else name_p, success=False, error_msg=f"Merge error: {merge_exc}")
                        continue  # Skip this platform
                    if df_updated is None:
                        logger.error(f"[SKIP] Platform {name_p}: update_plateforme returned None.")
                        if report_gen:
                            report_gen.add_file_result(str(latest_file) if 'latest_file' in locals() else name_p, success=False, error_msg="update_plateforme returned None.")
                        continue
                    reduced_data_p = df_updated
                    
                    # Add stock changes to report
                    if report_gen and stock_changes:
                        report_gen.add_stock_changes(stock_changes)
                    map_quantites = dict(zip(reduced_data_p[ID_PRODUCT], reduced_data_p[QUANTITY]))
                    if nom_reference_p is None or quantite_stock_p is None:
                        logger.error(f"[SKIP] Platform {name_p}: Mapping extraction failed (nom_reference_p or quantite_stock_p is None)")
                        if report_gen:
                            report_gen.add_file_result(str(latest_file) if 'latest_file' in locals() else name_p, success=False, error_msg="Mapping extraction failed.")
                        continue
                    df_p[quantite_stock_p] = df_p[nom_reference_p].map(map_quantites).fillna(df_p[quantite_stock_p])
                    platform_dir = UPDATED_FILES_PATH / name_p
                    platform_dir.mkdir(parents=True, exist_ok=True)
                    timestamp = time.strftime('%Y%m%d-%H%M%S')
                    # Detect original extension
                    platform_ext = Path(chemin_fichier_p).suffix.lower()
                    # Build output file paths with same extension
                    latest_file = platform_dir / f"{name_p}-latest{platform_ext}"
                    archive_file = platform_dir / f"{name_p}-{timestamp}{platform_ext}"
                    force_excel = platform_ext in {'.xls', '.xlsx'}
                    save_file(str(latest_file), df_p, encoding=encoding_p, sep=sep_p, force_excel=force_excel)
                    save_file(str(archive_file), df_p, encoding=encoding_p, sep=sep_p, force_excel=force_excel)
                    logger.info(f"-- -- ✅ -- --  Mise à jour effectuée et fichiers sauvegardés pour : {name_p}")
                    if report_gen:
                        report_gen.add_platform_processed(name_p)
                        report_gen.add_file_result(str(latest_file), success=True)
                        # The actual count of updated products is now handled by add_stock_changes
                except Exception as e:
                    logger.error(f"Erreur lors de la mise à jour de la plateforme {name_p}: {e}")
                    logger.error(f"[DEBUG] Platform '{name_p}' DataFrame: {df_p.head()}")
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