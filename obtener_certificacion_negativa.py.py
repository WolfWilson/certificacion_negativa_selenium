import os
import time
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from modules.conexion_db import obtener_cuils_pendientes, marcar_cuil_como_procesado

# --- Configuración ---
URL = "https://servicioswww.anses.gob.ar/censite/index.aspx"
BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE_DIR, "informes_obtenidos")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- Logging ---
inicio = datetime.datetime.now()
fecha_log = inicio.strftime("%Y-%m-%d_%H-%M-%S")
log_path = os.path.join(LOG_DIR, f"log_{fecha_log}.txt")
log = open(log_path, "w", encoding="utf-8")

log.write(f"🕓 Inicio del proceso: {inicio.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

# --- Obtener tareas ---
tareas = obtener_cuils_pendientes()
log.write(f"🔍 Tareas pendientes encontradas: {len(tareas)}\n\n")
print(f"🔍 Tareas pendientes detectadas: {len(tareas)}")

if not tareas:
    log.write("🚫 No hay tareas pendientes con Anses = 0. Proceso finalizado.\n")
    log.close()
    exit()

# --- Configuración del navegador solo si hay tareas ---
options = Options()
options.add_experimental_option("prefs", {
    "printing.print_preview_sticky_settings.appState": """{
        "recentDestinations": [{"id": "Save as PDF","origin": "local","account": ""}],
        "selectedDestinationId": "Save as PDF",
        "version": 2
    }""",
    "savefile.default_directory": OUTPUT_DIR
})
options.add_argument('--kiosk-printing')
driver = webdriver.Chrome(options=options)

# --- Funciones auxiliares ---
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

    driver.execute_script("window.print();")
    time.sleep(5)

    archivos = sorted(os.listdir(OUTPUT_DIR), key=lambda x: os.path.getctime(os.path.join(OUTPUT_DIR, x)), reverse=True)
    for archivo in archivos:
        if archivo.lower().endswith(".pdf"):
            origen = os.path.join(OUTPUT_DIR, archivo)
            destino = os.path.join(OUTPUT_DIR, f"{cuil}.pdf")
            os.rename(origen, destino)
            marcar_cuil_como_procesado(id_tarea)
            log.write(f"[✓] PDF generado y guardado para CUIL {cuil} (ID {id_tarea})\n")
            return True
    raise Exception("No se detectó ningún PDF generado")

# --- Bucle principal ---
procesados_ok = 0
procesados_error = 0

for i, (id_tarea, cuil) in enumerate(tareas, 1):
    try:
        consultar_y_guardar(id_tarea, cuil)
        procesados_ok += 1
    except Exception as e:
        msg = f"[✗] Error con CUIL {cuil} (ID {id_tarea}): {str(e)}"
        log.write(msg + "\n")
        print(msg)
        procesados_error += 1

    if i % 4 == 0:
        print("⏳ Pausa de 5 minutos...")
        time.sleep(300)
    else:
        print("⏱️ Pausa de 20 segundos...")
        time.sleep(20)

driver.quit()
fin = datetime.datetime.now()
duracion = fin - inicio

# --- Resumen final ---
log.write("\n--- RESUMEN ---\n")
log.write(f"🟢 CUILs procesados correctamente: {procesados_ok}\n")
log.write(f"🔴 Errores: {procesados_error}\n")
log.write(f"⏱️ Duración total: {str(duracion)}\n")
log.write(f"🕓 Fin del proceso: {fin.strftime('%Y-%m-%d %H:%M:%S')}\n")
log.close()
print("✅ Proceso finalizado. Log generado.")
