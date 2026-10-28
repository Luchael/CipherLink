"""Todoist 공식 OAuth 로그인. 사용자는 토큰/키를 복사할 필요가 없다.

공식 동적 클라이언트 등록(RFC 7591)과 브라우저 승인 코드 방식을 사용.
브라우저에서는 Todoist 본인 계정으로 로그인하며 이 프로그램은 비밀번호를 보지 않는다.
유저당 최초 한 번 등록한 client_id/client_secret, refresh_token은 로컬 보안 저장소 사용.
"""
import json
import secrets
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import time
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen
import webbrowser

from .credentials import read_secret, save_secret

REGISTER_URL = "https://todoist.com/oauth/register"
AUTHORIZE_URL = "https://todoist.com/oauth/authorize"
TOKEN_URL = "https://todoist.com/oauth/access_token"
CALLBACK = "http://127.0.0.1:18766/callback"  # 로컬 개발 콜백. 외부 인터넷에 노출 금지.


def token_expiry(response, now=None):
    seconds = response.get("expires_in")
    return (time.time() if now is None else now) + int(seconds) if seconds is not None and int(seconds) > 0 else 0


def _post(url, params, *, as_json=False):
    body = (json.dumps(params).encode("utf-8") if as_json else urlencode(params).encode("utf-8"))
    headers = {"Content-Type": "application/json" if as_json else "application/x-www-form-urlencoded",
               "Accept": "application/json"}
    req = Request(url, data=body, headers=headers, method="POST")
    with urlopen(req, timeout=20) as resp:
        return json.load(resp)


def _stored():
    raw = read_secret("todoist_oauth")
    return json.loads(raw) if raw else None


def _save(config):
    save_secret("todoist_oauth", json.dumps(config, ensure_ascii=False))


def register_local_client():
    """사용자별 기기에서 자체 OAuth 앱 동적 등록. 개발자 키 직접 입력이 필요 없다."""
    settings = _stored() or {}
    if settings.get("client_id") and settings.get("redirect_uri") == CALLBACK:
        return settings
    response = _post(REGISTER_URL, {
        "client_name": "CipherLink",
        "redirect_uris": [CALLBACK],
        "scope": "data:read_write",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "client_secret_post"
    }, as_json=True)
    settings = {"client_id": response["client_id"],
                "client_secret": response.get("client_secret", ""),
                "redirect_uri": CALLBACK}
    # Commit credentials only after browser authorization succeeds.
    return settings


def browser_login(*, timeout=180):
    """Todoist 로그인 창을 열고 localhost 콜백에서만 인증 코드를 수신한다.

    반환된 state가 다르거나 인증을 취소하면 토큰 저장이 이루어지지 않는다.
    """
    config = register_local_client()
    state = secrets.token_urlsafe(32)
    result = {}
    notified = threading.Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            route = urlparse(self.path)
            if route.path != "/callback":
                self.send_error(404)
                return
            args = parse_qs(route.query)
            if args.get("state", [None])[0] != state:
                # CSRF 방지: 다른 출처의 콜백은 무시
                self.send_error(403)
                return
            result["code"] = args.get("code", [None])[0]
            result["error"] = args.get("error", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<html><body><h3>사이퍼링크 연결 처리가 끝났습니다. 이 창을 닫으세요.</h3></body></html>".encode())
            notified.set()

        def log_message(self, *args):
            pass  # 인증 코드가 담긴 URL을 콘솔에 기록하지 않는다

    try:
        server = HTTPServer(("127.0.0.1", 18766), CallbackHandler)
    except OSError as exc:
        raise RuntimeError("로컬 인증 포트 18766이 사용 중입니다") from exc
    with server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = AUTHORIZE_URL + "?" + urlencode({
            "client_id": config["client_id"], "scope": "data:read_write",
            "state": state, "response_type": "code", "redirect_uri": CALLBACK
        })
        import os
        if "ANDROID_ROOT" in os.environ:
            # Termux에서는 데스크톱 기본 브라우저 검색보다 OS 인텐트를 이용.
            import subprocess
            try:
                subprocess.run(["termux-open-url", url], check=True, timeout=10)
            except (OSError, subprocess.SubprocessError) as exc:
                raise RuntimeError("안드로이드 브라우저를 열 수 없습니다 (Termux 확인)") from exc
        else:
            webbrowser.open(url)
        notified.wait(timeout)
        server.shutdown()
        thread.join(timeout=2)
    if not notified.is_set() or not result.get("code"):
        raise RuntimeError("로그인 취소 또는 인증 시간 초과: " + str(result.get("error") or ""))
    token = _post(TOKEN_URL, {"client_id": config["client_id"],
                              "client_secret": config.get("client_secret", ""),
                              "code": result["code"],
                              "redirect_uri": CALLBACK})
    config.update({"access_token": token["access_token"],
                   "refresh_token": token.get("refresh_token", config.get("refresh_token")),
                   "expires_at": token_expiry(token)})
    _save(config)
    return True


def get_oauth_token():
    """토큰 만료 시 refresh_token으로 갱신. 불가하면 다시 브라우저 로그인 필요."""
    config = _stored()
    if not config or not config.get("access_token"):
        return None
    if not config.get("expires_at") or time.time() < float(config["expires_at"]) - 120:
        return config["access_token"]
    if not config.get("refresh_token"):
        # 구형 장기 토큰의 경우 실제 만료 전까지 사용
        return config["access_token"]
    response = _post(TOKEN_URL, {"client_id": config["client_id"],
                                 "client_secret": config.get("client_secret", ""),
                                 "grant_type": "refresh_token",
                                 "refresh_token": config["refresh_token"]})
    config["access_token"] = response["access_token"]
    config["refresh_token"] = response.get("refresh_token", config["refresh_token"])
    config["expires_at"] = token_expiry(response)
    _save(config)
    return config["access_token"]
