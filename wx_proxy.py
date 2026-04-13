"""
WeChat MP Platform proxy module.
Handles QR code login, session management, and article fetching.
Based on the approach from wechat-article-exporter.
"""

import json
import re
import time
import requests
from datetime import datetime, timezone, timedelta

from config import Config
from models import db, WxSession

USER_AGENT = Config.WX_MP_USER_AGENT
MP_BASE = 'https://mp.weixin.qq.com'


class WxMpClient:
    """Client for interacting with the WeChat MP platform."""

    def __init__(self):
        self._session_cache = None  # cached WxSession
        self._cookies_str = None
        self._token = None

    def _get_active_session(self):
        """Load the active WxSession from DB."""
        ws = WxSession.query.filter_by(is_active=True).order_by(
            WxSession.created_at.desc()
        ).first()
        if ws:
            self._session_cache = ws
            self._cookies_str = ws.cookies
            self._token = ws.token
        return ws

    @property
    def is_logged_in(self):
        ws = self._get_active_session()
        if not ws:
            return False
        if ws.expires_at and datetime.now(timezone.utc) > ws.expires_at:
            ws.is_active = False
            db.session.commit()
            return False
        return True

    @property
    def session_info(self):
        ws = self._get_active_session()
        if not ws:
            return None
        return {
            'created_at': ws.created_at.isoformat() if ws.created_at else None,
            'expires_at': ws.expires_at.isoformat() if ws.expires_at else None,
        }

    # ---- Login flow ----

    def start_login(self):
        """Step 1: Get a login session id from WeChat, returns sessionid for startlogin."""
        sess = requests.Session()
        sess.headers.update({
            'User-Agent': USER_AGENT,
            'Referer': f'{MP_BASE}/',
            'Origin': MP_BASE,
        })

        # Visit the login page to get initial cookies
        resp = sess.get(f'{MP_BASE}/cgi-bin/bizlogin', params={
            'action': 'startlogin',
        }, allow_redirects=False)

        # Extract session cookies
        cookies = sess.cookies.get_dict()
        return {
            'cookies': dict(sess.cookies),
            'raw_cookies': '; '.join(f'{k}={v}' for k, v in sess.cookies.items()),
        }

    def get_login_qrcode(self, cookies_str):
        """Step 2: Start the login flow and get QR code image bytes.

        Flow: POST startlogin -> GET getqrcode (returns image)
        """
        sess = requests.Session()
        sess.headers.update({
            'User-Agent': USER_AGENT,
            'Referer': f'{MP_BASE}/',
            'Origin': MP_BASE,
        })

        # Parse cookies string back
        if cookies_str:
            for part in cookies_str.split('; '):
                if '=' in part:
                    k, v = part.split('=', 1)
                    sess.cookies.set(k, v)

        # Step: POST startlogin to get uuid cookie
        resp = sess.post(
            f'{MP_BASE}/cgi-bin/bizlogin',
            params={'action': 'startlogin'},
            data={
                'userlang': 'zh_CN',
                'redirect_url': '',
                'login_type': 3,
                'sessionid': str(int(time.time() * 1000)),
                'token': '',
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': 1,
            },
        )

        # Now get the QR code image
        qr_resp = sess.get(
            f'{MP_BASE}/cgi-bin/scanloginqrcode',
            params={
                'action': 'getqrcode',
                'random': int(time.time() * 1000),
            },
        )

        all_cookies = '; '.join(f'{k}={v}' for k, v in sess.cookies.items())

        return {
            'qrcode': qr_resp.content,
            'content_type': qr_resp.headers.get('Content-Type', 'image/jpeg'),
            'cookies': all_cookies,
        }

    def check_scan_status(self, cookies_str):
        """Step 3: Poll whether the user has scanned the QR code."""
        headers = {
            'User-Agent': USER_AGENT,
            'Referer': f'{MP_BASE}/',
            'Origin': MP_BASE,
            'Cookie': cookies_str,
        }

        resp = requests.get(
            f'{MP_BASE}/cgi-bin/scanloginqrcode',
            params={
                'action': 'ask',
                'token': '',
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': 1,
            },
            headers=headers,
        )

        try:
            data = resp.json()
        except Exception:
            return {'status': -1, 'msg': 'Failed to parse response'}

        # status: 0=waiting, 1=scanned (waiting confirm), 4=confirmed, 2=cancelled/expired
        return {
            'status': data.get('status'),
            'msg': data.get('user_category', ''),
            'raw': data,
        }

    def confirm_login(self, cookies_str):
        """Step 4: After user confirms on phone, complete the login."""
        sess = requests.Session()
        sess.headers.update({
            'User-Agent': USER_AGENT,
            'Referer': f'{MP_BASE}/',
            'Origin': MP_BASE,
        })

        # Set cookies
        if cookies_str:
            for part in cookies_str.split('; '):
                if '=' in part:
                    k, v = part.split('=', 1)
                    sess.cookies.set(k, v)

        resp = sess.post(
            f'{MP_BASE}/cgi-bin/bizlogin',
            params={'action': 'login'},
            data={
                'userlang': 'zh_CN',
                'redirect_url': '',
                'cookie_forbidden': 0,
                'cookie_cleaned': 0,
                'plugin_used': 0,
                'login_type': 3,
                'token': '',
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': 1,
            },
        )

        try:
            data = resp.json()
        except Exception:
            return {'success': False, 'msg': 'Failed to parse login response'}

        redirect_url = data.get('redirect_url', '')
        if not redirect_url:
            return {'success': False, 'msg': f'Login failed: {data}'}

        # Extract token from redirect_url
        token_match = re.search(r'token=(\d+)', redirect_url)
        if not token_match:
            return {'success': False, 'msg': 'Could not extract token'}

        token = token_match.group(1)
        all_cookies = '; '.join(f'{k}={v}' for k, v in sess.cookies.items())

        # Deactivate old sessions
        WxSession.query.filter_by(is_active=True).update({'is_active': False})

        # Save new session (WeChat sessions typically last ~4 days)
        ws = WxSession(
            token=token,
            cookies=all_cookies,
            expires_at=datetime.now(timezone.utc) + timedelta(days=4),
            is_active=True,
        )
        db.session.add(ws)
        db.session.commit()

        self._session_cache = ws
        self._cookies_str = all_cookies
        self._token = token

        # Get account info
        info = self._get_account_info()

        return {
            'success': True,
            'nickname': info.get('nick_name', ''),
            'avatar': info.get('head_img', ''),
        }

    def _make_request(self, method, url, params=None, data=None):
        """Make an authenticated request to the WeChat MP platform."""
        ws = self._get_active_session()
        if not ws:
            return None

        headers = {
            'User-Agent': USER_AGENT,
            'Referer': f'{MP_BASE}/',
            'Origin': MP_BASE,
            'Cookie': ws.cookies,
        }

        if method == 'GET':
            resp = requests.get(url, params=params, headers=headers)
        else:
            resp = requests.post(url, params=params, data=data, headers=headers)

        return resp

    def _get_account_info(self):
        """Get info about the logged-in MP account."""
        resp = self._make_request('GET', f'{MP_BASE}/cgi-bin/home', params={
            't': 'home/index',
            'token': self._token,
            'lang': 'zh_CN',
        })
        if not resp:
            return {}

        html = resp.text
        nick_name = ''
        head_img = ''

        m = re.search(r'wx\.cgiData\.nick_name\s*=\s*"([^"]+)"', html)
        if m:
            nick_name = m.group(1)
        m = re.search(r'wx\.cgiData\.head_img\s*=\s*"([^"]+)"', html)
        if m:
            head_img = m.group(1)

        return {'nick_name': nick_name, 'head_img': head_img}

    # ---- Article APIs ----

    def search_account(self, keyword, begin=0, size=5):
        """Search for a public account by keyword."""
        ws = self._get_active_session()
        if not ws:
            return None

        resp = self._make_request('GET', f'{MP_BASE}/cgi-bin/searchbiz', params={
            'action': 'search_biz',
            'begin': begin,
            'count': size,
            'query': keyword,
            'token': ws.token,
            'lang': 'zh_CN',
            'f': 'json',
            'ajax': '1',
        })

        if not resp:
            return None

        try:
            data = resp.json()
        except Exception:
            return None

        if data.get('base_resp', {}).get('ret') == 200003:
            # Session expired
            ws.is_active = False
            db.session.commit()
            return None

        if data.get('base_resp', {}).get('ret') != 0:
            return None

        return data.get('list', [])

    def get_article_list(self, fakeid, begin=0, size=10):
        """Get published articles for an account."""
        ws = self._get_active_session()
        if not ws:
            return None

        resp = self._make_request('GET', f'{MP_BASE}/cgi-bin/appmsgpublish', params={
            'sub': 'list',
            'search_field': 'null',
            'begin': begin,
            'count': size,
            'query': '',
            'fakeid': fakeid,
            'type': '101_1',
            'free_publish_type': 1,
            'sub_action': 'list_ex',
            'token': ws.token,
            'lang': 'zh_CN',
            'f': 'json',
            'ajax': 1,
        })

        if not resp:
            return None

        try:
            data = resp.json()
        except Exception:
            return None

        if data.get('base_resp', {}).get('ret') == 200003:
            ws.is_active = False
            db.session.commit()
            return None

        if data.get('base_resp', {}).get('ret') != 0:
            return None

        try:
            publish_page = json.loads(data.get('publish_page', '{}'))
            publish_list = publish_page.get('publish_list', [])
            total_count = publish_page.get('total_count', 0)

            articles = []
            for item in publish_list:
                publish_info_str = item.get('publish_info', '')
                if not publish_info_str:
                    continue
                publish_info = json.loads(publish_info_str)
                for art in publish_info.get('appmsgex', []):
                    articles.append(art)

            is_completed = len(publish_list) == 0
            return {
                'articles': articles,
                'is_completed': is_completed,
                'total_count': total_count,
            }
        except (json.JSONDecodeError, KeyError):
            return None


# Global client instance
wx_client = WxMpClient()
