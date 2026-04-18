from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subscriptions = db.relationship('Subscription', backref='user', lazy='dynamic')
    history = db.relationship('ReadHistory', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Account(db.Model):
    """WeChat public account (公众号)"""
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    fakeid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    nickname = db.Column(db.String(200), nullable=False)
    alias = db.Column(db.String(200), default='')
    round_head_img = db.Column(db.String(500), default='')
    service_type = db.Column(db.Integer, default=0)
    last_fetch_time = db.Column(db.DateTime, nullable=True)

    articles = db.relationship('Article', backref='account', lazy='dynamic')


class AccountGroup(db.Model):
    """User-defined group for organizing subscribed accounts"""
    __tablename__ = 'account_groups'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uq_user_group_name'),
    )


class Subscription(db.Model):
    """User's subscription to an account"""
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('account_groups.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    account = db.relationship('Account')
    group = db.relationship('AccountGroup')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'account_id', name='uq_user_account'),
    )


class Article(db.Model):
    """Cached article info"""
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False, index=True)
    title = db.Column(db.Text, nullable=False)
    digest = db.Column(db.Text, default='')
    link = db.Column(db.Text, nullable=False)
    cover = db.Column(db.Text, default='')
    create_time = db.Column(db.Integer, nullable=False, index=True)  # unix timestamp
    aid = db.Column(db.String(64), default='', index=True)  # article unique id from WeChat

    __table_args__ = (
        db.UniqueConstraint('account_id', 'aid', name='uq_account_aid'),
    )


class ReadHistory(db.Model):
    """User's read history"""
    __tablename__ = 'read_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    article = db.relationship('Article')


class WxSession(db.Model):
    """Stores WeChat MP platform login session (shared across all users)"""
    __tablename__ = 'wx_sessions'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(200), nullable=False)
    cookies = db.Column(db.Text, nullable=False)  # JSON string of cookies
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
