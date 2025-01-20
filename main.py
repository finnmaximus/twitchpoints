import os
import sys
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.entities.Bet import Strategy, BetSettings
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.logger import LoggerSettings

# Servidor HTTP simple para health checks
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        
    def log_message(self, format, *args):
        # Evitar logging de requests HTTP
        return

def run_health_server():
    server = HTTPServer(('0.0.0.0', int(os.getenv('PORT', 8080))), HealthCheckHandler)
    server.serve_forever()

# Asegurarse de que el archivo .env se carga desde el directorio del script
current_dir = Path(__file__).parent.absolute()
env_path = current_dir / '.env'
load_dotenv(env_path)

# Obtiene las credenciales desde las variables de entorno
username = os.getenv('TWITCH_USERNAME')
password = os.getenv('TWITCH_PASSWORD')

if not username or not password:
    print("Error: No se encontraron las credenciales en el archivo .env")
    print(f"Buscando archivo en: {env_path}")
    print("Asegúrate de que el archivo .env existe y contiene TWITCH_USERNAME y TWITCH_PASSWORD")
    sys.exit(1)

# Configuración del logger con más información visible
logger_settings = LoggerSettings(
    save=True,
    less=False,
    console_level=10,  # Cambiado a DEBUG level para ver más información
    file_level=10,     # DEBUG level
    emoji=True,
    colored=True,
    auto_clear=False,  # Cambiado a False para mantener todos los logs
    console_username=True  # Cambiado a True para ver el username en los logs
)

# Inicialización del minero sin configuración previa
twitch_miner = TwitchChannelPointsMiner(
    username=username,
    password=password,
    logger_settings=logger_settings
)

# Iniciar servidor de health check en un thread separado
health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()

# Configurar los ajustes después de la inicialización
Settings.check_interval = 60
Settings.make_predictions = False
Settings.follow_raid = True
Settings.claim_drops = True
Settings.watch_streak = True
Settings.auto_claim_bonuses = True
Settings.disable_ssl_cert_verification = True
Settings.enable_analytics = True
Settings.chat_online = False

# Ejecuta el miner con la configuración para el streamer Mixwell
twitch_miner.run([
    Streamer("mixwell")
])
