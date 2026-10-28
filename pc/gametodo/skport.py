"""SKPORT 엔드필드 프로토콜 터미널의 읽기 전용 상태 조회.

참고: AixLnyt/skport-api-docs (비공식 문서). 인증 규격은 변경될 수 있다.
POST OAuth 승인과 cred 교환은 로그인 처리이며 게임 재화·보상은 변경하지 않는다.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from .http_client import HttpClient

APP_CODE = "6eb76d4e13aa36e6"


class Skport:
    def __init__(self, account_token, http=None):
        self.token = account_token
        self.http = http or HttpClient(timeout=12)
        self._cred = None
        self._salt = None

    @staticmethod
    def _extract(rsp, key):
        if not isinstance(rsp, dict):
            raise ValueError("SKPORT 형식 오류")
        return (rsp.get("data") or {}).get(key) or rsp.get(key)

    def _session(self):
        if self._cred and self._salt:
            return
        rsp = self.http.request("https://as.gryphline.com/user/oauth2/v2/grant",
                                method="POST", payload={"token": self.token,
                                                         "appCode": APP_CODE, "type": 0})
        code = self._extract(rsp, "code")
        # 응답의 최상단 code가 오류 숫자인 경우 이를 OAuth 코드로 취급하지 않는다.
        if not isinstance(code, str) or not code:
            raise ValueError("GRYPHLINE OAuth 승인 실패 (토큰 만료 가능)")
        cred_rsp = self.http.request("https://zonai.skport.com/web/v1/user/auth/generate_cred_by_code",
                                     method="POST", payload={"kind": 1, "code": code})
        cred = self._extract(cred_rsp, "cred")
        if not isinstance(cred, str) or not cred:
            raise ValueError("SKPORT cred 획득 실패")
        refresh = self.http.request("https://zonai.skport.com/web/v1/auth/refresh",
                                    headers={"cred": cred, "Origin": "https://game.skport.com"})
        # 서명 키는 2026년 문서 기준 refresh.data.token으로 제공된다.
        salt = self._extract(refresh, "token") or self._extract(refresh, "salt")
        if not isinstance(salt, str) or not salt:
            raise ValueError("SKPORT salt 획득 실패")
        self._cred, self._salt = cred, salt

    def _signed_get(self, path, params=None, game_role=None):
        self._session()
        params = params or {}
        query = urlencode(params)
        now = str(int(time.time()))
        meta = {"platform": "3", "timestamp": now, "dId": "", "vName": "1.0.0"}
        meta_str = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
        raw = f"{path}{query}{now}{meta_str}".encode("utf-8")
        digest = hmac.new(self._salt.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        sign = hashlib.md5(digest.encode("ascii")).hexdigest()
        headers = {"Content-Type": "application/json", "cred": self._cred,
                   "sign": sign, "platform": "3", "timestamp": now,
                   "dId": "", "vName": "1.0.0", "sk-language": "ko-kr",
                   "Origin": "https://game.skport.com", "Referer": "https://game.skport.com/"}
        if game_role:
            headers["sk-game-role"] = game_role
        url = f"https://zonai.skport.com{path}" + ("?" + query if query else "")
        rsp = self.http.request(url, headers=headers)
        if not isinstance(rsp, dict) or not isinstance(rsp.get("data"), dict):
            raise ValueError("SKPORT API 응답 실패/서명 규격 변경")
        return rsp

    def binding(self):
        return self._signed_get("/api/v1/game/player/binding")

    def detail(self, role_id, server_id):
        return self._signed_get("/api/v1/game/endfield/card/detail",
                                {"roleId": role_id, "serverId": server_id},
                                game_role=f"3_{role_id}_{server_id}")
