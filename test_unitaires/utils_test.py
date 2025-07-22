import pytest
from pathlib import Path
import os

# On importe les fonctions à tester (adapter selon ton organisation de fichiers)
from ..utils import (
    keep_data_with_header_specified,
    separer_fournisseurs_et_plateformes,
    verifier_fichiers_existants,
)


# Mock simple pour read_yaml_file
def mock_read_yaml_file(path):
    return {
        "FOURNISSEUR_A": {
            "nom_reference": "ref_id",
            "quantite_stock": "stock_col"
        },
        "FOURNISSEUR_B": {
            "nom_reference": "id_col",
            "quantite_stock": "qty_col"
        }
    }


# Patch la fonction read_yaml_file dans ton module
import utils
utils.read_yaml_file = mock_read_yaml_file

def test_keep_data_with_header_specified_valid():
    fichiers = {
        "FOURNISSEUR_A": "/chemin/fichierA.csv",
        "FOURNISSEUR_B": "/chemin/fichierB.csv",
        "FOURNISSEUR_C": "/chemin/fichierC.csv"  # Non dans yaml mock
    }
    result = keep_data_with_header_specified(fichiers, "fake_path.yaml")
    assert "FOURNISSEUR_A" in result
    assert "FOURNISSEUR_B" in result
    assert "FOURNISSEUR_C" not in result
    assert result["FOURNISSEUR_A"]["chemin_fichier"] == "/chemin/fichierA.csv"
    assert result["FOURNISSEUR_A"]["nom_reference"] == "ref_id" or result["FOURNISSEUR_A"]["quantite_stock"] == "stock_col"


def test_separer_fournisseurs_et_plateformes():
    data = {
        "FOURNISSEUR_X": 1,
        "PLATFORM_Y": 2,
        "FOURNISSEUR_Z": 3,
        "PLATFORM_W": 4
    }
    fournisseurs, plateformes = separer_fournisseurs_et_plateformes(data)
    assert all(k.startswith("FOURNISSEUR") for k in fournisseurs)
    assert all(k.startswith("PLATFORM") for k in plateformes)
    assert len(fournisseurs) == 2
    assert len(plateformes) == 2


def test_verifier_fichiers_existants(tmp_path):
    # Créer un fichier temporaire valide
    fichier_valide = tmp_path / "fichier_valide.csv"
    fichier_valide.write_text("test")

    data = {
        "FOURNISSEUR_OK": {"chemin_fichier": str(fichier_valide)},
        "FOURNISSEUR_MISSING": {"chemin_fichier": "/chemin/inexistant.csv"},
        "FOURNISSEUR_NO_PATH": {}
    }

    result = verifier_fichiers_existants(data)
    assert "FOURNISSEUR_OK" in result
    assert "FOURNISSEUR_MISSING" not in result
    assert "FOURNISSEUR_NO_PATH" not in result