import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from utils import get_valid_fournisseurs, get_valid_platforms

def test_ftp_validation():
    print("\nTesting FTP Validation")
    print("=====================")
    
    # Test with a shorter timeout for quicker feedback
    timeout = 3
    
    print("\nValidating Supplier FTP Connections")
    print("---------------------------------")
    valid_fournisseurs = get_valid_fournisseurs(timeout=timeout)
    
    print("\nValidating Platform FTP Connections")
    print("--------------------------------")
    valid_platforms = get_valid_platforms(timeout=timeout)
    
    print("\nSummary")
    print("-------")
    print(f"Valid Suppliers: {valid_fournisseurs}")
    print(f"Valid Platforms: {valid_platforms}")

if __name__ == "__main__":
    test_ftp_validation()
