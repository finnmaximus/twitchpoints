import os
import time
import threading
import argparse
import getpass
import datetime
import json
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from dotenv import load_dotenv
import sys
import traceback
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import glob
import subprocess
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twitch_watcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class HealthCheckHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'  # Use HTTP/1.1 instead of 0.9
    bot = None

    def do_GET(self):
        try:
            if self.path == '/health':
                self._send_response("OK")
            elif self.path == '/help':
                self._send_response("""
=== Comandos Disponibles ===
help              - Muestra esta lista de comandos
status           - Muestra el estado actual
list             - Muestra streams activos

Para más comandos, usa los endpoints:
/add/<canal>     - Añade un nuevo stream
/remove/<canal>  - Elimina un stream
/change/<canal>  - Cambia el stream principal
                """)
            elif self.path == '/status':
                if self.bot:
                    self._send_response(f"Canal actual: {self.bot.current_stream}")
                else:
                    self._send_response("Bot no iniciado", 503)
            elif self.path == '/list':
                if self.bot:
                    streams = "\n".join([f"- {channel}" for channel in self.bot.streams])
                    self._send_response(streams if streams else "No hay streams activos")
                else:
                    self._send_response("Bot no iniciado", 503)
            else:
                self._send_response("Not Found", 404)
        except Exception as e:
            self._send_response(f"Error: {str(e)}", 500)

    def _send_response(self, message, status=200):
        """Helper para enviar respuestas HTTP consistentes"""
        self.send_response(status)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))

def run_health_server():
    """Ejecuta un servidor HTTP para health checks"""
    port = int(os.getenv('PORT', 8080))
    retries = 3
    
    for attempt in range(retries):
        try:
            server = HTTPServer(('', port), HealthCheckHandler)
            logger.info(f"Iniciando servidor HTTP en puerto {port}")
            server.serve_forever()
            break
        except OSError as e:
            if e.errno == 98:  # Address already in use
                if attempt < retries - 1:
                    logger.warning(f"Puerto {port} en uso, intentando liberar...")
                    time.sleep(2)
                    continue
                else:
                    logger.error(f"No se pudo iniciar el servidor HTTP: puerto {port} en uso")
                    raise
            else:
                raise

