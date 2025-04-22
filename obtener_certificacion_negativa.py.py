import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from modules.conexion_db import obtener_cuils_pendientes, marcar_cuil_como_procesado

# --- Configuración ---
URL = "https://servicioswww.anses.gob.ar/censite/index.aspx"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "informes_obtenidos")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Configuración de Chrome en modo PDF automático ---
options = Options()
options.add_experimental_option("prefs", {
    "printing.print_preview_sticky_settings.appState": """{
        "recentDestinations": [{"id": "Save as PDF","origin": "local","account": ""}],
        "selectedDestinationId": "Save as PDF",
        "version": 2
    }""",
    "savefile.default_directory": OUTPUT_DIR
})
options.add_argument('--kiosk-printing')  # Activar impresión directa
driver = webdriver.Chrome(options=options)

def dividir_cuil(cuil: str):
    return cuil[:2], cuil[2:10], cuil[10]

def consultar_y_guardar(id_tarea, cuil: str):
    driver.get(URL)
    time.sleep(2)

    pre, doc, dv = dividir_cuil(cuil)
    driver.find_element(By.ID, "txtCuitPre").send_keys(pre)
    driver.find_element(By.ID, "txtCuitDoc").send_keys(doc)
    driver.find_element(By.ID, "txtCuitDV").send_keys(dv)

    driver.find_element(By.ID, "btnVerificar").click()
    time.sleep(5)

    # Generar impresión a PDF
    driver.execute_script("window.print();")
    time.sleep(5)

    # Renombrar archivo descargado
    archivos = sorted(os.listdir(OUTPUT_DIR), key=lambda x: os.path.getctime(os.path.join(OUTPUT_DIR, x)), reverse=True)
    for archivo in archivos:
        if archivo.lower().endswith(".pdf"):
            origen = os.path.join(OUTPUT_DIR, archivo)
            destino = os.path.join(OUTPUT_DIR, f"{cuil}.pdf")
            os.rename(origen, destino)
            print(f"[✓] Guardado PDF: {destino}")
            marcar_cuil_como_procesado(id_tarea)
            print(f"[✓] Marcado en BD: ID {id_tarea} (CUIL: {cuil})")
            break
    else:
        raise Exception("No se detectó ningún PDF para guardar")

# --- Proceso principal ---
tareas = obtener_cuils_pendientes()
print(f"Se detectaron {len(tareas)} CUILs pendientes.")

for i, (id_tarea, cuil) in enumerate(tareas, 1):
    try:
        consultar_y_guardar(id_tarea, cuil)
    except Exception as e:
        print(f"[✗] Error con CUIL {cuil}: {e}")

    if i % 4 == 0:
        print("⏳ Esperando 5 minutos...")
        time.sleep(300)
    else:
        print("⏱️ Esperando 20 segundos...")
        time.sleep(20)

driver.quit()
print("✅ Proceso completado.")
