# app/config.py
import os
from pathlib import Path

#constants ftp
FTP_URI      = os.getenv("FTP_URI")
FTP_USER     = os.getenv("FTP_USERNAME")
FTP_PASS     = os.getenv("FTP_PASSWORD")
FTP_BASE     = os.getenv("FTP_BASE", "/")


# ── Rutas ───────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "informes_obtenidos"))
LOG_DIR    = Path(os.getenv("LOG_DIR",    BASE_DIR / "logs"))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", BASE_DIR / "backups"))
EXP_ROOT   = Path(os.getenv("EXP_ROOT",   "/mnt/expedientes"))

# ── Cadena de conexión ODBC ─────────────────────────────────────────────
SQL_CONN = os.getenv(
    "SQL_CONN",
    # Fallback sólo para uso local fuera de Docker
    "DRIVER={FreeTDS};"
    "SERVERNAME=SQL01_SERVER;"
    "DATABASE=Aportes;"
    "UID=Usr_wilson;PWD=MiContraseñaSegura;"
    "TrustServerCertificate=yes"
)
