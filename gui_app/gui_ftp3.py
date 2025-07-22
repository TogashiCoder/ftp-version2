import os
import sys
import time 
import threading
import customtkinter as ctk

from dotenv import dotenv_values  
from functions.functions_update import *
from tkinter import filedialog, messagebox
from config.temporary_data_list import current_dataFiles
from functions.functions_FTP import upload_updated_files_to_marketplace
from utils import get_valid_fournisseurs, get_valid_platforms


class MajFTPFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        # Common button style with orange theme
        orange_hover =  "#ef8018"#"#FFA500"   # Darker orange on hover
        self.button_kwargs = {            
            "font": ("Arial", 15),
            "height": 35,
            "corner_radius": 8,
            "fg_color": "#253d61", #"#2d4d7e",  #"#c5c7c8", #"#3B8ED0",
            "hover_color": orange_hover,
            "text_color": "white",
        }
        button_MAJ_kwargs = {            
            "font": ("Arial", 17),
            "height": 55,
            "corner_radius": 8,
            "fg_color": "#253d61", #"#2d4d7e",  #"#c5c7c8", #"#3B8ED0",
            "hover_color": orange_hover,
            "text_color": "white",
        }

        self.checkbox_all_style = {
            'checkmark_color': "#FCBE61",
            'hover_color': orange_hover,
            'fg_color': "#253d61", 
            'checkbox_width': 22,
            'checkbox_height': 20,
            'border_width':1,
            'font': ("Segoe UI", 13, "bold"),
        }
        self.checkbox_mini_style = {
            'checkmark_color': "#FCBE61",
            'hover_color': orange_hover,
            'fg_color': "#253d61", 
            'checkbox_width': 16,
            'checkbox_height': 14,
            'border_width':1,
            'font': ("Segoe UI", 13),
        }
        frames_dark_kwargs={
            "fg_color": "transparent", 
            "border_width": 1, 
            "border_color": "#555555"
        }
        frames_light_kwargs={
            "fg_color": "transparent", 
            "border_width": 1, 
            "border_color": "#AAAAAA"
        }
        # Police utilisée
        title_font = ("Segoe UI", 20, "bold")

        # ------------------------------------ Titre ------------------------------
        label = ctk.CTkLabel(self, text="Synchronisation des Stocks : Fournisseurs → Plateformes", font=title_font)
        label.pack(pady=(10, 20))

        self.platform_file = None
        self.fournisseur_files = []
        # -------------------------------------------------------------------------

        # ------------------------- Bloc 1 : Exécution FTP ------------------------
        self.block1 = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent", border_width=1, border_color="#555555")
        self.block1.pack(fill="x", pady=(45,5))

        self.execution_label = ctk.CTkLabel(self.block1, text="Synchronisation Automatique :", anchor="w", font=("Segoe UI", 13, "bold"))
        self.execution_label.pack(anchor="w", padx=15)
        
        self.execute_btn = ctk.CTkButton(self.block1, text="🖧      Mettre à Jour via FTP       🖧", command=self.run_update, **button_MAJ_kwargs)
        self.execute_btn.pack(padx=15, pady=(0, 25))
        # -------------------------------------------------------------------------
        


        # ----------------------- Bloc 2 : Listes Fournisseurs et Plateformes -----------------------
        self.block2 = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")#, border_width=1, border_color="#555555")
        self.block2.pack(fill="x", pady=12)
        
        # Fournisseurs
        self.block2_a = ctk.CTkFrame(self.block2, corner_radius=10, fg_color="transparent", border_width=1, border_color="#555555")
        self.block2_a.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.fournisseurs_var = ctk.BooleanVar(value=True)
        self.fournisseurs_checkbox = ctk.CTkCheckBox(
            self.block2_a,
            text="Fournisseurs disponibles :",
            **self.checkbox_all_style, 
            variable=self.fournisseurs_var,
            command=self.on_fournisseurs_checkbox_change 
        )
        self.fournisseurs_checkbox.pack(anchor="w", padx=15)

        list_container_a = ctk.CTkFrame(self.block2_a, fg_color="transparent")
        list_container_a.pack(fill="x", padx=20, pady=(5, 10))

        self.fournisseur_list = ctk.CTkScrollableFrame(list_container_a, height=80, width=200, fg_color="transparent")
        self.fournisseur_list.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Plateformes
        self.block2_b = ctk.CTkFrame(self.block2, corner_radius=10, fg_color="transparent", border_width=1, border_color="#555555")
        self.block2_b.pack(side="right", fill="both", expand=True, padx=(8, 0))

        self.platforms_var = ctk.BooleanVar(value=True)
        self.platforms_checkbox = ctk.CTkCheckBox(
            self.block2_b,
            text="Plateformes disponibles :",
            **self.checkbox_all_style, 
            variable=self.platforms_var,
            command=self.on_platforms_checkbox_change 
        )

        self.platforms_checkbox.pack(anchor="w", padx=15)
        
        list_container_b = ctk.CTkFrame(self.block2_b, fg_color="transparent")
        list_container_b.pack(fill="x", padx=20, pady=(5, 10))
        
        self.plateform_list = ctk.CTkScrollableFrame(list_container_b, fg_color="transparent", height=80, width=200)
        self.plateform_list.pack(side="left", fill="both", expand=True)
        # -------------------------------------------------------------------------

        


        # ----------------------- Bloc 3 : Affichage du log -----------------------
        self.block3 = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent", border_width=1, border_color="#555555")
        self.block3.pack(fill="x", pady=5)

        self.log_label = ctk.CTkLabel(self.block3, text="Journal de Mise à Jour :", anchor="w", font=("Segoe UI", 13, "bold"))
        self.log_label.pack(anchor="w", padx=10)
        self.log_frame = ctk.CTkScrollableFrame(self.block3, height=130, fg_color="#2e2e2e", corner_radius=0) # , fg_color="#2e2e2e"
        self.log_frame.pack(fill="x", padx=15, pady=(3, 5))


        self.fournisseur_vars = {}  
        self.platform_vars = {} 

        self.load_ftp_infos()

        # -------------------------------------------------------------------------
    
    
    def get_selected_fournisseurs(self):
        return [name for name, var in self.fournisseur_vars.items() if var.get()]

    
    def get_selected_platforms(self):
        return [name for name, var in self.platform_vars.items() if var.get()]
    

    def on_fournisseurs_checkbox_change(self):
        if self.fournisseurs_var.get():
            for var in self.fournisseur_vars.values():
                var.set(True)
                var.configure(state="disabled")
            print('Fournisseurs selectionés: ', self.get_selected_fournisseurs())
            list_fournisseurs = get_valid_fournisseurs()
        else:
            for var in self.fournisseur_vars.values():
                var.set(False)
                var.configure(state="normal")
            print('Fournisseurs selectionés: ', self.get_selected_fournisseurs())
            list_fournisseurs = []
        return list_fournisseurs


    def on_platforms_checkbox_change(self):
        if self.platforms_var.get():
            for var in self.platform_vars.values():
                var.set(True)
            print('Platforms selectionés: ', self.get_selected_platforms())
            list_platforms = get_valid_platforms()
        else:
            for var in self.platform_vars.values():
                var.set(False)
            print('Platforms selectionés: ', self.get_selected_platforms())
            list_platforms = []
        return list_platforms



    def get_latest_file(self, folder_path=LOG_FOLDER):
        files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        
        if not files:
            return None  # Aucun fichier

        latest_file = max(files, key=os.path.getctime)  # ou os.path.getmtime
        return latest_file


    def run_update(self):
        """# ---------------- Nettoyage du log précédent ----------------
        for widget in self.log_frame.winfo_children():
            widget.destroy()
        
        self.log_running = True  # Pour arrêter plus tard

        # ---------------- Afficher le début du log ----------------
        txt_line = '-------------- * * * Start * * * --------------'
        label = ctk.CTkLabel(self.log_frame, text=txt_line, anchor="w", text_color="white")
        label.pack(anchor="w", pady=1, padx=5)

        self.log_file_path = self.get_latest_file()
      
        # Lancement de la lecture dynamique
        threading.Thread(target=self.tail_log_file, daemon=True).start()

        # Lancement du traitement principal
        threading.Thread(target=self._run_update_process, daemon=True).start()
        """
        list_fournisseurs = self.on_fournisseurs_checkbox_change()
        list_platforms = self.on_platforms_checkbox_change()

        print('---list_fournisseurs', list_fournisseurs)
        print('---list_platforms', list_platforms)






    def _run_update_process(self):
        try:
            # ---------------------- Loding Data via FTP ---------------------
            #fichiers_fournisseurs, fichiers_platforms = config_and_load_data_from_FTP()

            selected_fournisseurs = self.get_selected_fournisseurs()
            selected_plateformes = self.get_selected_platforms()

            fichiers_fournisseurs = {k: v for k, v in load_fournisseurs_config().items() if k in selected_fournisseurs and k in get_valid_fournisseurs()}
            fichiers_platforms = {k: v for k, v in load_plateformes_config().items() if k in selected_plateformes and k in get_valid_platforms()}

            """
            # --------------------- All Fournisseurs / Platforms ----------------------
            list_fournisseurs = self.on_fournisseurs_checkbox_change()
            list_platforms = self.on_platforms_checkbox_change()

            # --------------------- Few Fournisseurs / Platforms ----------------------

            
            # ---------------------- Load data From FTP to Local ----------------------

            fichiers_fournisseurs =  load_fournisseurs_ftp(list_fournisseurs)
                                                #  dict('FOURNISSEUR_A': chemin fichierA , 
                                                #       'FOURNISSEUR_B': chemin fichierB,... )

            fichiers_platforms = load_platforms_ftp(list_platforms)

            """



            # ----------------------- Loding Local Data ----------------------
            fichiers_fournisseurs, fichiers_platforms = current_dataFiles()

            # ---------------------- Loding Data via FTP ---------------------
           
            fournisseurs_files_valides = check_ready_files(title_files='Fournisseurs', downloaded_files=fichiers_fournisseurs)
            platforms_files_valides = check_ready_files(title_files='Plateformes', downloaded_files=fichiers_platforms)
                
            # ------------------- Mettre A Jour le stock ---------------------
            is_store_updated = mettre_a_jour_Stock(platforms_files_valides, fournisseurs_files_valides)

            if is_store_updated:

                logger.info('-- -- ✅ -- --  Mise à jour effectuée -- -- ✅ -- -- ')
                upload_updated_files_to_marketplace(dry_run=False)
                messagebox.showinfo("Succès", "✅ La mise à jour a été effectuée avec succès.\nFiles have been uploaded to marketplaces FTP.")
                 
                # Supprimer ancien bouton s'il existe
                if hasattr(self, 'open_update_btn') and self.open_update_btn.winfo_exists():
                    self.open_update_btn.destroy()
                    
                # Bouton pour accéder au dossier mis à jour
                self.open_update_btn = ctk.CTkButton(
                    self.log_frame,
                    text="📂 Accéder aux fichiers mis à jour",
                    command=self.open_update_folder,
                    **self.button_kwargs
                )
                self.open_update_btn.pack(padx=15, pady=(0, 5))
        
            else:
                messagebox.showerror("Error", "-- -- ❌ -- --  Error de mise à jour  -- -- ❌ -- --")
                logger.info('-- -- ❌ -- --  Error de mise à jour  -- -- ❌ -- -- ')
            
            # Fin du suivi
            self.log_running = False

        except Exception as e:
            logger.error(f"❌ Erreur : {e}")
            messagebox.showerror("Erreur", str(e))
            # Fin du suivi
            self.log_running = False
        
   






    def tail_log_file(self):
        """Lit le fichier log ligne par ligne pendant qu'il est en cours d'écriture."""
        # Attend que le fichier existe
        while not os.path.exists(self.log_file_path):
            time.sleep(0.1)

        with open(self.log_file_path, "r", encoding="utf-8") as f:
            # Aller à la fin du fichier existant
            f.seek(0, os.SEEK_END)

            while self.log_running:
                line = f.readline()
                if line:
                    self.after(0, lambda l=line: self.add_log_line(l.strip()))
                else:
                    time.sleep(0.2)  # Pause courte avant de re-tester


    def add_log_line(self, line):
        color = "white"
        if "❌" in line or "Erreur" in line:
            color = "#FA6A6A"
        elif "✅" in line or "Succès" in line:
            color = "#9CEC5B"
        elif "⚠️" in line :
            color = "#F1D639"

        label = ctk.CTkLabel(self.log_frame, text=line, anchor="w",  text_color=color, font=("Segoe UI Emoji", 13))
        label.pack(anchor="w", pady=0, padx=2)

    
    def open_update_folder(self):
        dossier_mis_a_jour = UPDATED_FILES_PATH_RACINE  # à adapter si ton dossier de sortie est différent

        try:
            if os.path.exists(dossier_mis_a_jour):
                if os.name == 'nt':  # Windows
                    os.startfile(dossier_mis_a_jour)
                elif os.name == 'posix':  # MacOS, Linux
                    subprocess.Popen(['xdg-open', dossier_mis_a_jour])
            else:
                messagebox.showwarning("Dossier introuvable", f"Le dossier {dossier_mis_a_jour} n'existe pas.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le dossier : {str(e)}")

    
    def populate_list(self, f_container, f_items, p_container, p_items):

        for f_item in f_items:
            var = ctk.BooleanVar(value=True)
            self.fournisseur_vars[f_item] = var
            checkbox = ctk.CTkCheckBox(
                f_container, 
                text=f_item, 
                variable=var, 
                **self.checkbox_mini_style
            )
            checkbox.pack(anchor="w")

        for p_item in p_items:
            var = ctk.BooleanVar(value=True)
            self.platform_vars[p_item] = var
            checkbox = ctk.CTkCheckBox(
                p_container, 
                text=p_item, 
                variable=var, 
                **self.checkbox_mini_style
            )
            checkbox.pack(anchor="w")

            

    def show_logs(self, LOG_FILE_PATH):
        if not os.path.exists(LOG_FILE_PATH):
            label = ctk.CTkLabel(self.log_frame, text="Erreur: Fichier de log introuvable.", anchor="w", text_color="white")
            label.pack(anchor="w", pady=1, padx=5)
            return

        # Lire les lignes à l'avance
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            self.log_lines = f.readlines()

        self.current_line_index = 0
        self.display_next_log_line()


    def display_next_log_line(self):
        if self.current_line_index < len(self.log_lines):
            line = self.log_lines[self.current_line_index].strip()
            label = ctk.CTkLabel(self.log_frame, text=line, anchor="w", text_color="white")
            label.pack(anchor="w", pady=0, padx=2)

            self.current_line_index += 1

            # Affiche la prochaine ligne après 10 ms
            self.after(10, self.display_next_log_line)
    
    
    def load_ftp_infos(self):
        fournisseurs = get_valid_fournisseurs()
        plateformes = get_valid_platforms()
        for widget in self.fournisseur_list.winfo_children():
            widget.destroy()
        for widget in self.plateform_list.winfo_children():
            widget.destroy()
        self.populate_list(self.fournisseur_list, fournisseurs, self.plateform_list, plateformes)
