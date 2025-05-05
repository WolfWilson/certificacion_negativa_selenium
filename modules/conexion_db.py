#modules/conexion_db.py
import pyodbc

# --- Conexión ----------------------------------------------------------------
def get_connection():
    return pyodbc.connect(
        r'DRIVER={SQL Server};SERVER=SQL01;DATABASE=Aportes;Trusted_Connection=yes;'
    )

# --- SELECT ------------------------------------------------------------------
def obtener_cuils_pendientes():
    """
    Devuelve (Id, Cuil, NroExpediente) solo para registros:
      • Finalizado = 1
      • Error      = 0
      • Anses      = 0
      • FechaFinalizado posterior al 1-abr-2025
      • Ordenados de más antiguo a más nuevo
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

# --- UPDATE ------------------------------------------------------------------
def marcar_procesado(id_tarea: int):
    """Pone Anses = 1 cuando todo el flujo termina OK."""
    with get_connection() as cnx:
        cur = cnx.cursor()
        cur.execute(
            "UPDATE dbo.TareasExpedientesJubilacion SET Anses = 1 WHERE Id = ?",
            id_tarea
        )
        cnx.commit()
