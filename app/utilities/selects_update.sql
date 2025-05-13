SELECT TOP 1000 [Id]
      ,[WSInicioId]
      ,[NroExpediente]
      ,[Finalizado]
      ,[FechaFinalizado]
      ,[Error]
      ,[ErrorDescripcion]
      ,[FechaUltimaEjecucion]
      ,[Cuil]
      ,[Anses]
  FROM [Aportes].[dbo].[TareasExpedientesJubilacion] where Finalizado = 1 and error = 0 and Anses = 0 and FechaFinalizado > '2025-04-01' order by FechaFinalizado asc


  USE Aportes;
GO



UPDATE dbo.TareasExpedientesJubilacion
SET    Anses = 0
WHERE  Cuil IN (
                27121048251,
                27175962269,
                20232446146,
				27174975227)


UPDATE dbo.TareasExpedientesJubilacion
SET    Anses = 1
WHERE  Cuil IN (
                20169261807,
				27174975227,
				20113258951)

