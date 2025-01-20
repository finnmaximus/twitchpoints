import os
from twitch_channel_points_miner import TwitchChannelPointsMiner
from twitch_channel_points_miner.classes.settings import Settings
from twitch_channel_points_miner.classes.entities.bet import Strategy, BetSettings
from twitch_channel_points_miner.classes.entities.streamer import Streamer
from twitch_channel_points_miner.logger import LoggerSettings

# Obtener credenciales desde las variables de entorno del sistema
username = os.getenv('TWITCH_USERNAME')  # Debe estar definido en el sistema
password = os.getenv('TWITCH_PASSWORD')  # Debe estar definido en el sistema

if not username or not password:
    raise ValueError("Las variables de entorno 'TWITCH_USERNAME' y 'TWITCH_PASSWORD' deben estar definidas.")

# Configuración del logger
logger_settings = LoggerSettings(
    save=True,
    console_level="INFO",
    file_level="DEBUG",
    emoji=True,
    less=False,
    colored=True,
    path="logs",
    logger_file="history.log",
    session_file="session.data",
    debug_file="debug.log"
)

# Configuración general del miner
settings = Settings(
    check_interval=60,
    make_predictions=False,
    follow_raid=True,
    claim_drops=True,
    watch_streak=True,
    auto_claim_bonuses=True,
    bet=BetSettings(
        enabled=False,
        percentage_gap=20,
        max_points=50000,
        strategy=Strategy.SMART
    ),
    disable_ssl_cert_verification=True,
    enable_analytics=True,
    chat_online=False
)

# Inicialización y ejecución del miner
twitch_miner = TwitchChannelPointsMiner(
    username=username,
    password=password,
    logger_settings=logger_settings,
    settings=settings
)

twitch_miner.run([
    Streamer("mixwell", settings=settings)
])
