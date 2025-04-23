import pyodbc

def get_connection():
    return pyodbc.connect(
        r'DRIVER={SQL Server};SERVER=SQL01;DATABASE=Aportes;Trusted_Connection=yes;'
    )

def obtener_cuils_pendientes():
    conexion = get_connection()
    cursor = conexion.cursor()
    query = """
        SELECT Id, Cuil
        FROM dbo.TareasExpedientesJubilacion
        WHERE Finalizado = 1 AND Error = 0 AND Anses = 0
        ORDER BY FechaFinalizado DESC
    """
    cursor.execute(query)
    resultados = cursor.fetchall()
    return [(row.Id, str(row.Cuil).strip()) for row in resultados]

def marcar_cuil_como_procesado(id_tarea):
    conexion = get_connection()
    cursor = conexion.cursor()
    query = """
        UPDATE dbo.TareasExpedientesJubilacion
        SET Anses = 1
        WHERE Id = ?
    """
    cursor.execute(query, (id_tarea,))
    conexion.commit()
