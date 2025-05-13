# app/modules/conexion_db.py
import pyodbc
from config import SQL_CONN            # ← trae la cadena desde variables de entorno

# ── Conexión ------------------------------------------------------------------

#Devuelve un objeto pyodbc.Connection usando la cadena SQL_CONN.
#En Windows local puedes seguir empleando Trusted_Connection;  
#en Docker/Linux la variable SQL_CONN debe contener
#DRIVER={ODBC Driver 18 for SQL Server};SERVER=…;UID=…;PWD=…;Encrypt=yes;…
    

def get_connection():
    try:
        return pyodbc.connect(SQL_CONN, timeout=5)
    except pyodbc.Error as e:
        # loguea y relanza para no reiniciar en loop infinito
        print("❌ ERROR ODBC:", e)
        raise

# ── SELECT --------------------------------------------------------------------
def obtener_cuils_pendientes():
    """
    (Id, Cuil, NroExpediente) solo para registros:
      • Finalizado = 1
      • Error      = 0
      • Anses      = 0
      • FechaFinalizado > 2025-04-01
    """
    with get_connection() as cnx:
        cur = cnx.cursor()
        cur.execute("""
            SELECT Id, Cuil, NroExpediente
            FROM dbo.TareasExpedientesJubilacion
            WHERE Finalizado       = 1
              AND Error            = 0
              AND Anses            = 0
              AND FechaFinalizado > '2025-04-01'
            ORDER BY FechaFinalizado ASC
        """)
        return [(row.Id, str(row.Cuil).strip(), row.NroExpediente.strip())
                for row in cur]


# ── UPDATE --------------------------------------------------------------------
def marcar_procesado(id_tarea: int):
    """Pone Anses = 1 cuando todo el flujo termina OK."""
    with get_connection() as cnx:
        cur = cnx.cursor()
        cur.execute(
            "UPDATE dbo.TareasExpedientesJubilacion SET Anses = 1 WHERE Id = ?",
            id_tarea
        )
        cnx.commit()
