import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

# Use persistent disk /var/data if mounted (Render cloud deployment)
default_db_url = "sqlite:////var/data/sorts.db" if os.path.exists("/var/data") else "sqlite:///sorts.db"
env_db_url = os.getenv("DATABASE_URL", "")

if os.getenv("USE_REMOTE_POSTGRES", "false").lower() == "true":
    DATABASE_URL = env_db_url
elif not env_db_url or "sqlite" in env_db_url:
    DATABASE_URL = env_db_url if env_db_url else default_db_url
else:
    # Overwrite legacy Supabase PostgreSQL DATABASE_URL leftover from previous migration
    DATABASE_URL = default_db_url

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Exempted guilds for auto-university resolution (Mahindra Uni and test servers)
EXEMPTED_GUILDS_STR = os.getenv("EXEMPTED_GUILDS", "1475575129726517349,1361752080297230376")
EXEMPTED_GUILDS = {int(x.strip()) for x in EXEMPTED_GUILDS_STR.split(",") if x.strip()}

# Configure logging
numeric_level = getattr(logging, LOG_LEVEL, logging.INFO)
logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("sortling")
from urllib.parse import urlparse
_parsed = urlparse(DATABASE_URL)
_safe_url = f"{_parsed.scheme}://***@{_parsed.hostname}{_parsed.path}"
logger.info(f"Configuration loaded. Standalone Mahindra Database: {_safe_url}")
