"""
obtener_certificacion_negativa.py
Versión para Docker Linux (Xvfb) – Selenium GUI + Page.printToPDF
"""

import os, shutil, time, datetime, base64
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from modules.conexion_db import obtener_cuils_pendientes, marcar_procesado
import os, shutil, time, datetime, base64, uuid, tempfile   # uuid añadido
from config import BASE_DIR, OUTPUT_DIR, LOG_DIR, BACKUP_DIR, EXP_ROOT

# ── Parámetros generales ─────────────────────────────────────
MAX_RETRY   = 3
WAIT_DENY   = 60
WEB_PAUSE   = 10
CHECK_EVERY = 600
PAUSA_20S   = 20
PAUSA_5MIN  = 300
KEEP_DAYS   = 30
HEADER_NEGA = "servicioswww.anses.gob.ar/censite/antecedentes.aspx"

URL = "https://servicioswww.anses.gob.ar/censite/index.aspx"

for d in (OUTPUT_DIR, LOG_DIR, BACKUP_DIR):
    d.mkdir(exist_ok=True, parents=True)

inicio = datetime.datetime.now()
log_file = LOG_DIR / f"log_{inicio:%Y-%m-%d_%H-%M-%S}.txt"
def w(m: str):
    print(m)
    log_file.write_text(log_file.read_text(encoding="utf-8") + m + "\n" if log_file.exists() else m + "\n", encoding="utf-8")

w(f"🕓 Inicio servicio Docker: {inicio:%Y-%m-%d %H:%M:%S}")

# ── Selenium: opciones y perfil temporal ────────────────────
import os, shutil, time, datetime, base64, uuid, tempfile   # uuid añadido
# …

# ── Selenium: opciones y perfil temporal único ─────────────
opts = Options()
opts.binary_location = "/usr/bin/chromium"
opts.add_argument("--window-size=1366,768")
opts.add_argument("--disable-gpu")
opts.add_argument("--disable-logging")

# ← flags necesarios al correr como root
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")

# perfil temporal realmente único
CHROME_TMP = f"/tmp/chrome_{uuid.uuid4().hex}"
Path(CHROME_TMP).mkdir(parents=True, exist_ok=True)
opts.add_argument(f"--user-data-dir={CHROME_TMP}")

driver = webdriver.Chrome(options=opts)
wait   = WebDriverWait(driver, 30)


# ── Helpers ───────────────────────────────────────────────────
def dividir(cuil: str):
    return cuil[:2], cuil[2:10], cuil[10]

def ruta_exp(expediente: str):
    return EXP_ROOT / expediente[-4:] / expediente[0] / expediente

def fusionar(orig: Path, nuevo: Path):
    writer = PdfWriter()
    for src in (orig, nuevo):
        for page in PdfReader(src).pages:
            writer.add_page(page)
    tmp = orig.with_suffix(".tmp.pdf")
    with tmp.open("wb") as f:
        writer.write(f)
    tmp.replace(orig)

def ya_negativa(pdf: Path) -> bool:
    if not pdf.exists():
        return False
    r = PdfReader(pdf)
    for i in range(11, min(len(r.pages)-1, 15)+1):
        if HEADER_NEGA in (r.pages[i].extract_text() or "").lower():
            return True
    return False

def save_pdf(dest: Path):
    pdf = driver.execute_cdp_cmd(
        "Page.printToPDF",
        {"printBackground": True, "preferCSSPageSize": True}
    )
    dest.write_bytes(base64.b64decode(pdf["data"]))

def cleanup_output():
    limite = datetime.datetime.now() - datetime.timedelta(days=KEEP_DAYS)
    for fp in OUTPUT_DIR.glob("*.pdf"):
        if datetime.datetime.fromtimestamp(fp.stat().st_mtime) < limite:
            fp.unlink()
            w(f"🗑️  PDF viejo eliminado: {fp.name}")

# ── Proceso único por CUIL ───────────────────────────────────
def procesar(id_tarea: int, cuil: str, expediente: str):
    pdf_orig = ruta_exp(expediente) / f"{expediente}.pdf"
    if not pdf_orig.exists():
        raise FileNotFoundError(pdf_orig)

    if ya_negativa(pdf_orig):
        marcar_procesado(id_tarea)
        w(f"ℹ️  {cuil} | {expediente} ya tenía cert. → Anses=1")
        return False

    for intento in range(1, MAX_RETRY+1):
        driver.get(URL)
        try:
            wait.until(EC.presence_of_element_located((By.ID, "txtCuitPre")))
        except:
            w("⚠️  Formulario no cargó; reintento…")
            time.sleep(WAIT_DENY)
            continue

        pre, doc, dv = dividir(cuil)
        driver.find_element(By.ID, "txtCuitPre").send_keys(pre)
        driver.find_element(By.ID, "txtCuitDoc").send_keys(doc)
        driver.find_element(By.ID, "txtCuitDV").send_keys(dv)
        driver.find_element(By.ID, "btnVerificar").click()

        wait.until(lambda d: "Antecedentes" in d.page_source or
                             "Acceso denegado." in d.page_source)

        if "Acceso denegado." in driver.page_source:
            w(f"🚫 Acceso denegado ({intento}/{MAX_RETRY}) para {cuil}")
            time.sleep(WAIT_DENY)
            continue

        tmp_pdf = OUTPUT_DIR / f"{cuil}_tmp.pdf"
        save_pdf(tmp_pdf)
        time.sleep(WEB_PAUSE)

        final_pdf = OUTPUT_DIR / f"{cuil}.pdf"
        if final_pdf.exists():
            final_pdf.unlink()
        tmp_pdf.rename(final_pdf)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(pdf_orig, BACKUP_DIR / f"{expediente}_{ts}.pdf")
        fusionar(pdf_orig, final_pdf)

        marcar_procesado(id_tarea)
        w(f"[✓] {cuil} | {expediente} fusionado")
        return True
    raise RuntimeError("Acceso denegado persistente")

# ── Bucle servicio ───────────────────────────────────────────
try:
    while True:
        cleanup_output()
        tareas = obtener_cuils_pendientes()
        w(f"🔄 Pendientes: {len(tareas)}")

        ok = err = omitidos = 0
        for idx, (id_t, cuil, exp) in enumerate(tareas, 1):
            try:
                res = procesar(id_t, cuil, exp)
                if res:
                    ok += 1
                else:
                    omitidos += 1
            except Exception as e:
                err += 1
                w(f"[✗] {cuil} | {exp} -> {e}")
            time.sleep(PAUSA_5MIN if idx % 4 == 0 else PAUSA_20S)

        w(f"✅ Ciclo: OK={ok} | OMIT={omitidos} | ERR={err}")
        time.sleep(CHECK_EVERY)

except KeyboardInterrupt:
    pass
finally:
    try:
        driver.quit()
    except Exception:
        pass
    shutil.rmtree(CHROME_TMP, ignore_errors=True)
    w("🛑 Servicio detenido")


