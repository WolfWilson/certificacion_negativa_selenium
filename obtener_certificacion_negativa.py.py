import os, shutil, time, datetime, random
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from modules.conexion_db import obtener_cuils_pendientes, marcar_procesado

# ---------------- Parámetros --------------------------------------------------
MAX_RETRY     = 3
WAIT_ON_DENY  = 60        # s entre reintentos cuando ANSES bloquea
WEB_PAUSE     = 10        # s extra tras cada operación web exitosa
CHECK_EVERY   = 600       # 10 min entre consultas a la BD
PAUSA_20S     = 20        # pausa normal entre CUILs
PAUSA_5MIN    = 300       # cada 4 CUILs
HEADER_NEGA   = "servicioswww.anses.gob.ar/censite/Antecedentes.aspx".lower()

# ---------------- Rutas -------------------------------------------------------
BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "informes_obtenidos"
LOG_DIR    = BASE_DIR / "logs"
BACKUP_DIR = Path(r"C:\Test_negatividad")
for d in (OUTPUT_DIR, LOG_DIR, BACKUP_DIR):
    d.mkdir(parents=True, exist_ok=True)

URL = "https://servicioswww.anses.gob.ar/censite/index.aspx"

# ---------------- Logging -----------------------------------------------------
inicio_script = datetime.datetime.now()
log_name = LOG_DIR / f"log_{inicio_script:%Y-%m-%d_%H-%M-%S}.txt"
def w(msg: str):
    print(msg)
    with open(log_name, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

w(f"🕓 Servicio iniciado: {inicio_script:%Y-%m-%d %H:%M:%S}")

# ---------------- Selenium ----------------------------------------------------
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
opts = Options()
opts.add_argument("--log-level=3")
opts.add_argument("--disable-logging")
opts.add_argument("--kiosk-printing")
opts.add_experimental_option("prefs", {
    "savefile.default_directory": str(OUTPUT_DIR),
    "printing.print_preview_sticky_settings.appState": """
       {"recentDestinations":[{"id":"Save as PDF","origin":"local"}],
        "selectedDestinationId":"Save as PDF","version":2}"""
})
service = Service(log_path="NUL")
driver = webdriver.Chrome(service=service, options=opts)

# ---------------- Helpers -----------------------------------------------------
def dividir_cuil(cuil: str):
    return cuil[:2], cuil[2:10], cuil[10]

def ruta_exp(ed: str):
    return Path(r"\\fs01\Digitalizacion_Jubilaciones") / ed[-4:] / ed[0] / ed

def fusionar_pdfs(orig: Path, nuevo: Path):
    writer = PdfWriter()
    for fp in (orig, nuevo):
        reader = PdfReader(fp)
        for page in reader.pages:
            writer.add_page(page)
    tmp = orig.with_suffix(".tmp.pdf")
    with open(tmp, "wb") as f:
        writer.write(f)
    tmp.replace(orig)

def ya_tiene_negativa(pdf_path: Path) -> bool:
    if not pdf_path.exists():
        return False
    reader = PdfReader(str(pdf_path))
    start, end = 11, min(len(reader.pages) - 1, 15)
    for i in range(start, end + 1):
        texto = reader.pages[i].extract_text() or ""
        if HEADER_NEGA in texto.lower():
            return True
    return False

# ---------------- Proceso por CUIL -------------------------------------------
def procesar(id_tarea: int, cuil: str, expediente: str):
    carpeta_exp  = ruta_exp(expediente)
    original_pdf = carpeta_exp / f"{expediente}.pdf"
    if not original_pdf.exists():
        raise FileNotFoundError(f"No existe {original_pdf}")

    # 1) Control previo
    if ya_tiene_negativa(original_pdf):
        marcar_procesado(id_tarea)   # <-- ahora se marca como procesado
        w(f"ℹ️  {cuil} | Exp: {expediente} ya tiene cert. negativa → marcado Anses=1.")
        return False   # omitido

    # 2) Intento de generación
    for intento in range(1, MAX_RETRY + 1):
        driver.get(URL); time.sleep(2)

        pre, doc, dv = dividir_cuil(cuil)
        driver.find_element(By.ID,"txtCuitPre").send_keys(pre)
        driver.find_element(By.ID,"txtCuitDoc").send_keys(doc)
        driver.find_element(By.ID,"txtCuitDV").send_keys(dv)
        driver.find_element(By.ID,"btnVerificar").click(); time.sleep(5)

        if "Acceso denegado." in driver.page_source:
            w(f"🛑 Acceso denegado {cuil} (int {intento}/{MAX_RETRY})")
            if intento < MAX_RETRY:
                time.sleep(WAIT_ON_DENY)
                continue
            raise Exception("Acceso denegado persistente")

        driver.execute_script("window.print()")
        time.sleep(5 + WEB_PAUSE)    # pausa extra tras impresión

        nuevo_pdf = max(OUTPUT_DIR.glob("*.pdf"), key=os.path.getctime)
        destino_nuevo = OUTPUT_DIR / f"{cuil}.pdf"
        if destino_nuevo.exists():
            destino_nuevo.unlink()
        nuevo_pdf.rename(destino_nuevo)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(original_pdf, BACKUP_DIR / f"{expediente}_{ts}.pdf")
        fusionar_pdfs(original_pdf, destino_nuevo)

        marcar_procesado(id_tarea)
        w(f"[✓] {cuil} | Exp: {expediente} → fusionado y actualizado (Id {id_tarea})")
        return True
    return False

# ---------------- Bucle de servicio ------------------------------------------
try:
    while True:
        ciclo = datetime.datetime.now()
        tareas = obtener_cuils_pendientes()
        w(f"🔄 {ciclo:%H:%M:%S} → pendientes: {len(tareas)}")

        if tareas:
            ok = err = omitidos = 0
            for idx, (id_t, cuil, exp) in enumerate(tareas, 1):
                try:
                    resultado = procesar(id_t, cuil, exp)
                    if resultado:
                        ok += 1
                    else:
                        omitidos += 1
                except Exception as e:
                    err += 1
                    w(f"[✗] {cuil} | Exp: {exp} -> {e}")

                time.sleep(PAUSA_5MIN if idx % 4 == 0 else PAUSA_20S)

            w(f"✅ Ciclo: OK={ok} | OMITIDOS={omitidos} | ERR={err}")
        else:
            w("ℹ️  Sin tareas nuevas.")

        w(f"🕒 Esperando {CHECK_EVERY/60:.0f} min…\n")
        time.sleep(CHECK_EVERY)

except KeyboardInterrupt:
    pass
finally:
    driver.quit()
    w("🛑 Servicio detenido por usuario/exit.")
