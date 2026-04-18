"""
WeChat Article Reader - Main Flask Application
"""

import io
import json
import logging
import os
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
from models import db, User, Account, AccountGroup, Subscription, Article, ReadHistory

# ---- Logging setup ----
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('app')

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

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
        logger.info('New user registered: %s', username)
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
            logger.info('User logged in: %s', username)
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
    logger.info('User logged out: %s', current_user.username)
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
    try:
        result = wx_client.get_login_qrcode(session.get('wx_login_cookies', ''))
    except Exception:
        logger.exception('Failed to get QR code')
        return jsonify({'error': '获取二维码失败，请稍后重试'}), 502

    if not result or not result.get('qrcode'):
        return jsonify({'error': '二维码响应为空'}), 502

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


@app.route('/api/wx/refresh_session', methods=['POST'])
@login_required
def api_wx_refresh_session():
    """Manually validate and extend the WeChat session."""
    is_valid = wx_client.validate_session()
    return jsonify({
        'success': is_valid,
        'session_info': wx_client.session_info,
        'msg': '会话已延期' if is_valid else '会话已失效，请重新登录',
    })


# ---- API: Account Groups ----

@app.route('/api/groups')
@login_required
def api_get_groups():
    """Get user's account groups."""
    groups = AccountGroup.query.filter_by(user_id=current_user.id)\
        .order_by(AccountGroup.sort_order).all()
    return jsonify([{
        'id': g.id,
        'name': g.name,
        'sort_order': g.sort_order,
        'account_count': Subscription.query.filter_by(
            user_id=current_user.id, group_id=g.id).count(),
    } for g in groups])


@app.route('/api/groups', methods=['POST'])
@login_required
def api_create_group():
    """Create a new account group."""
    name = request.json.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'msg': '分组名称不能为空'})
    existing = AccountGroup.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        return jsonify({'success': False, 'msg': '分组名称已存在'})
    max_order = db.session.query(db.func.max(AccountGroup.sort_order))\
        .filter(AccountGroup.user_id == current_user.id).scalar() or 0
    group = AccountGroup(user_id=current_user.id, name=name, sort_order=max_order + 1)
    db.session.add(group)
    db.session.commit()
    logger.info('User %s created group: %s', current_user.username, name)
    return jsonify({'success': True, 'id': group.id, 'name': group.name})


@app.route('/api/groups/<int:group_id>', methods=['PUT'])
@login_required
def api_update_group(group_id):
    """Update a group (rename or reorder)."""
    group = AccountGroup.query.filter_by(id=group_id, user_id=current_user.id).first()
    if not group:
        return jsonify({'success': False, 'msg': '分组不存在'})
    name = request.json.get('name', '').strip()
    if name:
        group.name = name
    if 'sort_order' in request.json:
        group.sort_order = request.json['sort_order']
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/groups/<int:group_id>', methods=['DELETE'])
@login_required
def api_delete_group(group_id):
    """Delete a group (moves its subscriptions to the default group)."""
    group = AccountGroup.query.filter_by(id=group_id, user_id=current_user.id).first()
    if not group:
        return jsonify({'success': False, 'msg': '分组不存在'})
    if group.name == '默认':
        return jsonify({'success': False, 'msg': '默认分组不可删除'})
    default_group = _get_or_create_default_group(current_user.id)
    Subscription.query.filter_by(user_id=current_user.id, group_id=group_id)\
        .update({'group_id': default_group.id})
    db.session.delete(group)
    db.session.commit()
    logger.info('User %s deleted group: %s', current_user.username, group.name)
    return jsonify({'success': True})


@app.route('/api/accounts/<int:account_id>/group', methods=['POST'])
@login_required
def api_set_account_group(account_id):
    """Assign an account to a group (group_id is required)."""
    raw_group_id = request.json.get('group_id')
    if not raw_group_id:
        return jsonify({'success': False, 'msg': '每个公众号必须属于一个分组'})
    group_id = int(raw_group_id)
    sub = Subscription.query.filter_by(
        user_id=current_user.id, account_id=account_id).first()
    if not sub:
        return jsonify({'success': False, 'msg': '未关注此公众号'})
    group = AccountGroup.query.filter_by(id=group_id, user_id=current_user.id).first()
    if not group:
        return jsonify({'success': False, 'msg': '分组不存在'})
    sub.group_id = group_id
    db.session.commit()
    return jsonify({'success': True})


