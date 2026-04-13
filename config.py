import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "data.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # WeChat MP platform settings
    WX_MP_USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/130.0.0.0 Safari/537.36'
    )

    # Article fetch page size
    ARTICLE_PAGE_SIZE = 10

    # How many articles to show per load in the feed
    FEED_PAGE_SIZE = 20
