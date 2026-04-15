"""
WeChat Article Reader - Main Flask Application
"""

import io
import time
import requests as http_requests
from datetime import datetime
from urllib.parse import urlparse

from flask import (
    Flask, render_template, request, redirect, url_for,
    jsonify, flash, send_file, session, Response
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)

from config import Config
from models import db, bcrypt, User, Account, Subscription, Article, ReadHistory

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
bcrypt.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import wx_proxy after app setup so DB is available
from wx_proxy import wx_client


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---- Auth routes ----

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('feed'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            flash('用户名和密码不能为空', 'error')
            return render_template('register.html')
        if len(password) < 4:
            flash('密码至少需要4个字符', 'error')
            return render_template('register.html')
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'error')
            return render_template('register.html')
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)
        # New users need to login WeChat first
        return redirect(url_for('wx_login_page'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('feed'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            # If WeChat not logged in, guide user there first
            if not wx_client.is_logged_in:
                return redirect(url_for('wx_login_page'))
            return redirect(url_for('feed'))
        flash('用户名或密码错误', 'error')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ---- Main pages ----

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('feed'))
    return redirect(url_for('login'))


@app.route('/feed')
@login_required
def feed():
    wx_logged_in = wx_client.is_logged_in
    return render_template('feed.html', wx_logged_in=wx_logged_in)


@app.route('/history')
@login_required
def history_page():
    return render_template('history.html')


@app.route('/accounts')
@login_required
def accounts_page():
    return render_template('accounts.html')


@app.route('/wxlogin')
@login_required
def wx_login_page():
    return render_template('wxlogin.html')


# ---- API: WeChat Login ----

@app.route('/api/wx/qrcode')
@login_required
def api_wx_qrcode():
    """Get QR code for WeChat MP login."""
    # Store login cookies in server-side session
    result = wx_client.get_login_qrcode(session.get('wx_login_cookies', ''))
    session['wx_login_cookies'] = result['cookies']

    return send_file(
        io.BytesIO(result['qrcode']),
        mimetype=result['content_type'],
    )


@app.route('/api/wx/scan_status')
@login_required
def api_wx_scan_status():
    """Check if user has scanned the QR code."""
    cookies = session.get('wx_login_cookies', '')
    if not cookies:
        return jsonify({'status': -1, 'msg': 'No login session'})
    result = wx_client.check_scan_status(cookies)
    return jsonify(result)


@app.route('/api/wx/confirm_login', methods=['POST'])
@login_required
def api_wx_confirm_login():
    """Complete the login after user confirms."""
    cookies = session.get('wx_login_cookies', '')
    if not cookies:
        return jsonify({'success': False, 'msg': 'No login session'})
    result = wx_client.confirm_login(cookies)
    if result.get('success'):
        session.pop('wx_login_cookies', None)
    return jsonify(result)


@app.route('/api/wx/status')
@login_required
def api_wx_status():
    """Check if WeChat session is active."""
    return jsonify({
        'logged_in': wx_client.is_logged_in,
        'session_info': wx_client.session_info,
    })


# ---- API: Account subscription ----

@app.route('/api/accounts')
@login_required
def api_get_accounts():
    """Get user's subscribed accounts."""
    subs = Subscription.query.filter_by(user_id=current_user.id).all()
    accounts = []
    for sub in subs:
        acc = sub.account
        article_count = Article.query.filter_by(account_id=acc.id).count()
        accounts.append({
            'id': acc.id,
            'fakeid': acc.fakeid,
            'nickname': acc.nickname,
            'alias': acc.alias,
            'round_head_img': acc.round_head_img,
            'article_count': article_count,
            'subscribed_at': sub.created_at.isoformat() if sub.created_at else '',
        })
    return jsonify(accounts)


@app.route('/api/accounts/search', methods=['POST'])
@login_required
def api_search_account():
    """Search for public accounts by keyword."""
    keyword = request.json.get('keyword', '').strip()
    if not keyword:
        return jsonify({'success': False, 'msg': '请输入搜索关键词'})

    if not wx_client.is_logged_in:
        return jsonify({'success': False, 'msg': '微信未登录，请先扫码登录', 'need_wx_login': True})

    results = wx_client.search_account(keyword)
    if results is None:
        return jsonify({'success': False, 'msg': '搜索失败，请检查微信登录状态'})

    return jsonify({
        'success': True,
        'accounts': [{
            'fakeid': r.get('fakeid', ''),
            'nickname': r.get('nickname', ''),
            'alias': r.get('alias', ''),
            'round_head_img': r.get('round_head_img', ''),
            'service_type': r.get('service_type', 0),
        } for r in results],
    })


@app.route('/api/accounts/subscribe', methods=['POST'])
@login_required
def api_subscribe_account():
    """Subscribe to an account from search results."""
    acct_info = request.json
    return _subscribe_account(acct_info)


def _subscribe_account(acct_info):
    """Helper to subscribe to a WeChat account."""
    fakeid = acct_info.get('fakeid', '')
    nickname = acct_info.get('nickname', '')

    if not fakeid or not nickname:
        return jsonify({'success': False, 'msg': '公众号信息不完整'})

    # Find or create the Account record
    account = Account.query.filter_by(fakeid=fakeid).first()
    if not account:
        account = Account(
            fakeid=fakeid,
            nickname=nickname,
            alias=acct_info.get('alias', ''),
            round_head_img=acct_info.get('round_head_img', ''),
            service_type=acct_info.get('service_type', 0),
        )
        db.session.add(account)
        db.session.flush()

    # Check if already subscribed
    existing = Subscription.query.filter_by(
        user_id=current_user.id, account_id=account.id
    ).first()
    if existing:
        return jsonify({'success': True, 'msg': f'已经关注了 {nickname}', 'already': True})

    sub = Subscription(user_id=current_user.id, account_id=account.id)
    db.session.add(sub)
    db.session.commit()

    # Trigger initial article fetch in background
    _fetch_articles_for_account(account)

    return jsonify({'success': True, 'msg': f'成功关注 {nickname}'})


@app.route('/api/accounts/<int:account_id>/unsubscribe', methods=['POST'])
@login_required
def api_unsubscribe(account_id):
    """Unsubscribe from an account."""
    sub = Subscription.query.filter_by(
        user_id=current_user.id, account_id=account_id
    ).first()
    if sub:
        db.session.delete(sub)
        db.session.commit()
    return jsonify({'success': True})


# ---- API: Feed ----

@app.route('/api/feed')
@login_required
def api_feed():
    """Get the article feed for the current user, sorted newest first."""
    page = request.args.get('page', 1, type=int)
    per_page = Config.FEED_PAGE_SIZE

    # Get user's subscribed account IDs
    sub_account_ids = [
        s.account_id for s in
        Subscription.query.filter_by(user_id=current_user.id).all()
    ]

    if not sub_account_ids:
        return jsonify({'articles': [], 'has_more': False, 'page': page})

    # Query articles from subscribed accounts, sorted by create_time desc
    query = Article.query.filter(
        Article.account_id.in_(sub_account_ids)
    ).order_by(Article.create_time.desc())

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get read article IDs for this user
    read_ids = set()
    if paginated.items:
        article_ids = [a.id for a in paginated.items]
        read_records = ReadHistory.query.filter(
            ReadHistory.user_id == current_user.id,
            ReadHistory.article_id.in_(article_ids)
        ).all()
        read_ids = {r.article_id for r in read_records}

    articles = []
    for art in paginated.items:
        account = db.session.get(Account, art.account_id)
        articles.append({
            'id': art.id,
            'title': art.title,
            'digest': art.digest,
            'link': art.link,
            'cover': art.cover,
            'create_time': art.create_time,
            'account_name': account.nickname if account else '',
            'account_avatar': account.round_head_img if account else '',
            'is_read': art.id in read_ids,
        })

    return jsonify({
        'articles': articles,
        'has_more': paginated.has_next,
        'page': page,
    })


@app.route('/api/feed/refresh', methods=['POST'])
@login_required
def api_feed_refresh():
    """Refresh articles for all subscribed accounts."""
    if not wx_client.is_logged_in:
        return jsonify({'success': False, 'msg': '微信未登录', 'need_wx_login': True})

    sub_accounts = Subscription.query.filter_by(user_id=current_user.id).all()
    fetched = 0
    errors = 0
    for sub in sub_accounts:
        try:
            count = _fetch_articles_for_account(sub.account)
            fetched += count
        except Exception:
            errors += 1
        time.sleep(1)  # Rate limit to avoid being blocked

    return jsonify({
        'success': True,
        'fetched': fetched,
        'errors': errors,
    })


# ---- API: History ----

@app.route('/api/history')
@login_required
def api_history():
    """Get user's reading history."""
    page = request.args.get('page', 1, type=int)
    per_page = Config.FEED_PAGE_SIZE

    query = ReadHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(ReadHistory.read_at.desc())

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    history = []
    for record in paginated.items:
        art = record.article
        if not art:
            continue
        account = db.session.get(Account, art.account_id)
        history.append({
            'id': art.id,
            'title': art.title,
            'digest': art.digest,
            'link': art.link,
            'cover': art.cover,
            'create_time': art.create_time,
            'account_name': account.nickname if account else '',
            'account_avatar': account.round_head_img if account else '',
            'read_at': record.read_at.isoformat() if record.read_at else '',
        })

    return jsonify({
        'history': history,
        'has_more': paginated.has_next,
        'page': page,
    })


@app.route('/api/history/record', methods=['POST'])
@login_required
def api_record_history():
    """Record that user opened an article."""
    article_id = request.json.get('article_id')
    if not article_id:
        return jsonify({'success': False})

    # Check if already recorded recently (within 1 hour)
    existing = ReadHistory.query.filter_by(
        user_id=current_user.id,
        article_id=article_id,
    ).order_by(ReadHistory.read_at.desc()).first()

    if existing:
        # Update the read_at time
        existing.read_at = datetime.utcnow()
    else:
        record = ReadHistory(
            user_id=current_user.id,
            article_id=article_id,
        )
        db.session.add(record)

    db.session.commit()
    return jsonify({'success': True})


# ---- Helpers ----

def _fetch_articles_for_account(account, max_pages=3):
    """Fetch recent articles for an account and store them in DB."""
    total_new = 0
    begin = 0
    size = Config.ARTICLE_PAGE_SIZE

    for _ in range(max_pages):
        result = wx_client.get_article_list(account.fakeid, begin=begin, size=size)
        if not result:
            break

        for art_data in result['articles']:
            aid = str(art_data.get('aid', ''))
            title = art_data.get('title', '')
            link = art_data.get('link', '')

            if not title or not link:
                continue

            # Check if article already exists
            existing = Article.query.filter_by(
                account_id=account.id, aid=aid
            ).first() if aid else None

            if not existing and aid:
                article = Article(
                    account_id=account.id,
                    title=title,
                    digest=art_data.get('digest', ''),
                    link=link,
                    cover=art_data.get('cover', ''),
                    create_time=art_data.get('create_time', 0),
                    aid=aid,
                )
                db.session.add(article)
                total_new += 1

        db.session.commit()

        if result['is_completed']:
            break

        begin += size
        time.sleep(1)  # Rate limit

    return total_new


# ---- API: Image proxy ----

@app.route('/api/proxy/image')
def api_proxy_image():
    """Proxy WeChat images to bypass hotlink protection.

    WeChat images check the Referer header and reject direct loading from
    third-party websites. We proxy the request with a proper Referer.
    """
    img_url = request.args.get('url', '')
    if not img_url:
        return '', 400

    # Only allow proxying WeChat-related image domains
    try:
        parsed = urlparse(img_url)
        allowed_hosts = ('mmbiz.qpic.cn', 'mmbiz.qlogo.cn', 'wx.qlogo.cn',
                         'mp.weixin.qq.com', 'res.wx.qq.com')
        if parsed.hostname not in allowed_hosts:
            return '', 403
    except Exception:
        return '', 400

    try:
        resp = http_requests.get(img_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/130.0.0.0 Safari/537.36',
            'Referer': 'https://mp.weixin.qq.com/',
        }, timeout=10, stream=True)

        # Stream the image response back
        return Response(
            resp.iter_content(chunk_size=4096),
            content_type=resp.headers.get('Content-Type', 'image/jpeg'),
            headers={
                'Cache-Control': 'public, max-age=86400',
            },
        )
    except Exception:
        return '', 502


# ---- App initialization ----

with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
