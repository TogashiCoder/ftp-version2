import os
import sys
import yaml
import time
import string
import threading
import customtkinter as ctk
import tkinter as tk
import subprocess

from pathlib import Path
from tkinter import scrolledtext
from utils import read_yaml_file, load_fournisseurs_config, load_plateformes_config
from functions.functions_update import *
from config.logging_config import logger
from config.config_path_variables import *
from tkinter import filedialog, messagebox
from config.temporary_data_list import current_dataFiles
from functions.functions_FTP import upload_updated_files_to_marketplace
from functions.functions_report import ReportGenerator

class MajManuelleFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        # Title
        title_font = ("Segoe UI", 20, "bold")
        label = ctk.CTkLabel(self, text="Mise à Jour Manuelle : Plateforme via Fichier Fournisseur", font=title_font)
        label.pack(pady=(10, 20))
        # Platform dropdown
        from utils import load_plateformes_config
        self.platforms = list(load_plateformes_config().keys())
        self.selected_platform = tk.StringVar()
        platform_frame = ctk.CTkFrame(self, fg_color="transparent")
        platform_frame.pack(pady=10)
        ctk.CTkLabel(platform_frame, text="Sélectionnez la plateforme à mettre à jour :", font=("Segoe UI", 13)).pack(side="left", padx=5)
        self.platform_dropdown = ctk.CTkComboBox(platform_frame, values=self.platforms, variable=self.selected_platform, width=220)
        self.platform_dropdown.pack(side="left", padx=5)
        # File upload
        file_frame = ctk.CTkFrame(self, fg_color="transparent")
        file_frame.pack(pady=10)
        ctk.CTkLabel(file_frame, text="Fichier fournisseur à importer :", font=("Segoe UI", 13)).pack(side="left", padx=5)
        self.selected_file = tk.StringVar()
        self.file_label = ctk.CTkLabel(file_frame, text="Aucun fichier sélectionné", text_color="#888")
        self.file_label.pack(side="left", padx=5)
        file_btn = ctk.CTkButton(file_frame, text="Sélectionner un fichier", command=self.select_supplier_file)
        file_btn.pack(side="left", padx=5)
        # Mapping preview/validation
        mapping_frame = ctk.CTkFrame(self, fg_color="transparent")
        mapping_frame.pack(pady=10)
        self.mapping_status = ctk.CTkLabel(mapping_frame, text="Mapping : Non vérifié", text_color="#888")
        self.mapping_status.pack(side="left", padx=5)
        mapping_btn = ctk.CTkButton(mapping_frame, text="👁️ Prévisualiser mapping", command=self.preview_mapping)
        mapping_btn.pack(side="left", padx=5)
        # Process button
        process_btn = ctk.CTkButton(self, text="✅ Lancer la mise à jour", command=self.run_manual_update, font=("Segoe UI", 15, "bold"))
        process_btn.pack(pady=15)
        # Result/log display
        self.result_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 12))
        self.result_label.pack(pady=10)
        # Internal state
        self.supplier_file_path = None
        self.supplier_mapping_valid = False

    def select_supplier_file(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(title="Sélectionnez le fichier fournisseur", filetypes=[("Fichiers supportés", "*.csv *.xlsx *.xls *.txt *.json")])
        if file_path:
            self.supplier_file_path = file_path
            self.file_label.configure(text=os.path.basename(file_path), text_color="#1a7f37")
            self.mapping_status.configure(text="Mapping : À valider", text_color="#888")
            self.supplier_mapping_valid = False

    def preview_mapping(self):
        from utils import get_entity_mappings, read_dataset_file
        if not self.supplier_file_path:
            self.mapping_status.configure(text="Mapping : Aucun fichier", text_color="#d6470e")
            return
        platform = self.selected_platform.get()
        if not platform:
            self.mapping_status.configure(text="Mapping : Plateforme non sélectionnée", text_color="#d6470e")
            return
        mappings, no_header, multi_file = get_entity_mappings(platform)
        try:
            header = None if no_header else 'infer'
            data = read_dataset_file(self.supplier_file_path, header=header)
            df = data['dataset']
            
            # DEBUG: Show actual column names found in CSV
            print("=== DEBUG: Actual column names in CSV ===")
            for idx, col in enumerate(df.columns):
                print(f"Column {idx}: '{col}' (type: {type(col)}, repr: {repr(col)})")
            print("=" * 50)
            
            columns = list(df.columns)
            ref_col = next((m['source'] for m in mappings if m['target'] == 'nom_reference'), None)
            qty_col = next((m['source'] for m in mappings if m['target'] == 'quantite_stock'), None)
            
            print(f"DEBUG: Looking for ref_col: '{ref_col}', qty_col: '{qty_col}'")
            
            missing = []
            # Resolve columns by index or name
            preview_cols = []
            preview_indices = []  # Track column indices for correct data selection
            
            for col_name in [ref_col, qty_col]:
                found_col = None
                found_idx = None
                
                try:
                    idx = int(col_name)
                    if 0 <= idx < len(df.columns):
                        found_col = df.columns[idx]
                        found_idx = idx
                        print(f"DEBUG: Found column by index {idx}: '{found_col}'")
                except (ValueError, TypeError):
                    # For column names, we need special handling for NTY
                    # Check if this is the problematic NTY file structure
                    if (col_name in df.columns and 
                        len(df.columns) >= 8 and 
                        str(df.columns[0]).strip().lower() == "codes de produits" and
                        str(df.columns[7]).strip().lower() == "quantites"):
                        
                        # This is the NTY file with misaligned headers
                        if col_name == "Codes de produits":
                            found_idx = 0  # Use column 0 for product codes (A-AR-004...)
                            found_col = df.columns[0]
                            print(f"DEBUG: NTY special case - '{col_name}' -> using column index 0 for correct data")
                        elif col_name == "Quantites":
                            found_idx = 7  # Use column 7 for quantities (1.00...)
                            found_col = df.columns[7]
                            print(f"DEBUG: NTY special case - '{col_name}' -> using column index 7 for correct data")
                        else:
                            # Try exact match first
                            if col_name in df.columns:
                                found_col = col_name
                                found_idx = list(df.columns).index(col_name)
                                print(f"DEBUG: Found column by exact match: '{found_col}'")
                    else:
                        # Normal column name resolution
                        if col_name in df.columns:
                            found_col = col_name
                            found_idx = list(df.columns).index(col_name)
                            print(f"DEBUG: Found column by exact match: '{found_col}'")
                        else:
                            # Try case-insensitive and trimmed match
                            if col_name:
                                col_clean = col_name.strip().lower()
                                for idx, col in enumerate(df.columns):
                                    csv_col_clean = str(col).strip().lower()
                                    if csv_col_clean == col_clean:
                                        found_col = col
                                        found_idx = idx
                                        print(f"DEBUG: Found column by fuzzy match: '{col_name}' -> '{found_col}'")
                                        break
                
                if found_col is not None and found_idx is not None:
                    preview_cols.append(found_col)
                    preview_indices.append(found_idx)
                else:
                    missing.append(str(col_name))
                    print(f"DEBUG: Column NOT found: '{col_name}'")
            
            if missing:
                available_str = ", ".join([f"{i}:'{col}'" for i, col in enumerate(df.columns)])
                self.mapping_status.configure(text=f"Mapping : Invalide (colonnes manquantes: {', '.join(missing)})", text_color="#d6470e")
                self.supplier_mapping_valid = False
                messagebox.showwarning(
                    "Colonnes non trouvées", 
                    f"Colonnes non trouvées: {', '.join(missing)}\n\nColonnes disponibles:\n{available_str}\n\nMettez à jour votre mapping avec les index numériques (0, 1, 2...) si les noms ne correspondent pas exactement."
                )
            else:
                self.mapping_status.configure(text="Mapping : Valide", text_color="#1a7f37")
                self.supplier_mapping_valid = True
            
            if preview_indices:
                # Use iloc to select by position for correct data
                preview_df = df.iloc[:, preview_indices].head(10)
                # Set proper column names for display
                preview_df.columns = preview_cols
                # NTY cleaning
                if 'Codes de produits' in preview_df.columns:
                    preview_df['Codes de produits'] = preview_df['Codes de produits'].astype(str).str.split(';').str[0]
                if 'Quantites' in preview_df.columns:
                    import pandas as pd
                    preview_df['Quantites'] = pd.to_numeric(preview_df['Quantites'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0).astype(int)
                
                preview_modal = ctk.CTkToplevel(self)
                preview_modal.title(f"Prévisualisation du mapping: {platform}")
                preview_modal.geometry("700x400")
                text = ctk.CTkTextbox(preview_modal, width=680, height=360)
                text.pack(padx=10, pady=10)
                
                # Fix scientific notation display
                import pandas as pd
                old_options = pd.get_option('display.float_format')
                try:
                    pd.set_option('display.float_format', '{:.0f}'.format)
                    formatted_text = preview_df.to_string(index=False, float_format=lambda x: f'{int(x)}' if pd.notnull(x) and x == x else str(x))
                finally:
                    if old_options is not None:
                        pd.set_option('display.float_format', old_options)
                    else:
                        pd.reset_option('display.float_format')
                
                text.insert("end", formatted_text)
                text.configure(state="disabled")
        except Exception as e:
            self.mapping_status.configure(text=f"Mapping : Erreur ({e})", text_color="#d6470e")
            self.supplier_mapping_valid = False
            print(f"DEBUG: Preview error: {e}")
            import traceback
            traceback.print_exc()

    def run_manual_update(self):
        from utils import get_entity_mappings, read_dataset_file
        platform = self.selected_platform.get()
        if not platform:
            self.result_label.configure(text="Veuillez sélectionner une plateforme.", text_color="#d6470e")
            return
        if not self.supplier_file_path:
            self.result_label.configure(text="Veuillez sélectionner un fichier fournisseur.", text_color="#d6470e")
            return
        # Robust validation before processing
        mappings, no_header, multi_file = get_entity_mappings(platform)
        try:
            header = None if no_header else 'infer'
            data = read_dataset_file(self.supplier_file_path, header=header)
            df = data['dataset']
            ref_col = next((m['source'] for m in mappings if m['target'] == 'nom_reference'), None)
            qty_col = next((m['source'] for m in mappings if m['target'] == 'quantite_stock'), None)
            missing = []
            # Resolve columns by index or name
            resolved_cols = []
            for col in [ref_col, qty_col]:
                try:
                    idx = int(col)
                    if 0 <= idx < len(df.columns):
                        resolved_cols.append(df.columns[idx])
                    else:
                        missing.append(str(col))
                except (ValueError, TypeError):
                    if col in df.columns:
                        resolved_cols.append(col)
                    else:
                        missing.append(str(col))
            if missing:
                self.result_label.configure(text=f"Erreur: colonnes manquantes dans le fichier fournisseur: {', '.join(missing)}", text_color="#d6470e")
                return
            # After renaming, check for 'ID_PRODUCT' and 'QUANTITY'
            supplier_df = df[resolved_cols].copy()
            supplier_df.columns = ['ID_PRODUCT', 'QUANTITY']
            if 'ID_PRODUCT' not in supplier_df.columns or 'QUANTITY' not in supplier_df.columns:
                self.result_label.configure(text="Erreur: mapping incorrect, colonnes 'ID_PRODUCT' ou 'QUANTITY' manquantes après renommage.", text_color="#d6470e")
                return
        except Exception as e:
            self.result_label.configure(text=f"Erreur lors de la validation du fichier: {e}", text_color="#d6470e")
            return
        if not self.supplier_mapping_valid:
            self.result_label.configure(text="Veuillez valider le mapping avant de lancer la mise à jour.", text_color="#d6470e")
            return
        # Call the manual processing function
        try:
            result = self.process_manual_update(platform, self.supplier_file_path)
            if result is True:
                self.result_label.configure(text="Mise à jour effectuée avec succès !", text_color="#1a7f37")
            else:
                self.result_label.configure(text=f"Erreur lors de la mise à jour : {result}", text_color="#d6470e")
        except Exception as e:
            self.result_label.configure(text=f"Erreur lors de la mise à jour : {e}", text_color="#d6470e")

    def process_manual_update(self, platform, supplier_file_path):
        # This function should use the same cumule/processing logic as the main script, but for manual update
        # You can adapt cumule_fournisseurs, mettre_a_jour_Stock, etc. for this context
        from utils import get_entity_mappings, read_dataset_file
        from functions.functions_update import update_plateforme
        from config.config_path_variables import UPDATED_FILES_PATH
        import pandas as pd
        try:
            # Get mapping for platform
            mappings, no_header, multi_file = get_entity_mappings(platform)
            ref_col = next((m['source'] for m in mappings if m['target'] == 'nom_reference'), None)
            qty_col = next((m['source'] for m in mappings if m['target'] == 'quantite_stock'), None)
            if not ref_col or not qty_col:
                return "Mapping incomplet (référence ou quantité manquante)."
            # Read supplier file
            header = None # Always no_header for manual update
            data = read_dataset_file(supplier_file_path, header=header)
            df = data['dataset']
            if ref_col not in df.columns or qty_col not in df.columns:
                return f"Colonnes manquantes dans le fichier : {ref_col}, {qty_col}"
            # Prepare supplier data
            supplier_df = df[[ref_col, qty_col]].copy()
            supplier_df.columns = ['ID_PRODUCT', 'QUANTITY']
            supplier_df['QUANTITY'] = supplier_df['QUANTITY'].astype(int)
            # Read platform file (FTP sync logic can be reused here)
            # For manual, you may want to download the latest platform file or use a template
            # Here, we assume you have a function to get the latest platform file for the selected platform
            from functions.functions_FTP import find_latest_file_for_platform
            from pathlib import Path
            platform_dir = Path(UPDATED_FILES_PATH) / platform
            platform_file = find_latest_file_for_platform(platform_dir, platform)
            if not platform_file or not platform_file.exists():
                return f"Fichier plateforme introuvable pour {platform}."
            platform_data = read_dataset_file(str(platform_file))
            platform_df = platform_data['dataset']
            # Get mapping for platform file
            plat_ref_col = ref_col
            plat_qty_col = qty_col
            # Merge and update stock
            updated_df = update_plateforme(platform_df[[plat_ref_col, plat_qty_col]].copy(), supplier_df, platform, 'manual')
            platform_df[plat_qty_col] = platform_df[plat_ref_col].map(dict(zip(updated_df['ID_PRODUCT'], updated_df['QUANTITY']))).fillna(platform_df[plat_qty_col])
            # Save updated file
            import time
            timestamp = time.strftime('%Y%m%d-%H%M%S')
            latest_file = platform_dir / f"{platform}-latest.csv"
            archive_file = platform_dir / f"{platform}-{timestamp}.csv"
            platform_df.to_csv(latest_file, index=False)
            platform_df.to_csv(archive_file, index=False)
            return True
        except Exception as e:
            return str(e)

    