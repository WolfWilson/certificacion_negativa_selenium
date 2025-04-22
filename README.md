# 📄 CERTIFICACIÓN NEGATIVA - Automatización ANSES

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![Selenium](https://img.shields.io/badge/Web%20Automation-Selenium-green?style=for-the-badge&logo=selenium)
![SQL Server](https://img.shields.io/badge/Base%20de%20Datos-SQL%20Server-red?style=for-the-badge&logo=microsoftsqlserver)
![PDF Output](https://img.shields.io/badge/Salida-PDF-yellow?style=for-the-badge&logo=adobeacrobatreader)
![Windows](https://img.shields.io/badge/Windows-10%2B-lightgrey?style=for-the-badge&logo=windows)
![Estado](https://img.shields.io/badge/Estado-En%20Desarrollo-orange?style=for-the-badge)
![License](https://img.shields.io/badge/Licencia-MIT-blue?style=for-the-badge)

---

## 📢 Descripción General

**CERTIFICACIÓN NEGATIVA ANSES** es una herramienta automatizada que permite consultar y descargar en formato PDF las certificaciones negativas desde el sitio oficial de ANSES para una lista de CUILs provistos dinámicamente desde una base de datos SQL Server.

Este sistema reemplaza el proceso manual de ingreso de datos, navegación y descarga con una ejecución automática periódica o bajo demanda. Está diseñado para ejecutarse en servidores Windows o como servicio backend en entornos más complejos (Docker/API).

---

## 🚀 Objetivos del Proyecto

- 📥 Obtener CUILs pendientes de certificación desde base SQL.
- 🌐 Consultar el sitio oficial de ANSES.
- 📄 Descargar la certificación negativa en PDF.
- ✅ Marcar como procesado en la base de datos al finalizar.
- 🕒 Ejecutar con pausas configuradas entre tareas.

---

## 🧩 Características Destacadas

✔ Extracción directa de base de datos (SQL Server)  
✔ Navegación automática en sitio ASP.NET  
✔ Guardado de PDF personalizado por CUIL  
✔ Registro de estado en base de datos (campo `anses`)  
✔ Estructura modular y lista para contenerización  

---

## 🛠️ Tecnologías Utilizadas

| Categoría         | Herramientas                                                        |
|------------------|---------------------------------------------------------------------|
| Lenguaje         | `Python 3.12`                                                       |
| Web Automation   | `Selenium`, `Chromium`                                              |
| Base de Datos    | `SQL Server`, `pyodbc`                                              |
| PDF              | `Chrome Print-to-PDF` (modo automático)                             |
| Infraestructura  | Compatible con `Task Scheduler`, `Docker` o `FastAPI` (futuro)      |

---

## 📦 Instalación y Uso

### 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/certificacion_negativa.git
cd certificacion_negativa
```

### 📂 Estructura del Proyecto

```yaml
CERTIFICACION_NEGATIVA/
│
├── informes_obtenidos/          # PDFs descargados, uno por CUIL
│
├── module/
│   └── conexion_db.py           # Módulo para conectarse a SQL Server
│
├── obtener_certificacion_negativa.py   # Script principal de automatización
├── requirements.txt             # Dependencias necesarias
├── LICENSE
└── README.md
```

## 🔁 Flujo de Trabajo Automatizado
```yaml
1️⃣ Conectar a base de datos SQL Server
2️⃣ Obtener CUILs pendientes con Finalizado = 1 y Error = 0
3️⃣ Para cada CUIL:
     - Navegar a ANSES
     - Ingresar el CUIL en el formulario
     - Descargar y guardar el PDF
     - Marcar como procesado en la base (Anses = 1)
4️⃣ Pausar 20 segundos entre tareas y 5 minutos cada 4 CUILs
```

## 📅 Automatización Periódica
```yaml
El script puede ser programado con:

🪟 Task Scheduler de Windows

🐧 Cron en servidores Linux

🐳 Docker + entrypoint cron o supervisor

🌐 API Flask/FastAPI para ejecutar desde frontend u otros sistemas (opcional)
```

## 🧠 Funcionalidades Futuras
```yaml
🔜 Modo completamente headless (sin navegador visible)
🔜 Interfaz gráfica o panel web para ejecución manual
🔜 Registro de logs en disco o sistema centralizado
🔜 Notificación por correo o sistema interno
🔜 Integración con API interna para consultar certificados desde otras apps
```