# ---- API: Account subscription ----

@app.route('/api/accounts')
@login_required
def api_get_accounts():
    """Get user's subscribed accounts."""
    subs = Subscription.query.filter_by(user_id=current_user.id).all()
    accounts = []
    for sub in subs:
        acc = sub.account
        accounts.append({
            'id': acc.id,
            'fakeid': acc.fakeid,
            'nickname': acc.nickname,
            'alias': acc.alias,
            'round_head_img': acc.round_head_img,
            'subscribed_at': sub.created_at.isoformat() if sub.created_at else '',
            'group_id': sub.group_id,
            'group_name': sub.group.name if sub.group else None,
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

    logger.info('User %s searching for: %s', current_user.username, keyword)
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

    sub = Subscription(user_id=current_user.id, account_id=account.id,
                       group_id=_get_or_create_default_group(current_user.id).id)
    db.session.add(sub)
    db.session.commit()

    logger.info('User %s subscribed to: %s', current_user.username, nickname)

    return jsonify({'success': True, 'msg': f'成功关注 {nickname}，文章将在刷新时加载'})


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
        logger.info('User %s unsubscribed from account_id=%s', current_user.username, account_id)
    return jsonify({'success': True})


# ---- API: Feed ----

@app.route('/api/feed')
@login_required
def api_feed():
    """Get the article feed for the current user, cursor-based pagination."""
    cursor = request.args.get('cursor', type=int)  # create_time of last article
    per_page = Config.FEED_PAGE_SIZE
    group_id = request.args.get('group_id', type=int)

    # group_id is required (no "全部" tab)
    if group_id is None:
        return jsonify({'articles': [], 'has_more': False, 'next_cursor': None,
                        'has_subscriptions': False})

    # Get user's subscribed accounts filtered by group
    sub_query = Subscription.query.filter_by(user_id=current_user.id, group_id=group_id)
    subs = sub_query.all()
    sub_account_ids = [s.account_id for s in subs]

    has_subscriptions = Subscription.query.filter_by(user_id=current_user.id).count() > 0

    if not sub_account_ids:
        return jsonify({'articles': [], 'has_more': False, 'next_cursor': None,
                        'has_subscriptions': has_subscriptions})

    # Query articles with cursor-based pagination
    query = Article.query.filter(
        Article.account_id.in_(sub_account_ids)
    )
    if cursor:
        query = query.filter(Article.create_time < cursor)
    query = query.order_by(Article.create_time.desc())

    articles_raw = query.limit(per_page + 1).all()
    has_more = len(articles_raw) > per_page
    articles_raw = articles_raw[:per_page]

    next_cursor = articles_raw[-1].create_time if articles_raw else None

    # Get read article IDs for this user
    read_ids = set()
    if articles_raw:
        article_ids = [a.id for a in articles_raw]
        read_records = ReadHistory.query.filter(
            ReadHistory.user_id == current_user.id,
            ReadHistory.article_id.in_(article_ids)
        ).all()
        read_ids = {r.article_id for r in read_records}

    articles = []
    for art in articles_raw:
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
        'has_more': has_more,
        'next_cursor': next_cursor,
        'has_subscriptions': has_subscriptions,
    })


