import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_PATH = os.getenv("DB_PATH", "database.db")
    LOG_PATH = os.getenv("LOG_PATH", "system.log")
    DEFAULT_TARGET_URL = os.getenv("DEFAULT_TARGET_URL", "https://toscrape.com{page}.html")
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 10))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
