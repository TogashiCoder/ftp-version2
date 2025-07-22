import os 
import sys 
import customtkinter as ctk
from PIL import Image
from pathlib import Path

# Détermination du répertoire racine selon le contexte (script ou exécutable)
if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys.executable).parent
else:
    ROOT_DIR = Path(__file__).resolve().parents[1]

# Ajout au path pour les imports relatifs
sys.path.append(str(ROOT_DIR))
# sys.path.append(str(Path(__file__).resolve().parent.parent))

from gui_app.gui_ftp import MajFTPFrame
from gui_app.gui_manuelle_maj import MajManuelleFrame
from gui_app.gui_fournisseurs import FournisseurAdminFrame
from gui_app.gui_platforms import PlateformFrame
from gui_app.gui_verification import VerificationFrame
from gui_app.gui_configuration import ConfigurationFrame

from utils import get_resource_path
from config.config_path_variables import *

# Configuration CTk
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MainApp(ctk.CTk):
    """Application principale de mise à jour des fichiers plateformes."""

    def __init__(self):
        super().__init__()

        self.title("Mise à Jour des Fichiers Plateformes")
        # Taille désirée
        window_width = 1100
        window_height = 680
        self._set_window_geometry(window_width, window_height)

        # Définir les zones principales
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.pack(side="left", fill="y")

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(side="right", expand=True, fill="both")

        # Initialisation des différentes interfaces
        self.frames = {
            "MAJFTP": MajFTPFrame(self.main_frame),
            "MAJManual": MajManuelleFrame(self.main_frame),
            "fournisseur_admin": FournisseurAdminFrame(self.main_frame),
            "plateform": PlateformFrame(self.main_frame),
            "verification": VerificationFrame(self.main_frame),
            "configuration": ConfigurationFrame(self.main_frame)
        }

        self.init_sidebar()
        self.show_frame("MAJFTP")
    
    def _set_window_geometry(self, width: int, height: int):
        """Centre et redimensionne la fenêtre."""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width - width) / 2)
        y = int((screen_height - height) / 2)

        # Appliquer taille + position centrée
        self.geometry(f"{width}x{height}+{x}+{y}")


    def init_sidebar(self):
        # ---------------------- Logo -----------------------
        """Initialise la barre latérale avec le logo et le menu."""

        image_path = f'{IMG_SRC}/DROX-Logo.png'  # chemin vers l'image
        image_path = get_resource_path(image_path)
        image = ctk.CTkImage(light_image=Image.open(image_path), size=(124, 124))

        # Créer un cadre autour de l'image
        image_frame = ctk.CTkFrame(self.sidebar, width=140, height=80, corner_radius=6, fg_color="#D9D9D9")
        image_frame.pack(pady=5)
        image_frame.pack_propagate(False)

        # Ajouter le label avec l'image dans le cadre
        img_label = ctk.CTkLabel(image_frame, image=image, text="", fg_color="transparent")
        img_label.pack(expand=True)
        # ---------------------------------------------------

        # ---------------------- Menu -----------------------
        # Orange color palette
        orange_hover =  "#ef8018"#"#FFA500"   # Darker orange on hover
        
        # Common button style with orange theme
        button_kwargs = {
            "master": self.sidebar,
            "font": ("Arial", 15),
            "height": 35,
            "corner_radius": 8,
            "fg_color": "#253d61", #"#2d4d7e",  #"#c5c7c8", #"#3B8ED0",
            "hover_color": orange_hover,
            "text_color": "white",
        }

        # Buttons
        ctk.CTkButton(text="🏠 Accueil", command=lambda: self.show_frame("MAJFTP"), **button_kwargs).pack(fill="x", padx=10, pady=(15,5))
        ctk.CTkButton(text="📁 MAJ Manuelle", command=lambda: self.show_frame("MAJManual"), **button_kwargs).pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(text="🔑 Connexions Fournisseurs", command=lambda: self.show_frame("fournisseur_admin"), **button_kwargs).pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(text="🔑 Connexions Plateformes", command=lambda: self.show_frame("plateform"), **button_kwargs).pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(text="✅ Vérification", command=lambda: self.show_frame("verification"), **button_kwargs).pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(text="⚙️ configuration", command=lambda: self.show_frame("configuration"), **button_kwargs).pack(fill="x", padx=10, pady=5)


        # --------------------------- Mode sombre --------------------------
        # Spacer pour pousser le switch en bas
        ctk.CTkLabel(self.sidebar, text="").pack(expand=True)

        # Switch pour le mode sombre / clair
        self.theme_switch = ctk.CTkSwitch(
            self.sidebar,
            text="Mode Sombre",
            command=self.toggle_theme,
            onvalue="dark",
            offvalue="light"
        )
        self.theme_switch.pack(pady=20)
        self.theme_switch.select() 

    def toggle_theme(self):
        """Bascule entre le mode sombre et clair."""
        selected_theme = self.theme_switch.get()
        ctk.set_appearance_mode(selected_theme)

    def clear_main_frame(self):
        """Cache tous les cadres de la zone principale."""
        for frame in self.frames.values():
            frame.pack_forget()


    def show_frame(self, name: str):
        """Affiche l'interface correspondant à `name`."""
        self.clear_main_frame()
        self.frames[name].pack(fill="both", expand=True)

    """    
    @staticmethod
    def get_resource_path(relative_path):     # used when generating .exe
        '''Récupère le chemin absolu vers une ressource, compatible PyInstaller ou non.'''
        try:
            base_path = sys._MEIPASS  # PyInstaller crée cette variable en mode .exe
        except AttributeError:
            base_path = os.path.abspath(".")  # En mode développement
        return os.path.join(base_path, relative_path)

    """

if __name__ == "__main__":
    try:
        app = MainApp()
        app.mainloop()
    except Exception as e:
        import traceback
        print("Erreur lors du démarrage de l'interface :")
        traceback.print_exc()
        input("Appuyez sur Entrée pour quitter...")
