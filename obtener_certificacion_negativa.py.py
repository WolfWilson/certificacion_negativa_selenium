# -*- coding: utf-8 -*-
"""
obtener_certificacion_negativa.py
=================================
Servicio que descarga y fusiona Certificaciones Negativas de ANSES.

• Modo “perfil real”: aprovecha tus cookies → evita el reCAPTCHA
• Modo “perfil Selenium”: crea un perfil desechable en ./chrome_profile

Cambiar la constante USE_USER_PROFILE para alternar modos.
"""

from __future__ import annotations
import datetime, random, shutil, time, os
from pathlib import Path

import undetected_chromedriver as uc
from pypdf import PdfReader, PdfWriter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

from modules.conexion_db import obtener_cuils_pendientes, marcar_procesado

# ─────────────────────────── PARÁMETROS GLOBALES ──────────────────────────
USE_USER_PROFILE = False                       # True = perfil real
USER_DATA_DIR    = r"C:\Users\wbenitez\AppData\Local\Google\Chrome\User Data"
PROFILE_NAME     = "Default"                    # o "Profile 2", etc.

MAX_RETRY   = 3
WAIT_ON_DENY = 120
CHECK_EVERY = 600          # seg entre consultas a la BD
PAUSA_CUIL  = (25, 35)
PAUSA_CADA3 = (200, 320)

HEADER_NEGA = "servicioswww.anses.gob.ar/censite/Antecedentes.aspx"
URL = "https://servicioswww.anses.gob.ar/censite/index.aspx"

BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "informes_obtenidos"
LOG_DIR    = BASE_DIR / "logs"
BACKUP_DIR = Path(r"C:\Test_negatividad")
for d in (OUTPUT_DIR, LOG_DIR, BACKUP_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────── LOGGING ──────────────────────────────────
inicio = datetime.datetime.now()
log_name = LOG_DIR / f"log_{inicio:%Y-%m-%d_%H-%M-%S}.txt"

def w(msg: str) -> None:
    """Imprime mensaje y lo anexa al archivo de log."""
    print(msg)
    with open(log_name, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

w(f"🕓 Servicio iniciado: {inicio:%Y-%m-%d %H:%M:%S}")

# ────────────────────────────── SELENIUM ──────────────────────────────────
opts = uc.ChromeOptions()
opts.add_argument("--kiosk-printing")
opts.add_argument("--disable-logging")
opts.add_argument("--disable-blink-features=AutomationControlled")

if USE_USER_PROFILE:
    opts.add_argument(fr"--user-data-dir={USER_DATA_DIR}")
    opts.add_argument(fr"--profile-directory={PROFILE_NAME}")
else:
    perfil_tmp = BASE_DIR / "chrome_profile"
    perfil_tmp.mkdir(exist_ok=True)
    opts.add_argument(fr"--user-data-dir={perfil_tmp}")

opts.add_experimental_option("prefs", {
    "savefile.default_directory": str(OUTPUT_DIR),
    "printing.print_preview_sticky_settings.appState": """
       {"recentDestinations":[{"id":"Save as PDF","origin":"local"}],
        "selectedDestinationId":"Save as PDF","version":2}"""
})

driver = uc.Chrome(headless=False, options=opts, version_main=137)
wait   = WebDriverWait(driver, 20)

# -- Ocultar navigator.webdriver
driver.execute_cdp_cmd(
    "Page.addScriptToEvaluateOnNewDocument",
    {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"}
)

# -- Ajuste stealth adicional
stealth(driver,
        languages=["es-ES","es"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris")

# ──────────────────────────── UTILIDADES PDF ──────────────────────────────
def dividir_cuil(cuil: str) -> tuple[str, str, str]:
    return cuil[:2], cuil[2:10], cuil[10]

def ruta_exp(exp: str) -> Path:
    return Path(r"\\fs01\Digitalizacion_Jubilaciones") / exp[-4:] / exp[0] / exp

def pausa(rango: tuple[int|float,int|float]) -> None:
    time.sleep(random.uniform(*rango))

def ya_tiene_negativa(pdf: Path) -> bool:
    if not pdf.exists(): return False
    rd = PdfReader(str(pdf))
    for i in range(11, min(len(rd.pages)-1, 15)+1):
        if HEADER_NEGA in (rd.pages[i].extract_text() or "").lower():
            return True
    return False

def fusionar_pdfs(orig: Path, nuevo: Path) -> None:
    writer = PdfWriter()
    for fp in (orig, nuevo):
        for pg in PdfReader(fp).pages:
            writer.add_page(pg)
    tmp = orig.with_suffix(".tmp.pdf")
    with open(tmp, "wb") as f: writer.write(f)
    tmp.replace(orig)

# ───────────────────────────── PROCESAR CUIL ──────────────────────────────
def procesar(id_tarea: int, cuil: str, exp: str) -> bool:
    pdf_orig = ruta_exp(exp) / f"{exp}.pdf"
    if not pdf_orig.exists():
        raise FileNotFoundError(pdf_orig)

    if ya_tiene_negativa(pdf_orig):
        marcar_procesado(id_tarea)
        w(f"ℹ️  {cuil} ya tenía negativa → marcado.")
        return False

    for intento in range(1, MAX_RETRY+1):
        driver.get(URL); pausa((1.5,3))
        pre, doc, dv = dividir_cuil(cuil)

        wait.until(EC.presence_of_element_located((By.ID,"txtCuitPre"))).send_keys(pre)
        driver.find_element(By.ID,"txtCuitDoc").send_keys(doc)
        driver.find_element(By.ID,"txtCuitDV").send_keys(dv)
        wait.until(EC.element_to_be_clickable((By.ID,"btnVerificar"))).click()
        pausa((2,4))

        if "Acceso denegado." in driver.page_source:
            w(f"🛑 Acceso denegado {cuil} (int {intento}/{MAX_RETRY})")
            if intento < MAX_RETRY:
                time.sleep(WAIT_ON_DENY)
                continue
            raise RuntimeError("Acceso denegado persistente")

        driver.execute_script("window.print()"); pausa((6,8))

        nuevo_pdf = max(OUTPUT_DIR.glob("*.pdf"), key=os.path.getctime)
        destino   = OUTPUT_DIR / f"{cuil}.pdf"
        if destino.exists(): destino.unlink()
        nuevo_pdf.rename(destino)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(pdf_orig, BACKUP_DIR / f"{exp}_{ts}.pdf")
        fusionar_pdfs(pdf_orig, destino)

        marcar_procesado(id_tarea)
        w(f"✓ {cuil} fusionado y actualizado")
        return True
    return False

# ───────────────────────────── BUCLE PRINCIPAL ────────────────────────────
try:
    while True:
        tareas = obtener_cuils_pendientes()
        w(f"🔄 Pendientes: {len(tareas)}")
        ok = omitidos = err = 0

        for idx, (id_t, cuil, exp) in enumerate(tareas, 1):
            try:
                exito = procesar(id_t, cuil, exp)
                if exito:
                    ok += 1
                else:
                    omitidos += 1
            except Exception as e:
                err += 1
                w(f"✗ {cuil} | Exp: {exp} -> {e}")

            pausa(PAUSA_CUIL)
            if idx % 3 == 0:
                pausa(PAUSA_CADA3)

        w(f"✅ Ciclo: OK={ok} | OMIT={omitidos} | ERR={err}")
        w(f"🕒 Esperando {CHECK_EVERY/60:.0f} min…\n")
        time.sleep(CHECK_EVERY)

except KeyboardInterrupt:
    pass
finally:
    driver.quit()
    w("🛑 Servicio detenido.")
