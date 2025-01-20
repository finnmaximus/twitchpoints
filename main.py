import os
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.entities.Bet import Strategy, BetSettings
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.logger import LoggerSettings

# Obtiene las credenciales desde las variables de entorno definidas previamente en el sistema
username = os.getenv('TWITCH_USERNAME')
password = os.getenv('TWITCH_PASSWORD')

if not username or not password:
    raise ValueError("Las variables de entorno 'TWITCH_USERNAME' y 'TWITCH_PASSWORD' deben estar definidas.")

# Configuración del logger usando los parámetros correctos según la documentación
logger_settings = LoggerSettings(
    save=True,
    less=False,
    console_level=20,  # INFO level
    file_level=10,     # DEBUG level
    emoji=True,
    colored=True,
    auto_clear=True,
    console_username=False
)

# Configuración del miner
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

# Ejecuta el miner con la configuración para el streamer Mixwell
twitch_miner.run([
    Streamer("mixwell", settings=settings)
])
