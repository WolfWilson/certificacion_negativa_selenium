# app/config.py
import os
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "informes_obtenidos"))
LOG_DIR    = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", BASE_DIR / "backups"))
EXP_ROOT   = Path(os.getenv("EXP_ROOT", "/mnt/expedientes"))

SQL_CONN = os.getenv(
    "SQL_CONN",
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=SQL01,1433;"
    "DATABASE=Aportes;"
    "UID=certbot;PWD=YourStrong!Passw0rd;"
    "Encrypt=yes;TrustServerCertificate=yes;"
)
