import os
import logging
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv

# =============================================
# Load configuration from .env
# =============================================
load_dotenv()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# =============================================
# Ollama (local LLM)
# =============================================
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_CHAT = os.getenv("MODEL_CHAT", "qwen3:4b")
# PRD v14: default tetap 50000 detik (override via .env)
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "50000"))

# =============================================
# Logging setup (console + daily rotating file)
# =============================================
logger = logging.getLogger("TalentSearch")
logger.setLevel(logging.DEBUG)

os.makedirs("logs", exist_ok=True)

# Console handler (INFO+)
_console = logging.StreamHandler()
_console.setLevel(logging.INFO)
_console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_console)

# File handler (DEBUG, rotate daily keep 7 days)
_file = TimedRotatingFileHandler("logs/app.log", when="midnight", backupCount=7, encoding="utf-8")
_file.setLevel(logging.DEBUG)
_file.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
logger.addHandler(_file)
