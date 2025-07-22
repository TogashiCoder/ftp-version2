from pathlib import Path
import os

def afficher_structure_dossier(chemin, niveau=0, max_niveau=2, prefixe=""):
    if niveau >= max_niveau:
        return
    for element in os.listdir(chemin):
        chemin_complet = os.path.join(chemin, element)
        print(prefixe + "|-- " + element)
        if os.path.isdir(chemin_complet):
            afficher_structure_dossier(chemin_complet, niveau + 1, max_niveau, prefixe + "    ")

chemin = Path("D:/18_Hassan/Drox_Update_Store")
afficher_structure_dossier(chemin)