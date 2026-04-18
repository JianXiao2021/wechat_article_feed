"""
WeChat MP Platform proxy module.
Handles QR code login, session management, and article fetching.
Based on the approach from wechat-article-exporter.
"""

import json
import logging
import re
import time
import requests
from datetime import datetime, timedelta

from config import Config
from models import db, WxSession

logger = logging.getLogger('wx_proxy')

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
        if ws.expires_at and datetime.utcnow() > ws.expires_at:
            logger.info('WxSession expired, deactivating')
            ws.is_active = False
            db.session.commit()
            return False
        # If within 1 day of expiry, validate and try to extend
        if ws.expires_at and (ws.expires_at - datetime.utcnow()).total_seconds() < 86400:
            logger.info('WxSession close to expiry, validating...')
            return self.validate_session()
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

    def validate_session(self):
        """Check if the current session is still valid by making a lightweight request."""
        ws = self._get_active_session()
        if not ws:
            return False

        try:
            resp = self._make_request('GET', f'{MP_BASE}/cgi-bin/home', params={
                't': 'home/index',
                'token': ws.token,
                'lang': 'zh_CN',
            })
            if resp and resp.status_code == 200 and 'token' in resp.text:
                ws.expires_at = datetime.utcnow() + timedelta(days=Config.WX_SESSION_DAYS)
                db.session.commit()
                logger.info('WxSession validated and extended to %s', ws.expires_at)
                return True
            else:
                logger.warning('WxSession validation failed, deactivating')
                ws.is_active = False
                db.session.commit()
                return False
        except Exception:
            logger.exception('Error validating WxSession')
            return False

    # ---- Login flow ----
    # The complete WeChat MP login flow (from wechat-article-exporter):
    #   1. POST bizlogin?action=startlogin  ->  gets uuid cookie in set-cookie
    #   2. GET  scanloginqrcode?action=getqrcode  ->  returns QR image (needs uuid)
    #   3. GET  scanloginqrcode?action=ask  ->  polls scan status (needs uuid)
    #      status 0 = waiting for scan
    #      status 4/6 = scanned, waiting for user to confirm on phone
    #      status 1 = user confirmed, ready to complete login
    #      status 2/3 = expired/cancelled
    #   4. POST bizlogin?action=login  ->  completes login, gets token + session cookies

    def get_login_qrcode(self, cookies_str=''):
        """Start login flow: POST startlogin then GET qrcode.

        Uses requests.Session to accumulate cookies across steps.
        Returns qrcode image bytes and the full cookie string for subsequent calls.
        """
        sess = requests.Session()
        sess.headers.update({
            'User-Agent': USER_AGENT,
            'Referer': f'{MP_BASE}/',
            'Origin': MP_BASE,
        })

        # Load any existing cookies
        if cookies_str:
            for part in cookies_str.split('; '):
                if '=' in part:
                    k, v = part.split('=', 1)
                    sess.cookies.set(k, v)

        # Step 1: POST startlogin to get uuid cookie
        sid = str(int(time.time() * 1000)) + str(int(time.time()) % 100)
        resp = sess.post(
            f'{MP_BASE}/cgi-bin/bizlogin',
            params={'action': 'startlogin'},
            data={
                'userlang': 'zh_CN',
                'redirect_url': '',
                'login_type': 3,
                'sessionid': sid,
                'token': '',
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': 1,
            },
            timeout=15,
        )

        try:
            startlogin_data = resp.json()
            logger.info('startlogin response: %s', startlogin_data)
        except Exception:
            logger.warning('startlogin non-json response: status=%s', resp.status_code)

        # Step 2: GET the QR code image (uuid cookie is now in the session)
        qr_resp = sess.get(
            f'{MP_BASE}/cgi-bin/scanloginqrcode',
            params={
                'action': 'getqrcode',
                'random': int(time.time() * 1000),
            },
            timeout=15,
        )

        # Collect ALL cookies from the session (including uuid from startlogin)
        all_cookies = '; '.join(f'{k}={v}' for k, v in sess.cookies.items())
        logger.debug('cookies after qrcode: %s', list(sess.cookies.keys()))

        return {
            'qrcode': qr_resp.content,
            'content_type': qr_resp.headers.get('Content-Type', 'image/jpeg'),
            'cookies': all_cookies,
        }

    def check_scan_status(self, cookies_str):
        """Poll whether the user has scanned the QR code.

        Returns status:
          0 = waiting for scan
          4 or 6 = scanned, waiting for confirm on phone
          1 = confirmed, ready to call confirm_login
          2 or 3 = expired/cancelled, need to refresh QR code
          5 = account not bound to email
        """
        headers = {
            'User-Agent': USER_AGENT,
            'Referer': f'{MP_BASE}/',
            'Origin': MP_BASE,
            'Cookie': cookies_str,
        }

        try:
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
                timeout=15,
            )
        except requests.exceptions.RequestException as e:
            logger.warning('check_scan_status request failed: %s', e)
            return {'status': -1, 'msg': 'Request failed'}

        try:
            data = resp.json()
        except Exception:
            logger.warning('check_scan_status non-json response: %s', resp.status_code)
            return {'status': -1, 'msg': 'Failed to parse response'}

        return {
            'status': data.get('status'),
            'msg': data.get('user_category', ''),
            'acct_size': data.get('acct_size', 0),
        }

    def confirm_login(self, cookies_str):
        """Complete the login after user confirmed on phone (status=1).

        Uses requests.Session to properly handle cookies and set-cookies
        from the final bizlogin?action=login call.
        """
        sess = requests.Session()
        sess.headers.update({
            'User-Agent': USER_AGENT,
            'Referer': f'{MP_BASE}/',
            'Origin': MP_BASE,
        })

        # Load ALL accumulated cookies (must include uuid from startlogin)
        if cookies_str:
            for part in cookies_str.split('; '):
                if '=' in part:
                    k, v = part.split('=', 1)
                    sess.cookies.set(k, v)

        logger.debug('confirm_login cookies: %s', list(sess.cookies.keys()))

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
            timeout=15,
        )

        try:
            data = resp.json()
        except Exception:
            logger.error('confirm_login non-json response: %s %s', resp.status_code, resp.text[:500])
            return {'success': False, 'msg': '登录响应解析失败'}

        logger.info('bizlogin response: %s', data)

        redirect_url = data.get('redirect_url', '')
        if not redirect_url:
            ret = data.get('base_resp', {}).get('ret', '')
            err_msg = data.get('base_resp', {}).get('err_msg', '')
            logger.warning('Login failed: ret=%s, err=%s', ret, err_msg)
            return {'success': False, 'msg': f'登录失败 (ret={ret}, err={err_msg})'}

        # Extract token from redirect_url
        token_match = re.search(r'token=(\d+)', redirect_url)
        if not token_match:
            logger.error('Could not extract token from redirect_url: %s', redirect_url)
            return {'success': False, 'msg': '无法从重定向URL中提取token'}

        token = token_match.group(1)

        # Collect ALL cookies after login (session cookies from set-cookie are auto-merged)
        all_cookies = '; '.join(f'{k}={v}' for k, v in sess.cookies.items())
        logger.info('login success, token=%s, cookies: %s', token, list(sess.cookies.keys()))

        # Deactivate old sessions
        WxSession.query.filter_by(is_active=True).update({'is_active': False})

        # Save new session (extend to 7 days; actual validity depends on WeChat server)
        ws = WxSession(
            token=token,
            cookies=all_cookies,
            expires_at=datetime.utcnow() + timedelta(days=Config.WX_SESSION_DAYS),
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

        try:
            if method == 'GET':
                resp = requests.get(url, params=params, headers=headers, timeout=15)
            else:
                resp = requests.post(url, params=params, data=data, headers=headers, timeout=15)
            return resp
        except requests.exceptions.RequestException as e:
            logger.error('Request failed: %s %s - %s', method, url, e)
            return None

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
            logger.warning('search_account request returned None for keyword=%s', keyword)
            return None

        try:
            data = resp.json()
        except Exception:
            logger.error('search_account non-json response: %s', resp.status_code)
            return None

        if data.get('base_resp', {}).get('ret') == 200003:
            logger.warning('search_account: session expired (200003)')
            ws.is_active = False
            db.session.commit()
            return None

        if data.get('base_resp', {}).get('ret') != 0:
            logger.warning('search_account error: %s', data.get('base_resp'))
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
            logger.warning('get_article_list request returned None for fakeid=%s', fakeid)
            return None

        try:
            data = resp.json()
        except Exception:
            logger.error('get_article_list non-json response: %s', resp.status_code)
            return None

        if data.get('base_resp', {}).get('ret') == 200003:
            logger.warning('get_article_list: session expired (200003)')
            ws.is_active = False
            db.session.commit()
            return None

        if data.get('base_resp', {}).get('ret') != 0:
            logger.warning('get_article_list error: %s', data.get('base_resp'))
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
        except (json.JSONDecodeError, KeyError) as e:
            logger.error('get_article_list parse error: %s', e)
            return None


# Global client instance
wx_client = WxMpClient()
