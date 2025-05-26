"""
obtener_certificacion_negativa.py
Versión Docker Linux (Xvfb) – Selenium GUI + Page.printToPDF
Descarga / fusiona / sube expedientes PDF usando un servidor FTP o FTPS.
"""

# ── IMPORTS ───────────────────────────────────────────────────
import os
import shutil
import time
import datetime as dt
import base64
import uuid
from pathlib import Path
from contextlib import contextmanager
from ftplib import (
    FTP,
    FTP_TLS,
    error_perm,
    all_errors,        # ── CAMBIO ──
)

from pypdf import PdfReader, PdfWriter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from modules.conexion_db import obtener_cuils_pendientes, marcar_procesado
from config import BASE_DIR, OUTPUT_DIR, LOG_DIR, BACKUP_DIR

# ── PARÁMETROS ────────────────────────────────────────────────
MAX_RETRY   = 3
WAIT_DENY   = 60
WEB_PAUSE   = 10
CHECK_EVERY = int(os.getenv("CHECK_EVERY", "120"))
PAUSA_20S   = 20
PAUSA_5MIN  = 300
KEEP_DAYS   = int(os.getenv("KEEP_DAYS", "30"))
HEADER_NEGA = "servicioswww.anses.gob.ar/censite/antecedentes.aspx"

URL = "https://servicioswww.anses.gob.ar/censite/index.aspx"

FTP_URI      = os.getenv("FTP_URI")
FTP_USERNAME = os.getenv("FTP_USERNAME")
FTP_PASSWORD = os.getenv("FTP_PASSWORD", "").rstrip("\r\n")


# ── Logging sencillo ─────────────────────────────────────────
for d in (OUTPUT_DIR, LOG_DIR, BACKUP_DIR):
    d.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / f"log_{dt.datetime.now():%Y-%m-%d_%H-%M-%S}.txt"
def w(msg: str) -> None:
    """Escribe mensaje en consola y en el log con marca de tiempo."""
    now = dt.datetime.now().strftime("%H:%M:%S")
    line = f"[{now}] {msg}"
    print(line)
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

# Muestra variables críticas (sin exponer la contraseña) ── CAMBIO ──
w(f"🖧 FTP_URI={FTP_URI}")
w(f"👤 FTP_USERNAME={FTP_USERNAME}")
w("🔐 FTP_PASSWORD=<oculto>")
w("🕓 Servicio iniciado")

# ── Selenium (GUI sobre Xvfb) ─────────────────────────────────
opts = Options()
opts.binary_location = "/usr/bin/chromium"
opts.add_argument("--window-size=1366,768")
opts.add_argument("--disable-gpu")
opts.add_argument("--disable-logging")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
CHROME_TMP = f"/tmp/chrome_{uuid.uuid4().hex}"
Path(CHROME_TMP).mkdir()
opts.add_argument(f"--user-data-dir={CHROME_TMP}")

driver = webdriver.Chrome(options=opts)
wait   = WebDriverWait(driver, 30)

# ── FTP HELPERS ───────────────────────────────────────────────
def _build_ftp(debug: int = 0):
    """
    Intenta negociar FTPS explícito (AUTH TLS); si falla,
    retrocede a FTP plano. Devuelve la instancia lista para login().
    """
    # Primer intento: FTPS explícito
    ftp = FTP_TLS(timeout=30)
    ftp.set_debuglevel(debug)
    try:
        ftp.connect(FTP_URI, 21)
        w("🔌 Conectado, intentando AUTH TLS…")
        ftp.auth()       # ⇢ AUTH TLS
        ftp.prot_p()     # ⇢ PROT P (canal de datos cifrado)
        w("🔒 TLS negociado correctamente")
    except Exception as e:
        w(f"ℹ️  TLS no disponible ({e}); usando FTP sin cifrar")
        try:
            ftp.close()
        except Exception:
            pass
        ftp = FTP(timeout=30)
        ftp.set_debuglevel(debug)
        ftp.connect(FTP_URI, 21)
    return ftp

@contextmanager
def ftp_conn(debug: int = 0):
    """
    Context manager para obtener una conexión FTP/FTPS
    con manejo detallado de errores y cierre seguro.
    """
    ftp = _build_ftp(debug)
    try:
        ftp.login(FTP_USERNAME, FTP_PASSWORD)
        w("✅ Login FTP correcto")
        ftp.encoding = "latin-1"   # evita problemas con tildes en Windows
        yield ftp
    except error_perm as e:
        w(f"❌ error_perm: {e}")   # 530, 550, etc.
        raise
    except all_errors as e:
        w(f"❌ all_errors: {e}")   # timeouts, socket, etc.
        raise
    finally:
        try:
            ftp.quit()
            w("🔚 Conexión FTP cerrada")
        except Exception as e:
            w(f"⚠️  Error al cerrar la conexión FTP: {e}")

def ftp_remote_path(expediente: str) -> str:
    """Ejemplo → /2025/E/E-010577-2025/E-010577-2025.pdf"""
    return f"/{expediente[-4:]}/{expediente[0]}/{expediente}/{expediente}.pdf"

