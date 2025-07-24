import os
import yaml
import customtkinter as ctk
from tkinter import messagebox, filedialog
from pathlib import Path
from utils import get_entity_mappings

CONFIG_PATH = Path(__file__).resolve().parents[1] / 'config' / 'fournisseurs_connexions.yaml'

class FournisseurAdminFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.connexions = self.load_connexions()
        self.selected_fournisseur = None
        self.selected_row_widget = None
        self.build_gui()

    def load_connexions(self):
        if not CONFIG_PATH.exists():
            return {}
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if data is None or data == []:
                return {}
            return data

    def save_connexions(self):
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.connexions, f, allow_unicode=True)

    def build_gui(self):
        title = ctk.CTkLabel(self, text="Administration Connexion Fournisseur", font=("Segoe UI", 20, "bold"))
        title.pack(pady=(10, 10))
        
        # Table header
        header_frame = ctk.CTkFrame(self, fg_color="#253d61")
        header_frame.pack(fill="x", padx=10)
        headers = ["Nom", "Type", "Hôte", "Port", "Utilisateur", "Mot de passe", "Notes"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(header_frame, text=h, font=("Segoe UI", 13, "bold"), anchor="w", text_color="#fff", fg_color="#253d61").grid(row=0, column=i, padx=4, pady=2, sticky="w")

        # Table body (scrollable)
        self.table_scroll = ctk.CTkScrollableFrame(self, height=260)
        self.table_scroll.pack(fill="x", padx=10, pady=(0, 5))

        # Action buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=8)
        self.add_btn = ctk.CTkButton(btn_frame, text="➕ Ajouter", command=self.add_fournisseur_modal)
        self.edit_btn = ctk.CTkButton(btn_frame, text="✏️ Modifier", command=self.edit_fournisseur_modal, state="disabled")
        self.del_btn = ctk.CTkButton(btn_frame, text="🗑️ Supprimer", command=self.remove_fournisseur, state="disabled")
        self.test_btn = ctk.CTkButton(btn_frame, text="🔌 Tester Connexion", command=self.test_connexion, state="disabled")
        self.mapping_btn = ctk.CTkButton(btn_frame, text="🗂️ Gérer les mappings de colonnes", command=self.open_mapping_modal, state="disabled")
        self.add_btn.pack(side="left", padx=5)
        self.edit_btn.pack(side="left", padx=5)
        self.del_btn.pack(side="left", padx=5)
        self.test_btn.pack(side="left", padx=5)
        self.mapping_btn.pack(side="left", padx=5)

        # Status bar
        self.status_bar = ctk.CTkLabel(self, text="", font=("Segoe UI", 11), text_color="#888", anchor="w")
        self.status_bar.pack(fill="x", padx=10, pady=(2, 0))

        self.mapping_display_frame = ctk.CTkFrame(self)
        self.mapping_display_frame.pack(fill="x", padx=10, pady=(0, 5))

        # Now safe to call refresh_table
        self.refresh_table()

    def refresh_table(self):
        for widget in self.table_scroll.winfo_children():
            widget.destroy()
        alt_colors = ["#f7f7f7", "#e9e9e9"]
        for idx, (name, info) in enumerate(self.connexions.items()):
            is_selected = (name == self.selected_fournisseur)
            row_bg = "#ffe5c2" if is_selected else alt_colors[idx%2]
            row_font = ("Segoe UI", 12, "bold") if is_selected else ("Segoe UI", 12)
            row_frame = ctk.CTkFrame(self.table_scroll, fg_color=row_bg)
            row_frame.pack(fill="x", pady=1)
            pw_mask = '******' if info.get('password') else ''
            values = [name, info.get('type',''), info.get('host',''), info.get('port',''), info.get('username',''), pw_mask, info.get('notes','')]
            for i, v in enumerate(values):
                ctk.CTkLabel(row_frame, text=v, anchor="w", font=row_font, text_color="#222", fg_color=row_bg).grid(row=0, column=i, padx=4, pady=2, sticky="w")
            row_frame.bind("<Button-1>", lambda e, n=name, rf=row_frame: self.select_row(n, rf))
            for child in row_frame.winfo_children():
                child.bind("<Button-1>", lambda e, n=name, rf=row_frame: self.select_row(n, rf))
            # highlight if selected
            if is_selected:
                row_frame.configure(border_width=2, border_color="#ef8018")
            else:
                row_frame.configure(border_width=0)
        # --- FIX: After table refresh, reset selection and buttons ---
        self.selected_fournisseur = None
        self.selected_row_widget = None
        self.edit_btn.configure(state="disabled")
        self.del_btn.configure(state="disabled")
        self.test_btn.configure(state="disabled")
        self.mapping_btn.configure(state="disabled")
        self.status_bar.configure(text="Sélectionnez un fournisseur pour modifier, supprimer ou tester.", text_color="#888")
        self.refresh_mapping_display()
        # Set focus to Add button to remove hover from last row
        self.add_btn.focus_set()

    def refresh_mapping_display(self):
        for widget in self.mapping_display_frame.winfo_children():
            widget.destroy()
        if not self.selected_fournisseur:
            ctk.CTkLabel(self.mapping_display_frame, text="Aucun fournisseur sélectionné.").pack(anchor="w", padx=5, pady=2)
            return
        # Get mappings for the selected fournisseur
        entity_key = self.selected_fournisseur.strip()
        columns, no_header, multi_file = get_entity_mappings(entity_key)
        if not columns:
            ctk.CTkLabel(self.mapping_display_frame, text="Aucun mapping défini pour ce fournisseur.").pack(anchor="w", padx=5, pady=2)
            return
        header_frame = ctk.CTkFrame(self.mapping_display_frame)
        header_frame.pack(fill="x")
        ctk.CTkLabel(header_frame, text="Source", width=200, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, padx=5)
        ctk.CTkLabel(header_frame, text="Cible", width=200, font=("Segoe UI", 12, "bold")).grid(row=0, column=1, padx=5)
        for idx, mapping in enumerate(columns):
            row_frame = ctk.CTkFrame(self.mapping_display_frame)
            row_frame.pack(fill="x")
            ctk.CTkLabel(row_frame, text=mapping.get('source',''), width=200).grid(row=0, column=0, padx=5)
            ctk.CTkLabel(row_frame, text=mapping.get('target',''), width=200).grid(row=0, column=1, padx=5)

    def select_row(self, name, row_widget):
        self.selected_fournisseur = name
        if self.selected_row_widget:
            self.selected_row_widget.configure(border_width=0, fg_color="#f7f7f7")
        row_widget.configure(border_width=2, border_color="#ef8018", fg_color="#ffe5c2")
        self.selected_row_widget = row_widget
        self.edit_btn.configure(state="normal")
        self.del_btn.configure(state="normal")
        self.test_btn.configure(state="normal")
        self.mapping_btn.configure(state="normal")
        self.status_bar.configure(text=f"Fournisseur sélectionné: {name}", text_color="#253d61")
        self.refresh_mapping_display()

    def add_fournisseur_modal(self):
        self.open_fournisseur_modal("Ajouter un fournisseur")

    def edit_fournisseur_modal(self):
        if not self.selected_fournisseur:
            return
        self.open_fournisseur_modal("Modifier le fournisseur", self.selected_fournisseur, self.connexions[self.selected_fournisseur])

    def open_fournisseur_modal(self, title, name_init=None, info=None):
        modal = ctk.CTkToplevel(self)
        modal.title(title)
        modal.geometry("500x370")
        modal.grab_set()
        modal.focus()
        modal.resizable(False, False)
        fields = ["Nom", "Type", "Hôte", "Port", "Utilisateur", "Mot de passe", "Notes"]
        entries = {}
        for i, field in enumerate(fields):
            ctk.CTkLabel(modal, text=field+":", anchor="w").grid(row=i, column=0, sticky="w", padx=12, pady=7)
            if field == "Type":
                entry = ctk.CTkComboBox(modal, values=["FTP", "manual"])
                entry.set((info.get('type') if info and info.get('type') else "FTP"))
            elif field == "Mot de passe":
                entry = ctk.CTkEntry(modal, show="*")
                entry.insert(0, info.get('password') if info and info.get('password') else "")
            elif field == "Port":
                entry = ctk.CTkEntry(modal)
                entry.insert(0, str(info.get('port')) if info and info.get('port') else "21")
            elif field == "Nom":
                entry = ctk.CTkEntry(modal)
                entry.insert(0, name_init if name_init else "")
                if name_init:
                    entry.configure(state="disabled")
            else:
                # For all other fields, show empty if missing/null
                entry = ctk.CTkEntry(modal)
                entry.insert(0, info.get(field.lower().replace(' ','')) if info and info.get(field.lower().replace(' ','')) else "")
            entry.grid(row=i, column=1, sticky="ew", padx=8, pady=7)
            entries[field] = entry
        modal.grid_columnconfigure(1, weight=1)
        def on_save():
            name = entries["Nom"].get().strip()
            type_ = entries["Type"].get().strip()
            host = entries["Hôte"].get().strip()
            port = entries["Port"].get().strip()
            username = entries["Utilisateur"].get().strip()
            password = entries["Mot de passe"].get().strip()
            notes = entries["Notes"].get().strip()
            if not name:
                self.status_bar.configure(text="Le nom est requis.", text_color="#d6470e")
                return
            if not type_:
                self.status_bar.configure(text="Le type est requis.", text_color="#d6470e")
                return
            if type_.lower() == "ftp" and (not host or not username or not password):
                self.status_bar.configure(text="Hôte, utilisateur et mot de passe requis pour FTP.", text_color="#d6470e")
                return
            try:
                port = int(port) if port else 21
            except ValueError:
                self.status_bar.configure(text="Le port doit être un nombre.", text_color="#d6470e")
                return
            info_dict = {
                'type': type_,
                'host': host,
                'port': port,
                'username': username,
                'password': password,
                'notes': notes
            }
            if not name_init and name in self.connexions:
                self.status_bar.configure(text="Ce fournisseur existe déjà.", text_color="#d6470e")
                return
            self.connexions[name] = info_dict
            self.save_connexions()
            self.refresh_table()
            self.status_bar.configure(text="Fournisseur enregistré avec succès.", text_color="#1a7f37")
            modal.destroy()
        def on_cancel():
            modal.destroy()
        btn_save = ctk.CTkButton(modal, text="💾 Enregistrer", command=on_save)
        btn_cancel = ctk.CTkButton(modal, text="Annuler", command=on_cancel)
        btn_save.grid(row=len(fields), column=0, pady=15, padx=12)
        btn_cancel.grid(row=len(fields), column=1, pady=15, padx=12, sticky="e")

    def remove_fournisseur(self):
        if not self.selected_fournisseur:
            return
        if messagebox.askyesno("Confirmer", f"Supprimer {self.selected_fournisseur} ?"):
            del self.connexions[self.selected_fournisseur]
            self.save_connexions()
            # --- FIX: Reset selection and buttons after delete ---
            self.selected_fournisseur = None
            self.selected_row_widget = None
            self.refresh_table()
            self.status_bar.configure(text="Fournisseur supprimé.", text_color="#d6470e")

    def test_connexion(self):
        # Always use the current selected_fournisseur and update status bar
        if not self.selected_fournisseur or self.selected_fournisseur not in self.connexions:
            self.status_bar.configure(text="Sélectionnez un fournisseur à tester.", text_color="#d6470e")
            return
        info = self.connexions[self.selected_fournisseur]
        if info.get('type', '').lower() == 'manual':
            self.status_bar.configure(text="Ce fournisseur est manuel (pas de connexion à tester).", text_color="#888")
            return
        try:
            from ftplib import FTP
            ftp = FTP()
            ftp.connect(info['host'], int(info['port']))
            ftp.login(info['username'], info['password'])
            ftp.quit()
            self.status_bar.configure(text="Connexion FTP réussie !", text_color="#1a7f37")
        except Exception as e:
            self.status_bar.configure(text=f"Échec de la connexion FTP : {e}", text_color="#d6470e")

    def open_mapping_modal(self):
        if not self.selected_fournisseur:
            messagebox.showinfo("Info", "Sélectionnez un fournisseur pour gérer les mappings.")
            return
        from utils import get_entity_mappings, set_entity_mappings, ALLOWED_TARGETS, read_dataset_file, get_column_by_mapping
        columns, no_header, multi_file = get_entity_mappings(self.selected_fournisseur)
        modal = ctk.CTkToplevel(self)
        modal.title(f"Mappings de colonnes pour {self.selected_fournisseur}")
        modal.geometry("600x500")
        modal.grab_set()
        modal.focus()
        modal.resizable(False, False)
        table_frame = ctk.CTkFrame(modal)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        header = ctk.CTkLabel(table_frame, text="Source", width=200)
        header.grid(row=0, column=0, padx=5)
        header2 = ctk.CTkLabel(table_frame, text="Cible", width=200)
        header2.grid(row=0, column=1, padx=5)
        row_widgets = []
        def refresh_mapping_table():
            for w in row_widgets:
                w[0].destroy()
                w[1].destroy()
                w[2].destroy()
            row_widgets.clear()
            for idx, mapping in enumerate(columns):
                src_var = ctk.StringVar(value=mapping.get('source',''))
                tgt_var = ctk.StringVar(value=mapping.get('target',''))
                src_entry = ctk.CTkEntry(table_frame, textvariable=src_var, width=200)
                src_entry.grid(row=idx+1, column=0, padx=5, pady=2)
                tgt_combo = ctk.CTkComboBox(table_frame, values=ALLOWED_TARGETS, width=200)
                tgt_combo.set(mapping.get('target',''))
                tgt_combo.grid(row=idx+1, column=1, padx=5, pady=2)
                del_btn = ctk.CTkButton(table_frame, text="❌", width=30, command=lambda i=idx: delete_mapping(i))
                del_btn.grid(row=idx+1, column=2, padx=2)
                row_widgets.append((src_entry, tgt_combo, del_btn))
        def add_mapping():
            columns.append({'source':'','target':ALLOWED_TARGETS[0]})
            refresh_mapping_table()
        def delete_mapping(idx):
            if 0 <= idx < len(columns):
                columns.pop(idx)
                refresh_mapping_table()
        # No-header checkbox
        no_header_var = ctk.BooleanVar(value=no_header)
        no_header_checkbox = ctk.CTkCheckBox(
            modal,
            text="Ce fournisseur fournit des fichiers SANS en-tête (mapper par index)",
            variable=no_header_var
        )
        no_header_checkbox.pack(pady=5)
        # Multi-file checkbox
        multi_file_var = ctk.BooleanVar(value=multi_file)
        multi_file_checkbox = ctk.CTkCheckBox(modal, text="Ce fournisseur fournit plusieurs fichiers (multi-entrepôt)", variable=multi_file_var)
        multi_file_checkbox.pack(pady=5)
        def validate_mappings_against_file(file_path, new_mappings):
            try:
                header = None if no_header_var.get() else 'infer'
                data = read_dataset_file(file_path, header=header)
                df = data['dataset']
                columns_ = list(df.columns)
                missing = []
                for m in new_mappings:
                    src = m['source']
                    try:
                        idx = int(src)
                        if 0 <= idx < len(df.columns):
                            continue
                        else:
                            missing.append(src)
                    except ValueError:
                        if src not in columns_:
                            missing.append(src)
                return missing, columns_
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la lecture du fichier: {e}")
                return None, None
        def save_mappings():
            new_mappings = []
            for src_entry, tgt_combo, _ in row_widgets:
                src = src_entry.get().strip()
                tgt = tgt_combo.get().strip()
                if src and tgt in ALLOWED_TARGETS:
                    new_mappings.append({'source': src, 'target': tgt})
            # Save no_header and multi_file flags
            mapping_dict = {
                'no_header': no_header_var.get(),
                'multi_file': multi_file_var.get(),
                'columns': new_mappings
            }
            if not new_mappings:
                set_entity_mappings(self.selected_fournisseur, mapping_dict)
                modal.destroy()
                self.refresh_mapping_display()
                messagebox.showinfo("Succès", "Mappings enregistrés.")
                return
            file_path = filedialog.askopenfilename(title="Sélectionnez un fichier d'exemple pour valider le mapping", filetypes=[("Fichiers supportés", "*.csv *.xlsx *.xls *.txt")])
            if not file_path:
                messagebox.showwarning("Validation", "Aucun fichier sélectionné. Validation ignorée.")
                set_entity_mappings(self.selected_fournisseur, mapping_dict)
                modal.destroy()
                self.refresh_mapping_display()
                messagebox.showinfo("Succès", "Mappings enregistrés.")
                return
            missing, columns_ = validate_mappings_against_file(file_path, new_mappings)
            if missing is None:
                return
            if missing:
                messagebox.showwarning("Colonnes manquantes", f"Les colonnes suivantes sont absentes du fichier: {', '.join(missing)}\nCorrigez le mapping ou le fichier.")
                return
            set_entity_mappings(self.selected_fournisseur, mapping_dict)
            modal.destroy()
            self.refresh_mapping_display()
            messagebox.showinfo("Succès", "Mappings enregistrés et validés.")
        def preview_mapping():
            file_path = filedialog.askopenfilename(title="Sélectionnez un fichier pour prévisualiser le mapping", filetypes=[("Fichiers supportés", "*.csv *.xlsx *.xls *.txt")])
            if not file_path:
                return
            try:
                header = None if no_header_var.get() else 'infer'
                data = read_dataset_file(file_path, header=header)
                df = data['dataset']
                
                # DEBUG: Show actual column names found in CSV
                print("=== DEBUG: Actual column names in CSV ===")
                for idx, col in enumerate(df.columns):
                    print(f"Column {idx}: '{col}' (type: {type(col)}, repr: {repr(col)})")
                print("=" * 50)
                
                preview_cols = []
                preview_indices = []  # Track column indices for correct data selection
                missing_cols = []
                
                for src_entry, _, _ in row_widgets:
                    src = src_entry.get().strip()
                    found_col = None
                    found_idx = None
                    
                    # Try to resolve as int index if possible
                    try:
                        idx = int(src)
                        if 0 <= idx < len(df.columns):
                            found_col = df.columns[idx]
                            found_idx = idx
                            print(f"DEBUG: Found column by index {idx}: '{found_col}'")
                    except ValueError:
                        # For column names, we need special handling for NTY
                        # Check if this is the problematic NTY file structure
                        if (src in df.columns and 
                            len(df.columns) >= 8 and 
                            str(df.columns[0]).strip().lower() == "codes de produits" and
                            str(df.columns[7]).strip().lower() == "quantites"):
                            
                            # This is the NTY file with misaligned headers
                            if src == "Codes de produits":
                                found_idx = 0  # Use column 0 for product codes (A-AR-004...)
                                found_col = df.columns[0]
                                print(f"DEBUG: NTY special case - '{src}' -> using column index 0 for correct data")
                            elif src == "Quantites":
                                found_idx = 7  # Use column 7 for quantities (1.00...)
                                found_col = df.columns[7]
                                print(f"DEBUG: NTY special case - '{src}' -> using column index 7 for correct data")
                            else:
                                # Try exact match first
                                if src in df.columns:
                                    found_col = src
                                    found_idx = list(df.columns).index(src)
                                    print(f"DEBUG: Found column by exact match: '{found_col}'")
                        else:
                            # Normal column name resolution
                            if src in df.columns:
                                found_col = src
                                found_idx = list(df.columns).index(src)
                                print(f"DEBUG: Found column by exact match: '{found_col}'")
                            else:
                                # Try case-insensitive and trimmed match
                                src_clean = src.strip().lower()
                                for idx, col in enumerate(df.columns):
                                    col_clean = str(col).strip().lower()
                                    if col_clean == src_clean:
                                        found_col = col
                                        found_idx = idx
                                        print(f"DEBUG: Found column by fuzzy match: '{src}' -> '{found_col}'")
                                        break
                    
                    if found_col is not None and found_idx is not None:
                        preview_cols.append(found_col)
                        preview_indices.append(found_idx)
                    else:
                        missing_cols.append(src)
                        print(f"DEBUG: Column NOT found: '{src}'")
                
                if missing_cols:
                    missing_str = ", ".join(missing_cols)
                    available_str = ", ".join([f"{i}:'{col}'" for i, col in enumerate(df.columns)])
                    messagebox.showwarning(
                        "Colonnes non trouvées", 
                        f"Colonnes non trouvées: {missing_str}\n\nColonnes disponibles:\n{available_str}\n\nUtilisez les index numériques (0, 1, 2...) si les noms ne correspondent pas exactement."
                    )
                
                if preview_indices:
                    # Use iloc to select by position for correct data
                    preview_df = df.iloc[:, preview_indices].head(10)
                    # Set proper column names for display
                    preview_df.columns = preview_cols
                    
                    # After building preview_df -----------------------------
                    if 'Codes de produits' in preview_df.columns:
                        preview_df['Codes de produits'] = preview_df['Codes de produits'].astype(str).str.split(';').str[0]
                    if 'Quantites' in preview_df.columns:
                        import pandas as pd
                        preview_df['Quantites'] = pd.to_numeric(preview_df['Quantites'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0).astype(int)
                    
                    preview_modal = ctk.CTkToplevel(modal)
                    preview_modal.title("Prévisualisation du mapping")
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
                messagebox.showerror("Erreur", f"Erreur lors de la prévisualisation: {e}")
                print(f"DEBUG: Preview error: {e}")
                import traceback
                traceback.print_exc()
        add_btn = ctk.CTkButton(modal, text="➕ Ajouter mapping", command=add_mapping)
        add_btn.pack(pady=5)
        preview_btn = ctk.CTkButton(modal, text="👁️ Prévisualiser mapping", command=preview_mapping)
        preview_btn.pack(pady=5)
        save_btn = ctk.CTkButton(modal, text="💾 Enregistrer", command=save_mappings)
        save_btn.pack(pady=5)
        refresh_mapping_table()
