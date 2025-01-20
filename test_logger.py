
from TwitchChannelPointsMiner.logger import LoggerSettings

# Intenta crear el objeto con diferentes combinaciones
try:
    logger = LoggerSettings()
    print("Parámetros por defecto:", vars(logger))
except Exception as e:
    print("Error con parámetros por defecto:", str(e))

# Imprime la documentación de la clase
print("\nDocumentación de LoggerSettings:")
help(LoggerSettings)