import os
import secrets
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError('DATABASE_URL environment variable is not set. '
                           'Copy .env.example to .env and fill in your credentials.')
    # Use pg8000 (pure Python) driver so it works on Termux without compiling C extensions.
    # Converts: postgresql://user:pass@host/db -> postgresql+pg8000://user:pass@host/db
    if SQLALCHEMY_DATABASE_URI.startswith('postgresql://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            'postgresql://', 'postgresql+pg8000://', 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }

    # WeChat MP platform settings
    WX_MP_USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/130.0.0.0 Safari/537.36'
    )

    # Article fetch page size
    ARTICLE_PAGE_SIZE = 10

    # How many articles to show per load in the feed
    FEED_PAGE_SIZE = 10
