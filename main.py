import os
from dotenv import load_dotenv
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.entities.Bet import Strategy, BetSettings
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.logger import LoggerSettings

# Cargar variables de entorno
load_dotenv()

# Get credentials from environment variables
username = os.getenv('TWITCH_USERNAME')
password = os.getenv('TWITCH_PASSWORD')

# Configure logger settings for better tracking
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

# Main settings with optimized configuration
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

# Initialize the miner with updated settings
twitch_miner = TwitchChannelPointsMiner(
    username=username,
    password=password,
    logger_settings=logger_settings,
    settings=settings
)

# Run the miner with Mixwell's channel
twitch_miner.run([
    Streamer("mixwell", settings=settings)
])