@app.route('/api/feed/refresh', methods=['POST'])
@login_required
def api_feed_refresh():
    """Sync articles for subscribed accounts in a group (1 page each).

    Returns backfill_accounts for accounts that may have more new articles.
    """
    if not wx_client.is_logged_in:
        return jsonify({'success': False, 'msg': '微信未登录', 'need_wx_login': True})

    force = False
    group_id = None
    if request.is_json:
        force = request.json.get('force', False)
        group_id = request.json.get('group_id')

    if group_id is None:
        return jsonify({'success': False, 'msg': '缺少 group_id'})

    sub_query = Subscription.query.filter_by(user_id=current_user.id, group_id=group_id)
    sub_accounts = sub_query.all()
    fetched = 0
    errors = 0
    skipped = 0
    backfill_accounts = []

    for sub in sub_accounts:
        try:
            new_count, hit_cache = _fetch_articles_for_account(
                sub.account, begin=0, max_pages=1, force=force)
            if new_count == -1:
                skipped += 1
            elif new_count >= 0:
                fetched += new_count
                # If we got a full page of new articles without hitting cache,
                # there may be more new articles to backfill
                if not hit_cache and new_count >= Config.ARTICLE_PAGE_SIZE:
                    backfill_accounts.append({
                        'account_id': sub.account.id,
                        'next_begin': Config.ARTICLE_PAGE_SIZE,
                    })
        except Exception:
            logger.exception('Error fetching articles for %s', sub.account.nickname)
            errors += 1
        time.sleep(1)  # Rate limit

    logger.info('Feed sync: user=%s group=%s fetched=%d errors=%d skipped=%d backfill=%d',
                current_user.username, group_id, fetched, errors, skipped, len(backfill_accounts))

    return jsonify({
        'success': True,
        'fetched': fetched,
        'errors': errors,
        'skipped': skipped,
        'backfill_accounts': backfill_accounts,
    })


