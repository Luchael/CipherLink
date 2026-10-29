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
from .login_diagnostics import LoginApiError, login_request, numeric_status

APP_CODE = "6eb76d4e13aa36e6"


class Skport:
    def __init__(self, account_token, http=None, notify=None):
        self.token = account_token
        self.http = http or HttpClient(timeout=12)
        self.notify = notify
        self._cred = None
        self._salt = None

    @staticmethod
    def _check_response(rsp, operation):
        """An error envelope must never supply credentials or game data.

        These APIs use zero for success. Missing status fields remain compatible
        with older responses; unknown/nonzero statuses are errors, not an
        inferred token-expiration diagnosis.
        """
        if not isinstance(rsp, dict):
            raise LoginApiError(operation, response=rsp)
        for key in ('code', 'status'):
            if key not in rsp:
                continue
            if numeric_status(rsp[key]) != 0:
                raise LoginApiError(operation, response=rsp)
        if 'data' in rsp and not isinstance(rsp['data'], dict):
            raise LoginApiError(operation, response=rsp)
        return rsp.get('data') or {}

    @classmethod
    def _extract(cls, rsp, key, operation):
        data = cls._check_response(rsp, operation)
        value = data.get(key) or rsp.get(key)
        if not isinstance(value, str) or not value.strip():
            raise LoginApiError(operation, response=rsp)
        return value

    def _session(self):
        if self._cred and self._salt:
            return
        rsp = login_request(self.http, 'skport_oauth', "https://as.gryphline.com/user/oauth2/v2/grant",
                                notify=self.notify,
                                method="POST", payload={"token": self.token,
                                                         "appCode": APP_CODE, "type": 0})
        data = self._check_response(rsp, 'skport_oauth')
        # Top-level code is a status, never an OAuth authorization code.
        code = data.get('code')
        if not isinstance(code, str) or not code.strip():
            raise LoginApiError('skport_oauth', response=rsp)
        cred_rsp = login_request(self.http, 'skport_cred', "https://zonai.skport.com/web/v1/user/auth/generate_cred_by_code",
                                     notify=self.notify,
                                     method="POST", payload={"kind": 1, "code": code})
        cred = self._extract(cred_rsp, "cred", 'skport_cred')
        refresh = login_request(self.http, 'skport_refresh', "https://zonai.skport.com/web/v1/auth/refresh",
                                    notify=self.notify,
                                    headers={"cred": cred, "Origin": "https://game.skport.com"})
        # 서명 키는 2026년 문서 기준 refresh.data.token으로 제공된다.
        data = self._check_response(refresh, 'skport_refresh')
        # Preserve the legacy salt field while preferring the documented token.
        salt = data.get('token') or data.get('salt') or refresh.get('token') or refresh.get('salt')
        if not isinstance(salt, str) or not salt.strip():
            raise LoginApiError('skport_refresh', response=refresh)
        self._cred, self._salt = cred, salt

    def _signed_get(self, path, params=None, game_role=None, *, operation):
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
        rsp = login_request(self.http, operation, url, notify=self.notify, headers=headers)
        self._check_response(rsp, operation)
        if not isinstance(rsp.get("data"), dict):
            raise LoginApiError(operation, response=rsp)
        return rsp

    def binding(self):
        rsp = self._signed_get("/api/v1/game/player/binding", operation='skport_binding')
        if not isinstance(rsp['data'].get('list'), list):
            raise LoginApiError('skport_binding', response=rsp)
        return rsp

    def detail(self, role_id, server_id):
        return self._signed_get("/api/v1/game/endfield/card/detail",
                                {"roleId": role_id, "serverId": server_id},
                                game_role=f"3_{role_id}_{server_id}", operation='skport_detail')

    def indie_hard(self, role_id, server_id):
        return self._signed_get('/api/v1/game/endfield/card/indie-hard',
            {'roleId':role_id,'serverId':server_id},game_role=f'3_{role_id}_{server_id}',operation='skport_indie_hard')

    def crisis_contract(self,role_id,server_id):
        # Global read-only candidate; live Asia support is not established by the CN model.
        return self._signed_get('/api/v1/game/endfield/card/crisis-contract',
            {'roleId':role_id,'serverId':server_id},game_role=f'3_{role_id}_{server_id}',operation='skport_crisis')

    def war_echoes(self,role_id,server_id):
        return self._signed_get('/api/v1/game/endfield/card/war-echoes',
            {'roleId':role_id,'serverId':server_id},game_role=f'3_{role_id}_{server_id}',operation='skport_war_echoes')