class TwitchWatcher:
    def find_chrome_binary(self):
        """Busca dinámicamente la ubicación de Chrome"""
        koyeb_paths = [
            '/workspace/.heroku/python/lib/python3.9/site-packages/undetected_chromedriver/chromedriver',
            '/workspace/.local/share/undetected_chromedriver/chromedriver',
            '/workspace/.heroku/python/bin/chromedriver'
        ]
        
        # Primero buscar en rutas de Koyeb
        for path in koyeb_paths:
            if os.path.exists(path):
                logger.info(f"ChromeDriver encontrado en: {path}")
                return path

        # Si no se encuentra, usar el ChromeDriver incorporado
        chromedriver_dir = os.path.join(os.path.expanduser('~'), '.local/share/undetected_chromedriver')
        if not os.path.exists(chromedriver_dir):
            os.makedirs(chromedriver_dir)
        
        logger.info(f"Usando directorio ChromeDriver: {chromedriver_dir}")

        # Instalar Chrome si no está presente
        if os.getenv('KOYEB_APP_NAME') and not any(os.path.exists(p) for p in koyeb_paths):
            logger.info("Instalando Chrome en Koyeb...")
            os.system('apt-get update && apt-get install -y chromium-browser')

        return None  # Dejar que undetected_chromedriver lo maneje

    def __init__(self):
        self.driver = None
        self.streams = {}  # Diccionario de streams activos
        self.running = True
        self.setup_driver()
        self.commands = {
            'help': self.show_help,
            'exit': self.exit_program,
            'change': self.handle_change_stream,
            'status': self.show_status,
            'add': self.handle_add_stream,    # Nuevo comando
            'remove': self.handle_remove_stream,  # Nuevo comando
            'list': self.list_streams    # Nuevo comando
        }
        self.start_time = None
        self.stats_file = "twitch_stats.txt"
        self.last_save_time = time.time()
        self.save_interval = 300
        self.max_streams = 4
        self.max_retries = 3
        self.retry_delay = 60  # segundos entre reintentos

        # Obtener o pedir credenciales
        self.twitch_username = os.getenv('TWITCH_USERNAME')
        self.twitch_password = os.getenv('TWITCH_PASSWORD')
        
        if not self.twitch_username or not self.twitch_password:
            print("\n=== Configuración de Credenciales ===")
            print("No se encontraron credenciales en variables de entorno.")
            print("Por favor, ingresa tus credenciales de Twitch:")
            self.twitch_username = input("Usuario: ")
            self.twitch_password = getpass.getpass("Contraseña: ")
            
            # Guardar en variables de entorno para la sesión actual
            os.environ['TWITCH_USERNAME'] = self.twitch_username
            os.environ['TWITCH_PASSWORD'] = self.twitch_password
            
            print("\nNota: Para no tener que ingresar las credenciales cada vez,")
            print("configura las variables de entorno TWITCH_USERNAME y TWITCH_PASSWORD")
            print("en la plataforma Koyeb o en un archivo .env local.\n")

        if not self.twitch_username or not self.twitch_password:
            print("Error: Las credenciales son obligatorias")
            sys.exit(1)

    def setup_driver(self):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                options = uc.ChromeOptions()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                
                if os.getenv('KOYEB_APP_NAME'):
                    chrome_path = self.find_chrome_binary()
                    if chrome_path:
                        logger.info(f"Iniciando Chrome con driver path: {chrome_path}")
                        self.driver = uc.Chrome(
                            driver_executable_path=chrome_path,
                            options=options,
                            headless=True,
                            use_subprocess=False
                        )
                    else:
                        logger.info("No se encontró ChromeDriver, dejando que undetected_chromedriver maneje la instalación")
                        self.driver = uc.Chrome(options=options, headless=True, use_subprocess=False)
                else:
                    self.driver = uc.Chrome(options=options)
                
                logger.info("Chrome iniciado correctamente")
                return
                
            except Exception as e:
                logger.error(f"Error al iniciar Chrome (intento {attempt + 1}/{max_attempts}): {str(e)}")
                if attempt == max_attempts - 1:
                    raise
                time.sleep(5)

    def login(self):
        try:
            self.driver.get('https://www.twitch.tv/login')
            wait = WebDriverWait(self.driver, 20)
            
            username_input = wait.until(EC.presence_of_element_located((By.ID, "login-username")))
            password_input = self.driver.find_element(By.ID, "password-input")
            
            # Usar credenciales de variables de entorno
            username_input.send_keys(self.twitch_username)
            password_input.send_keys(self.twitch_password)
            
            login_button = self.driver.find_element(By.CSS_SELECTOR, "[data-a-target='passport-login-button']")
            login_button.click()
            
            print("\nIntentando login...")
            time.sleep(3)  # Esperar respuesta inicial

            # Verificar si hay verificación por correo
            max_attempts = 3
            while max_attempts > 0:
                try:
                    verify_element = self.driver.find_element(By.CSS_SELECTOR, "[data-a-target='verification-code-input']")
                    if verify_element:
                        print("\n¡Se requiere verificación por correo!")
                        print("Revisa tu correo y copia el código de verificación.")
                        verification_code = input("\nIngresa el código de verificación: ")
                        verify_element.send_keys(verification_code)
                        
                        # Buscar y hacer clic en el botón de enviar código
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, "[data-a-target='verification-code-submit-button']")
                        submit_button.click()
                        time.sleep(3)
                except:
                    # Si no encontramos el elemento de verificación, verificamos si el login fue exitoso
                    if "twitch.tv/" in self.driver.current_url and "login" not in self.driver.current_url:
                        print("\n¡Login exitoso!")
                        return True
                
                max_attempts -= 1
                time.sleep(2)

            if "twitch.tv/" in self.driver.current_url and "login" not in self.driver.current_url:
                print("\n¡Login exitoso!")
                return True
            else:
                print("\nError: No se pudo completar el login")
                return False

        except Exception as e:
            print(f"\nError durante el login: {str(e)}")
            return False

    def show_help(self, *args):
        """Muestra la lista de comandos disponibles"""
        print("\n=== Comandos Disponibles ===")
        print("help              - Muestra esta lista de comandos")
        print("change <canal>    - Cambia el stream principal")
        print("add <canal>       - Añade un nuevo stream (máximo 4)")
        print("remove <canal>    - Elimina un stream")
        print("list             - Muestra todos los streams activos")
        print("status           - Muestra el estado actual")
        print("exit             - Cierra la aplicación")
        return True

    def exit_program(self, *args):
        """Cierra el programa"""
        print("\nGuardando estadísticas finales...")
        self.save_stats()
        print("\nCerrando la aplicación...")
        self.running = False
        return False

    def show_status(self, *args):
        """Muestra el estado actual del bot"""
        print(f"\nEstás viendo el canal: {self.current_stream}")
        return True

    def handle_change_stream(self, *args):
        """Maneja el cambio de canal"""
        if not args or not args[0]:
            print("Error: Debes especificar un canal. Ejemplo: change mixwell")
            return True
        new_channel = args[0]
        threading.Thread(target=self.change_stream, args=(new_channel,)).start()
        return True

    def handle_add_stream(self, args):
        """Añade un nuevo stream para ver simultáneamente"""
        if not args:
            print("Error: Debes especificar un canal. Ejemplo: add ibai")
            return True

        channel = args[0]
        if len(self.streams) >= self.max_streams:
            print(f"Error: Ya estás viendo el máximo de {self.max_streams} streams")
            return True

        if channel in self.streams:
            print(f"Ya estás viendo el canal de {channel}")
            return True

        # Iniciar nuevo stream en thread separado
        self.streams[channel] = {
            'thread': threading.Thread(target=self.watch_stream, args=(channel,)),
            'viewing_points': 0,
            'claimed_points': 0,
            'start_time': time.time()
        }
        self.streams[channel]['thread'].start()
        print(f"Añadido stream de {channel}")
        return True

    def handle_remove_stream(self, args):
        """Elimina un stream activo"""
        if not args:
            print("Error: Debes especificar un canal. Ejemplo: remove ibai")
            return True

        channel = args[0]
        if channel == "mixwell":
            print("No puedes eliminar el stream principal de mixwell")
            return True

        if channel in self.streams:
            print(f"Eliminando stream de {channel}...")
            self.streams[channel]['thread'].join(1)
            del self.streams[channel]
            print(f"Stream de {channel} eliminado")
        else:
            print(f"No estás viendo el canal de {channel}")
        return True

    def list_streams(self, *args):
        """Lista todos los streams activos"""
        print("\n=== Streams Activos ===")
        for channel in self.streams:
            points = self.streams[channel]['viewing_points'] + self.streams[channel]['claimed_points']
            print(f"- {channel}: {int(points)} puntos totales")
        return True

    def command_loop(self):
        print("\nEscribe 'help' para ver la lista de comandos disponibles")
        while True:
            try:
                cmd_input = input("\n> ").strip().lower()
                if not cmd_input:
                    continue

                parts = cmd_input.split()
                command = parts[0]
                args = parts[1:] if len(parts) > 1 else []

                if command in self.commands:
                    if not self.commands[command](args):
                        break
                else:
                    print(f"Comando desconocido: {command}")
                    print("Escribe 'help' para ver la lista de comandos")

            except Exception as e:
                print(f"Error al procesar el comando: {str(e)}")

    def save_stats(self):
        """Guarda las estadísticas en un archivo"""
        if not self.start_time:
            return

        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                f.write(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for channel, data in self.streams.items():
                    elapsed_time = time.time() - data['start_time']
                    elapsed_minutes = elapsed_time / 60
                    total_points = data['viewing_points'] + data['claimed_points']
                    points_per_minute = total_points / elapsed_minutes if elapsed_minutes > 0 else 0

                    f.write(f"=== Canal: {channel} ===\n")
                    f.write(f"Tiempo Activo: {int(elapsed_minutes)} minutos\n")
                    f.write(f"Puntos Por Visualizar: {int(data['viewing_points'])}\n")
                    f.write(f"Puntos Reclamados: {int(data['claimed_points'])}\n")
                    f.write(f"Total Puntos: {int(total_points)}\n")
                    f.write(f"Puntos Por Minuto: {round(points_per_minute, 2)}\n\n")

            print("\nEstadísticas guardadas en", self.stats_file)
        except Exception as e:
            logger.error(f"Error al guardar estadísticas: {str(e)}")

    def safe_find_element(self, by, value, timeout=10):
        """Busca un elemento de manera segura con reintento"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None
        except Exception as e:
            logger.error(f"Error buscando elemento {value}: {str(e)}")
            return None

    def restart_stream(self, channel):
        """Reinicia un stream que ha fallado"""
        logger.info(f"Intentando reiniciar stream de {channel}...")
        try:
            if channel in self.streams:
                self.streams[channel]['thread'] = threading.Thread(
                    target=self.watch_stream, 
                    args=(channel,)
                )
                self.streams[channel]['thread'].start()
                logger.info(f"Stream de {channel} reiniciado correctamente")
        except Exception as e:
            logger.error(f"Error al reiniciar stream de {channel}: {str(e)}")

    def watch_stream(self, channel):
        retry_count = 0
        while self.running and retry_count < self.max_retries:
            try:
                if channel not in self.streams:
                    self.streams[channel] = {
                        'viewing_points': 0,
                        'claimed_points': 0,
                        'start_time': time.time()
                    }

                self.current_stream = channel
                if not self.start_time:
                    self.start_time = time.time()
                
                self.driver.get(f'https://www.twitch.tv/{channel}')
                print(f"\nConectando al canal de {channel}...")
                time.sleep(5)  # Wait for stream to load
                
                # Click on mature content button if it appears
                try:
                    mature_button = self.driver.find_element(By.CSS_SELECTOR, "[data-a-target='player-overlay-mature-accept']")
                    mature_button.click()
                    print("Contenido para mayores de edad aceptado")
                except:
                    pass

                print(f"¡Conectado al canal de {channel}!")
                print("Monitorizando puntos del canal...")

                # Start checking for channel points button periodically
                while self.running and channel in self.streams:
                    try:
                        current_time = time.time()
                        
                        # Verificar que seguimos en la página correcta
                        if channel not in self.driver.current_url:
                            logger.warning(f"Página incorrecta detectada para {channel}, reconectando...")
                            raise Exception("Página incorrecta")

                        # Añadir puntos por visualización
                        self.streams[channel]['viewing_points'] += 10 * ((current_time - self.last_save_time) / 300)
                        
                        # Intentar reclamar puntos con manejo de errores
                        try:
                            points_button = self.safe_find_element(By.CSS_SELECTOR, ".claimable-bonus__icon")
                            if points_button and points_button.is_displayed():
                                points_button.click()
                                self.streams[channel]['claimed_points'] += 50
                                logger.info(f"¡Puntos reclamados en el canal de {channel}!")
                        except:
                            pass

                        if current_time - self.last_save_time >= self.save_interval:
                            self.save_stats()
                            self.last_save_time = current_time
                        
                        time.sleep(30)
                        retry_count = 0  # Resetear contador si todo va bien

                    except Exception as e:
                        logger.error(f"Error en el loop del stream {channel}: {str(e)}")
                        time.sleep(5)  # Pequeña pausa antes de reintentar
                        retry_count += 1

            except Exception as e:
                logger.error(f"Error grave en el stream de {channel}: {str(e)}")
                logger.error(traceback.format_exc())
                retry_count += 1
                
                if retry_count < self.max_retries:
                    wait_time = self.retry_delay * retry_count
                    logger.info(f"Reintentando en {wait_time} segundos...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Stream de {channel} fallido después de {self.max_retries} intentos")
                    if channel in self.streams:
                        del self.streams[channel]
                    break

    def change_stream(self, new_channel):
        self.running = False  # Stop current stream watching loop
        time.sleep(1)  # Wait for current loop to finish
        self.running = True  # Reset for new stream
        print(f"Cambiando de {self.current_stream} a {new_channel}")
        self.watch_stream(new_channel)

    def cleanup(self):
        """Limpieza segura de recursos"""
        try:
            self.running = False
            self.save_stats()
            
            for channel, data in list(self.streams.items()):
                try:
                    if 'thread' in data:
                        data['thread'].join(timeout=2)
                except:
                    pass
                    
            if self.driver:
                self.driver.quit()
        except Exception as e:
            logger.error(f"Error durante la limpieza: {str(e)}")

def run_command(command):
    """Ejecuta un comando y retorna la respuesta"""
    try:
        response = requests.get(f"http://localhost:8080/{command}")
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    bot = None
    try:
        logger.info("=== Iniciando TwitchWatcher ===")
        logger.info("Esperando credenciales...")
        
        bot = TwitchWatcher()
        
        logger.info("Intentando login en Twitch...")
        if bot.login():
            HealthCheckHandler.bot = bot
            
            logger.info("\n=== Bot iniciado correctamente ===")
            logger.info("Usa los siguientes comandos para controlar el bot:")
            logger.info("python control.py status  - Ver estado")
            logger.info("python control.py list    - Ver streams")
            logger.info("python control.py log     - Ver logs\n")
            
            bot.handle_add_stream(["mixwell"])
            
            health_thread = threading.Thread(target=run_health_server, daemon=True)
            health_thread.start()
            
            while bot.running:
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("\nPrograma detenido por el usuario")
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        if bot:
            bot.cleanup()
