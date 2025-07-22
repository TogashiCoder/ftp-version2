# tests/test_ftp_utils.py
import os
import tempfile
import pytest
from pathlib import Path
from ..functions.functions_FTP import create_ftp_config, charger_infos_ftp

def test_create_ftp_config(monkeypatch):
    # Monkeypatch des variables d'environnement
    monkeypatch.setenv("FTP_HOST_FOURNISSEUR_A", "ftp.example.com")
    monkeypatch.setenv("FTP_USER_FOURNISSEUR_A", "userA")
    monkeypatch.setenv("FTP_PASS_FOURNISSEUR_A", "passA")

    keys = ["FOURNISSEUR_A"]
    config = create_ftp_config(keys)

    assert "FOURNISSEUR_A" in config
    assert config["FOURNISSEUR_A"]["host"] == "ftp.example.com"
    assert config["FOURNISSEUR_A"]["user"] == "userA"
    assert config["FOURNISSEUR_A"]["password"] == "passA"

def test_create_ftp_config_missing(monkeypatch):
    # Absence de variable env utilisateur
    monkeypatch.setenv("FTP_HOST_FOURNISSEUR_B", "ftp.example.com")
    monkeypatch.delenv("FTP_USER_FOURNISSEUR_B", raising=False)
    monkeypatch.setenv("FTP_PASS_FOURNISSEUR_B", "passB")

    keys = ["FOURNISSEUR_B"]
    with pytest.raises(ValueError):
        create_ftp_config(keys)


def test_charger_infos_ftp(tmp_path):
    # Création d'un fichier .env temporaire
    env_content = """
FTP_HOST_FOURNISSEUR_A=ftp.example.com
FTP_USER_FOURNISSEUR_A=userA
FTP_PASS_FOURNISSEUR_A=passA
FTP_HOST_PLATFORM_B=ftp.platform.com
FTP_USER_PLATFORM_B=userB
FTP_PASS_PLATFORM_B=passB
"""
    env_file = tmp_path / ".env"
    env_file.write_text(env_content)

    data, fournisseurs, plateformes = charger_infos_ftp(str(env_file))

    assert "FOURNISSEUR_A" in data
    assert "PLATFORM_B" in data
    assert "host" in data["FOURNISSEUR_A"]
    assert data["FOURNISSEUR_A"]["host"] == "ftp.example.com"
    assert "password" in data["PLATFORM_B"]
    assert data["PLATFORM_B"]["password"] == "passB"
    assert "FOURNISSEUR_A" in fournisseurs
    assert "PLATFORM_B" in plateformes