@app.route('/api/feed/backfill', methods=['POST'])
@login_required
def api_feed_backfill():
    """Backfill more articles for accounts that didn't hit cache during sync.

    Accepts {accounts: [{account_id, begin}]}, fetches 1 page each (force=True).
    Returns updated backfill_accounts (accounts that still have more).
    """
    if not wx_client.is_logged_in:
        return jsonify({'success': False, 'msg': '微信未登录', 'need_wx_login': True})

    accounts_to_fill = request.json.get('accounts', [])
    if not accounts_to_fill:
        return jsonify({'success': True, 'fetched': 0, 'backfill_accounts': []})

    # Verify user owns these accounts via subscription
    user_account_ids = {s.account_id for s in
                        Subscription.query.filter_by(user_id=current_user.id).all()}

    fetched = 0
    updated_backfill = []

    for item in accounts_to_fill:
        account_id = item.get('account_id')
        begin = item.get('begin', 0)

        if account_id not in user_account_ids:
            continue

        account = db.session.get(Account, account_id)
        if not account:
            continue

        try:
            new_count, hit_cache = _fetch_articles_for_account(
                account, begin=begin, max_pages=1, force=True)
            if new_count > 0:
                fetched += new_count
            # If still no cache hit and got a full page, continue backfilling
            if not hit_cache and new_count >= Config.ARTICLE_PAGE_SIZE:
                updated_backfill.append({
                    'account_id': account_id,
                    'next_begin': begin + Config.ARTICLE_PAGE_SIZE,
                })
        except Exception:
            logger.exception('Error backfilling articles for %s', account.nickname)
        time.sleep(1)

    logger.info('Feed backfill: user=%s fetched=%d remaining=%d',
                current_user.username, fetched, len(updated_backfill))

    return jsonify({
        'success': True,
        'fetched': fetched,
        'backfill_accounts': updated_backfill,
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


# ---- API: Data Export/Import ----

@app.route('/api/data/export')
@login_required
def api_data_export():
    """Export all user data as JSON for migration."""
    subs = Subscription.query.filter_by(user_id=current_user.id).all()
    account_ids = [s.account_id for s in subs]

    accounts = Account.query.filter(Account.id.in_(account_ids)).all() if account_ids else []
    articles = Article.query.filter(Article.account_id.in_(account_ids)).all() if account_ids else []
    history = ReadHistory.query.filter_by(user_id=current_user.id).all()
    groups = AccountGroup.query.filter_by(user_id=current_user.id).all()

    data = {
        'version': 1,
        'exported_at': datetime.utcnow().isoformat(),
        'user': {'username': current_user.username},
        'groups': [{'name': g.name, 'sort_order': g.sort_order} for g in groups],
        'accounts': [{
            'fakeid': a.fakeid, 'nickname': a.nickname,
            'alias': a.alias, 'round_head_img': a.round_head_img,
            'service_type': a.service_type,
        } for a in accounts],
        'subscriptions': [{
            'fakeid': s.account.fakeid,
            'group_name': s.group.name if s.group else None,
        } for s in subs],
        'articles': [{
            'fakeid': a.account.fakeid if a.account else '',
            'title': a.title, 'digest': a.digest, 'link': a.link,
            'cover': a.cover, 'create_time': a.create_time, 'aid': a.aid,
        } for a in articles],
        'read_history': [{
            'article_aid': h.article.aid if h.article else '',
            'article_account_fakeid': h.article.account.fakeid if h.article and h.article.account else '',
            'read_at': h.read_at.isoformat() if h.read_at else '',
        } for h in history],
    }

    logger.info('User %s exported data: %d accounts, %d articles',
                current_user.username, len(accounts), len(articles))

    return jsonify(data)


@app.route('/api/data/import', methods=['POST'])
@login_required
def api_data_import():
    """Import user data from JSON export."""
    data = request.json
    if not data or data.get('version') != 1:
        return jsonify({'success': False, 'msg': '数据格式不正确'})

    imported_groups = 0
    imported_accounts = 0
    imported_articles = 0
    imported_subs = 0

    try:
        # Import groups
        group_map = {}  # name -> AccountGroup
        for g_data in data.get('groups', []):
            name = g_data.get('name', '').strip()
            if not name:
                continue
            existing = AccountGroup.query.filter_by(
                user_id=current_user.id, name=name).first()
            if not existing:
                existing = AccountGroup(
                    user_id=current_user.id, name=name,
                    sort_order=g_data.get('sort_order', 0))
                db.session.add(existing)
                db.session.flush()
                imported_groups += 1
            group_map[name] = existing

        # Import accounts
        account_map = {}  # fakeid -> Account
        for a_data in data.get('accounts', []):
            fakeid = a_data.get('fakeid', '')
            if not fakeid:
                continue
            existing = Account.query.filter_by(fakeid=fakeid).first()
            if not existing:
                existing = Account(
                    fakeid=fakeid, nickname=a_data.get('nickname', ''),
                    alias=a_data.get('alias', ''),
                    round_head_img=a_data.get('round_head_img', ''),
                    service_type=a_data.get('service_type', 0))
                db.session.add(existing)
                db.session.flush()
                imported_accounts += 1
            account_map[fakeid] = existing

        # Import subscriptions
        for s_data in data.get('subscriptions', []):
            fakeid = s_data.get('fakeid', '')
            account = account_map.get(fakeid)
            if not account:
                continue
            existing = Subscription.query.filter_by(
                user_id=current_user.id, account_id=account.id).first()
            if not existing:
                group_name = s_data.get('group_name')
                group = group_map.get(group_name) if group_name else None
                sub = Subscription(
                    user_id=current_user.id, account_id=account.id,
                    group_id=group.id if group else None)
                db.session.add(sub)
                imported_subs += 1

        # Import articles
        for art_data in data.get('articles', []):
            fakeid = art_data.get('fakeid', '')
            account = account_map.get(fakeid)
            if not account:
                continue
            aid = art_data.get('aid', '')
            if aid:
                existing = Article.query.filter_by(
                    account_id=account.id, aid=aid).first()
                if existing:
                    continue
            article = Article(
                account_id=account.id, title=art_data.get('title', ''),
                digest=art_data.get('digest', ''), link=art_data.get('link', ''),
                cover=art_data.get('cover', ''),
                create_time=art_data.get('create_time', 0),
                aid=aid)
            db.session.add(article)
            imported_articles += 1

        db.session.commit()

        logger.info('User %s imported data: %d groups, %d accounts, %d subs, %d articles',
                    current_user.username, imported_groups, imported_accounts,
                    imported_subs, imported_articles)

        return jsonify({
            'success': True,
            'msg': f'导入成功：{imported_groups}个分组、{imported_accounts}个公众号、'
                   f'{imported_subs}个订阅、{imported_articles}篇文章',
        })

    except Exception:
        db.session.rollback()
        logger.exception('Data import failed for user %s', current_user.username)
        return jsonify({'success': False, 'msg': '导入失败，请检查数据格式'})


# ---- Helpers ----

def _get_or_create_default_group(user_id):
    """Get or create the '默认' group for a user. Returns the AccountGroup."""
    group = AccountGroup.query.filter_by(user_id=user_id, name='默认').first()
    if not group:
        group = AccountGroup(user_id=user_id, name='默认', sort_order=0)
        db.session.add(group)
        db.session.flush()
        logger.info('Created default group for user_id=%s', user_id)
    return group


def _fetch_articles_for_account(account, begin=0, max_pages=1, force=False):
    """Fetch recent articles for an account with incremental sync.

    Stops as soon as a cached article is encountered.
    Returns (new_count, hit_cache):
      - new_count: number of new articles inserted (-1 if skipped due to cooldown)
      - hit_cache: True if stopped because a cached article was found
    """
    # Check cooldown (minutes-based)
    if not force and account.last_fetch_time:
        minutes_since = (datetime.utcnow() - account.last_fetch_time).total_seconds() / 60
        if minutes_since < Config.ARTICLE_CACHE_TTL:
            logger.debug('Skipping fetch for %s (cached %.1f min ago)',
                         account.nickname, minutes_since)
            return (-1, True)

    logger.info('Fetching articles for %s (begin=%d, max_pages=%d, force=%s)',
                account.nickname, begin, max_pages, force)

    total_new = 0
    hit_cache = False
    size = Config.ARTICLE_PAGE_SIZE
    offset = begin

    for page_num in range(max_pages):
        result = wx_client.get_article_list(account.fakeid, begin=offset, size=size)
        if not result:
            logger.warning('get_article_list returned None for %s at offset %d',
                           account.nickname, offset)
            break

        page_hit_cache = False
        for art_data in result['articles']:
            aid = str(art_data.get('aid', ''))
            title = art_data.get('title', '')
            link = art_data.get('link', '')

            if not title or not link:
                continue

            # Check if article already exists (incremental stop)
            if aid:
                existing = Article.query.filter_by(
                    account_id=account.id, aid=aid
                ).first()
                if existing:
                    hit_cache = True
                    page_hit_cache = True
                    break

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

        if page_hit_cache or result['is_completed']:
            break

        offset += size
        time.sleep(1)  # Rate limit

    # Update last fetch time
    account.last_fetch_time = datetime.utcnow()
    db.session.commit()

    logger.info('Fetched %d new articles for %s (hit_cache=%s)',
                total_new, account.nickname, hit_cache)
    return (total_new, hit_cache)



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
        logger.exception('Image proxy failed for %s', img_url)
        return '', 502


# ---- App initialization ----

with app.app_context():
    db.create_all()

    # Lightweight schema migrations for existing databases
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)

    try:
        # Add last_fetch_time to accounts if not exists
        columns = [c['name'] for c in inspector.get_columns('accounts')]
        if 'last_fetch_time' not in columns:
            db.session.execute(text(
                'ALTER TABLE accounts ADD COLUMN last_fetch_time TIMESTAMP'))
            db.session.commit()
            logger.info('Migration: added last_fetch_time to accounts')

        # Add group_id to subscriptions if not exists
        columns = [c['name'] for c in inspector.get_columns('subscriptions')]
        if 'group_id' not in columns:
            db.session.execute(text(
                'ALTER TABLE subscriptions ADD COLUMN group_id INTEGER'))
            db.session.commit()
            logger.info('Migration: added group_id to subscriptions')
    except Exception:
        logger.exception('Schema migration check failed (may be fine on fresh DB)')

    # Ensure every user has a default group, and ungrouped subscriptions are assigned
    try:
        users = User.query.all()
        for user in users:
            default_group = _get_or_create_default_group(user.id)
            ungrouped = Subscription.query.filter_by(
                user_id=user.id, group_id=None).all()
            for sub in ungrouped:
                sub.group_id = default_group.id
            if ungrouped:
                logger.info('Migration: assigned %d ungrouped subs to default group for user %s',
                            len(ungrouped), user.username)
        db.session.commit()
    except Exception:
        logger.exception('Default group migration failed')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
