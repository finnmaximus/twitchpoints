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

class TwitchWatcher:
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
            'add': self.handle_add_stream,
            'remove': self.handle_remove_stream,
            'list': self.list_streams
        }
        self.start_time = None
        self.stats_file = "twitch_stats.txt"
        self.last_save_time = time.time()
        self.save_interval = 300
        self.max_streams = 4
        self.max_retries = 3
        self.retry_delay = 60  # segundos entre reintentos

        # Obtener credenciales desde variables de entorno
        self.twitch_username = os.getenv('TWITCH_USERNAME')
        self.twitch_password = os.getenv('TWITCH_PASSWORD')
        
        if not self.twitch_username or not self.twitch_password:
            print("\n=== Configuración de Credenciales ===")
            self.twitch_username = input("Usuario: ")
            self.twitch_password = getpass.getpass("Contraseña: ")
            os.environ['TWITCH_USERNAME'] = self.twitch_username
            os.environ['TWITCH_PASSWORD'] = self.twitch_password

        if not self.twitch_username or not self.twitch_password:
            print("Error: Las credenciales son obligatorias")
            sys.exit(1)

    def setup_driver(self):
        """Configura el driver de Selenium con Chrome"""
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')

        # Ruta de Chrome instalada en Koyeb
        chrome_path = "/app/.apt/opt/google/chrome/google-chrome"
        if not os.path.exists(chrome_path):
            raise FileNotFoundError("🚨 Google Chrome no está instalado. Verifica entrypoint.sh.")

        options.binary_location = chrome_path

        # Iniciar Selenium con Chrome
        self.driver = uc.Chrome(
            options=options,
            headless=True,
            version_main=120,  # Ajusta según la versión instalada
            browser_executable_path=chrome_path
        )
        print("🚀 Chrome configurado y listo para usar en Koyeb")

    def login(self):
        """Inicia sesión en Twitch"""
        try:
            self.driver.get('https://www.twitch.tv/login')
            wait = WebDriverWait(self.driver, 20)

            username_input = wait.until(EC.presence_of_element_located((By.ID, "login-username")))
            password_input = self.driver.find_element(By.ID, "password-input")

            username_input.send_keys(self.twitch_username)
            password_input.send_keys(self.twitch_password)

            login_button = self.driver.find_element(By.CSS_SELECTOR, "[data-a-target='passport-login-button']")
            login_button.click()

            time.sleep(3)

            if "twitch.tv/" in self.driver.current_url and "login" not in self.driver.current_url:
                print("\n¡Login exitoso!")
                return True
            else:
                print("\nError: No se pudo completar el login")
                return False

        except Exception as e:
            print(f"\nError durante el login: {str(e)}")
            return False

    def handle_add_stream(self, args):
        """Añade un nuevo stream"""
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
            'start_time': time.time()
        }
        self.streams[channel]['thread'].start()
        print(f"Añadido stream de {channel}")
        return True

    def watch_stream(self, channel):
        """Visualiza el stream en Twitch"""
        try:
            self.driver.get(f'https://www.twitch.tv/{channel}')
            print(f"\nConectando al canal de {channel}...")
            time.sleep(5)

            print(f"¡Conectado al canal de {channel}!")
        except Exception as e:
            print(f"Error en el stream {channel}: {str(e)}")

    def cleanup(self):
        """Cierra correctamente Selenium"""
        print("\nCerrando Selenium...")
        if self.driver:
            self.driver.quit()

if __name__ == "__main__":
    bot = None
    try:
        print("=== Iniciando TwitchWatcher ===")

        bot = TwitchWatcher()

        print("Intentando login en Twitch...")
        if bot.login():
            print("\n=== Bot iniciado correctamente ===")
            bot.handle_add_stream(["mixwell"])
            
            while bot.running:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\nPrograma detenido por el usuario")
    except Exception as e:
        print(f"Error crítico: {str(e)}")
    finally:
        if bot:
            bot.cleanup()
