import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from utils import load_fournisseurs_config, load_plateformes_config

def test_configs():
    print("\nTesting configuration loading:")
    print("==============================")
    
    print("\nTesting fournisseurs config:")
    print("----------------------------")
    fournisseurs = load_fournisseurs_config()
    print(f"Number of fournisseurs: {len(fournisseurs)}")
    print("Fournisseurs found:", list(fournisseurs.keys()))
    
    print("\nTesting plateformes config:")
    print("---------------------------")
    plateformes = load_plateformes_config()
    print(f"Number of plateformes: {len(plateformes)}")
    print("Plateformes found:", list(plateformes.keys()))

if __name__ == "__main__":
    test_configs()