def ftp_download(remote: str, local: Path, debug: int = 0):
    w(f"⬇️  Descargando {remote} → {local}")
    with ftp_conn(debug) as ftp, open(local, "wb") as f:
        ftp.retrbinary(f"RETR {remote}", f.write)

def ftp_upload(local: Path, remote: str, debug: int = 0):
    w(f"⬆️  Subiendo {local} → {remote}")
    with ftp_conn(debug) as ftp, open(local, "rb") as f:
        ftp.storbinary(f"STOR {remote}", f)

# ── UTILIDADES ────────────────────────────────────────────────
def dividir(cuil: str):
    """Devuelve prefijo, cuerpo y dígito verificador: 20-12345678-3"""
    return cuil[:2], cuil[2:10], cuil[10]

def fusionar(orig: Path, nuevo: Path):
    w = PdfWriter()
    for p in (orig, nuevo):
        for page in PdfReader(p).pages:
            w.add_page(page)
    tmp = orig.with_suffix(".tmp.pdf")
    with tmp.open("wb") as f:
        w.write(f)
    tmp.replace(orig)

def ya_negativa(pdf: Path) -> bool:
    r = PdfReader(pdf)
    for i in range(11, min(len(r.pages)-1, 15)+1):
        if HEADER_NEGA in (r.pages[i].extract_text() or "").lower():
            return True
    return False

def save_pdf(dest: Path):
    data = driver.execute_cdp_cmd(
        "Page.printToPDF",
        {"printBackground": True, "preferCSSPageSize": True}
    )
    dest.write_bytes(base64.b64decode(data["data"]))

def cleanup_output():
    límite = dt.datetime.now() - dt.timedelta(days=KEEP_DAYS)
    for fp in OUTPUT_DIR.glob("*.pdf"):
        if dt.datetime.fromtimestamp(fp.stat().st_mtime) < límite:
            fp.unlink()
            w(f"🗑️  Eliminado {fp.name}")

# ── PROCESO POR CUIL ──────────────────────────────────────────
def procesar(id_tarea: int, cuil: str, expediente: str):
    remote_pdf = ftp_remote_path(expediente)
    tmp_local  = OUTPUT_DIR / f"{expediente}_orig.pdf"

    # 1▪ descarga original
    try:
        ftp_download(remote_pdf, tmp_local, debug=0)
    except Exception as e:
        raise FileNotFoundError(f"No se pudo descargar {remote_pdf}: {e}")

    # 2▪ controla si ya tiene negativa
    if ya_negativa(tmp_local):
        marcar_procesado(id_tarea)
        w(f"ℹ️  {cuil} | {expediente} ya tenía negativa")
        tmp_local.unlink(missing_ok=True)
        return False

    # 3▪ genera cert. vía web
    for intento in range(1, MAX_RETRY + 1):
        driver.get(URL)
        try:
            wait.until(EC.presence_of_element_located((By.ID, "txtCuitPre")))
        except:
            time.sleep(WAIT_DENY)
            continue

        pre, doc, dv = dividir(cuil)
        driver.find_element(By.ID, "txtCuitPre").send_keys(pre)
        driver.find_element(By.ID, "txtCuitDoc").send_keys(doc)
        driver.find_element(By.ID, "txtCuitDV").send_keys(dv)
        driver.find_element(By.ID, "btnVerificar").click()

        wait.until(
            lambda d: "Antecedentes" in d.page_source
            or "Acceso denegado." in d.page_source
        )

        if "Acceso denegado." in driver.page_source:
            w(f"🚫 Acceso denegado ({intento}/{MAX_RETRY}) {cuil}")
            time.sleep(WAIT_DENY)
            continue

        nueva = OUTPUT_DIR / f"{cuil}_neg.pdf"
        save_pdf(nueva)
        time.sleep(WEB_PAUSE)

        # 4▪ backup y fusión
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(tmp_local, BACKUP_DIR / f"{expediente}_{ts}.pdf")
        fusionar(tmp_local, nueva)

        # 5▪ sube el PDF fusionado
        ftp_upload(tmp_local, remote_pdf, debug=0)

        marcar_procesado(id_tarea)
        w(f"[✓] {cuil} | {expediente} procesado")
        nueva.unlink(missing_ok=True)
        tmp_local.unlink(missing_ok=True)
        return True

    raise RuntimeError("Acceso denegado persistente")

# ── BUCLE PRINCIPAL ───────────────────────────────────────────
try:
    while True:
        cleanup_output()
        tareas = obtener_cuils_pendientes()
        w(f"🔄 Pendientes: {len(tareas)}")

        ok = err = omit = 0
        for i, (id_t, cuil, exp) in enumerate(tareas, 1):
            try:
                if procesar(id_t, cuil, exp):
                    ok += 1
                else:
                    omit += 1
            except Exception as e:
                err += 1
                w(f"[✗] {cuil}|{exp} -> {e}")
            time.sleep(PAUSA_5MIN if i % 4 == 0 else PAUSA_20S)

        w(f"✅ Ciclo OK={ok} OMIT={omit} ERR={err}")
        time.sleep(CHECK_EVERY)

finally:
    driver.quit()
    shutil.rmtree(CHROME_TMP, ignore_errors=True)
    w("🛑 Servicio detenido")
