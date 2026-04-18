import os
import secrets
import logging
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

_logger = logging.getLogger('config')


class Config:
    # --- SECRET_KEY (persistent across gunicorn workers) ---
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        _key_file = os.path.join(BASE_DIR, '.secret_key')
        if os.path.exists(_key_file):
            with open(_key_file, 'r') as _f:
                SECRET_KEY = _f.read().strip()
        if not SECRET_KEY:
            SECRET_KEY = secrets.token_hex(32)
            try:
                with open(_key_file, 'w') as _f:
                    _f.write(SECRET_KEY)
            except OSError:
                pass
        _logger.warning('SECRET_KEY not set in environment, using file-based key.')

    # --- Database: local SQLite or Supabase PostgreSQL ---
    DB_TYPE = os.environ.get('DB_TYPE', 'auto')  # 'local', 'supabase', or 'auto'

    if DB_TYPE == 'auto':
        DB_TYPE = 'supabase' if os.environ.get('DATABASE_URL') else 'local'

    if DB_TYPE == 'local':
        _db_dir = os.path.join(BASE_DIR, 'data')
        os.makedirs(_db_dir, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(_db_dir, "app.db")}'
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
        if not SQLALCHEMY_DATABASE_URI:
            raise RuntimeError(
                'DATABASE_URL environment variable is not set. '
                'Set DB_TYPE=local in .env for SQLite, or provide DATABASE_URL for Supabase.'
            )
        # Use pg8000 (pure Python) driver so it works on Termux without compiling C extensions.
        if SQLALCHEMY_DATABASE_URI.startswith('postgresql://'):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
                'postgresql://', 'postgresql+pg8000://', 1
            )
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': 5,
            'pool_recycle': 300,
            'pool_pre_ping': True,
        }

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # WeChat MP platform settings
    WX_MP_USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/130.0.0.0 Safari/537.36'
    )

    # Article fetch / cache settings
    ARTICLE_PAGE_SIZE = 10
    FEED_PAGE_SIZE = 10
    ARTICLE_CACHE_TTL = int(os.environ.get('ARTICLE_CACHE_TTL', 30))  # minutes
    MAX_ARTICLE_PAGES = int(os.environ.get('MAX_ARTICLE_PAGES', 3))  # pages per refresh (conservative)

    # WeChat session settings
    WX_SESSION_DAYS = int(os.environ.get('WX_SESSION_DAYS', 30))  # session expiry in days
