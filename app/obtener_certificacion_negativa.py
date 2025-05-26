"""
obtener_certificacion_negativa.py
─────────────────────────────────
Descarga la Certificación Negativa de ANSES, la fusiona inmediatamente
con el PDF del expediente alojado en el share SMB y marca la tarea
como procesada en la BD.

   • /data/salida            : PDFs temporales <CUIL>_neg.pdf
   • /data/expedientes       : Share UNC \\fs01\Digitalizacion_Jubilaciones
   • /data/logs              : <timestamp>.txt + salida consola
   • /data/backups           : copia del PDF original antes de fusionar
"""

# ── IMPORTS ───────────────────────────────────────────────────
import os, shutil, time, datetime as dt, base64, uuid, sys, traceback
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from modules.conexion_db import obtener_cuils_pendientes, marcar_procesado
from config import LOG_DIR, BACKUP_DIR

# ── CONSTANTES ───────────────────────────────────────────────
MAX_RETRY   = 3
WAIT_DENY   = 60
WEB_PAUSE   = 10
CHECK_EVERY = int(os.getenv("CHECK_EVERY", "120"))      # s
PAUSA_20S   = 20
PAUSA_5MIN  = 300
KEEP_DAYS   = int(os.getenv("KEEP_DAYS", "30"))
HEADER_NEGA = "servicioswww.anses.gob.ar/censite/antecedentes.aspx"
URL         = "https://servicioswww.anses.gob.ar/censite/index.aspx"

NEG_DIR   = Path("/data/salida")
EXP_ROOT  = Path("/data/expedientes")

for d in (NEG_DIR, LOG_DIR, BACKUP_DIR):
    d.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / f"log_{dt.datetime.now():%Y-%m-%d_%H-%M-%S}.txt"
def w(msg: str, err: bool = False) -> None:
    ts = dt.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {'❌' if err else '•'} {msg}"
    print(line, file=sys.stderr if err else sys.stdout, flush=True)
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

w("🕓 Servicio iniciado — modo UNC")

# ── Selenium (Xvfb) ──────────────────────────────────────────
opts = Options()
opts.binary_location = "/usr/bin/chromium"
opts.add_argument("--disable-gpu")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--disable-logging")
opts.add_argument("--window-size=1366,768")
CHROME_TMP = f"/tmp/chrome_{uuid.uuid4().hex}"
Path(CHROME_TMP).mkdir()
opts.add_argument(f"--user-data-dir={CHROME_TMP}")

driver = webdriver.Chrome(options=opts)
wait   = WebDriverWait(driver, 30)

# ── UTILIDADES ───────────────────────────────────────────────
def dividir_cuil(cuil: str):
    return cuil[:2], cuil[2:10], cuil[10]

def ya_negativa(pdf: Path) -> bool:
    try:
        r = PdfReader(pdf)
        for i in range(11, min(len(r.pages)-1, 15)+1):
            if HEADER_NEGA in (r.pages[i].extract_text() or "").lower():
                return True
    except Exception as e:
        w(f"No se pudo leer {pdf}: {e}", err=True)
    return False

def save_pdf(dest: Path):
    data = driver.execute_cdp_cmd(
        "Page.printToPDF",
        {"printBackground": True, "preferCSSPageSize": True}
    )
    dest.write_bytes(base64.b64decode(data["data"]))

def fusionar_pdfs(orig: Path, nueva: Path):
    w_pdf = PdfWriter()
    for p in (orig, nueva):
        for page in PdfReader(p).pages:
            w_pdf.add_page(page)
    tmp = orig.with_suffix(".tmp.pdf")
    with tmp.open("wb") as f:
        w_pdf.write(f)
    tmp.replace(orig)

def exp_pdf_path(expediente: str) -> Path:
    """Devuelve la ruta en /data/expedientes según patrón Año/Letra/…"""
    return EXP_ROOT / expediente[-4:] / expediente[0] / expediente / f"{expediente}.pdf"

def cleanup_dirs():
    límite = dt.datetime.now() - dt.timedelta(days=KEEP_DAYS)
    for root in (NEG_DIR, BACKUP_DIR):
        for fp in root.glob("*.pdf"):
            if dt.datetime.fromtimestamp(fp.stat().st_mtime) < límite:
                fp.unlink(missing_ok=True)

# ── PROCESO PRINCIPAL POR CUIL ───────────────────────────────
def procesar(id_tarea: int, cuil: str, expediente: str):
    orig_pdf = exp_pdf_path(expediente)
    if not orig_pdf.exists():
        raise FileNotFoundError(f"{orig_pdf} no existe en el share")

    if ya_negativa(orig_pdf):
        marcar_procesado(id_tarea)
        w(f"ℹ️  {expediente} ya contenía negativa")
        return False

    neg_pdf = NEG_DIR / f"{cuil}_neg.pdf"

    # –– Generar Certificación Negativa –––––––––––––––––––––––
    for intento in range(1, MAX_RETRY + 1):
        driver.get(URL)
        if not wait.until(lambda d: d.find_elements(By.ID, "txtCuitPre")):
            time.sleep(WAIT_DENY); continue

        pre, doc, dv = dividir_cuil(cuil)
        driver.find_element(By.ID, "txtCuitPre").send_keys(pre)
        driver.find_element(By.ID, "txtCuitDoc").send_keys(doc)
        driver.find_element(By.ID, "txtCuitDV").send_keys(dv)
        driver.find_element(By.ID, "btnVerificar").click()

        wait.until(lambda d: "Antecedentes" in d.page_source
                             or "Acceso denegado." in d.page_source)

        if "Acceso denegado." in driver.page_source:
            w(f"Acceso denegado intento {intento}/{MAX_RETRY} — {cuil}")
            time.sleep(WAIT_DENY); continue

        save_pdf(neg_pdf)
        time.sleep(WEB_PAUSE)
        break
    else:
        raise RuntimeError("Acceso denegado persistente tras 3 intentos")

    # –– Fusionar y respaldar –––––––––––––––––––––––––––––––––
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(orig_pdf, BACKUP_DIR / f"{expediente}_{ts}.pdf")

    fusionar_pdfs(orig_pdf, neg_pdf)
    neg_pdf.unlink(missing_ok=True)

    marcar_procesado(id_tarea)
    w(f"[✓] {expediente} fusionado correctamente")
    return True

# ── LOOP INFINITO ────────────────────────────────────────────
try:
    while True:
        cleanup_dirs()
        tareas = obtener_cuils_pendientes()
        w(f"🔄 Tareas pendientes: {len(tareas)}")

        ok=err=omit=0
        for i, (id_t, cuil, exp) in enumerate(tareas, 1):
            try:
                if procesar(id_t, cuil, exp):
                    ok += 1
                else:
                    omit += 1
            except Exception as e:
                err += 1
                w(f"❌ {cuil}|{exp} -> {e}", err=True)
                traceback.print_exc()  # detalle en consola y log
            time.sleep(PAUSA_5MIN if i % 4 == 0 else PAUSA_20S)

        w(f"✅ Ciclo OK={ok} OMIT={omit} ERR={err}")
        time.sleep(CHECK_EVERY)

finally:
    driver.quit()
    shutil.rmtree(CHROME_TMP, ignore_errors=True)
    w("🛑 Servicio detenido")
