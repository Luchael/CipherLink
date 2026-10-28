"""ETag/Last-Modified와 gzip을 사용한 절전/저트래픽 HTTP 클라이언트."""
import gzip
import json
import logging
import random
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LOG = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, store=None, timeout=12, token=None):
        self.store = store
        self.timeout = timeout
        self.token = token
        self.last_status = None

    def request(self, url, method="GET", payload=None, cache=False, headers=None):
        self.last_status = None
        h = {"User-Agent": "GameTodoBridge/0.1 (+personal automation)", "Accept-Encoding": "gzip"}
        if headers:
            h.update(headers)
        if self.token and url.startswith("https://api.todoist.com/"):
            h["Authorization"] = f"Bearer {self.token}"
        blob = None
        if payload is not None:
            blob = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
            h.setdefault("Content-Type", "application/json")
        old = self.store.cached(url) if cache and self.store else None
        if old:
            if old[0]: h["If-None-Match"] = old[0]
            if old[1]: h["If-Modified-Since"] = old[1]
        for attempt in range(3):
            try:
                req = Request(url, data=blob, headers=h, method=method)
                with urlopen(req, timeout=self.timeout) as res:
                    self.last_status = res.status
                    raw = res.read(2_500_001)
                    if len(raw) > 2_500_000:
                        raise ValueError("응답이 비정상적으로 큽니다")
                    if res.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                    if cache and self.store:
                        self.store.cache(url, res.headers.get("ETag"), res.headers.get("Last-Modified"), raw)
                    if not raw:
                        return None
                    if "application/json" in res.headers.get("Content-Type", ""):
                        return json.loads(raw)
                    return raw.decode("utf-8")
            except HTTPError as exc:
                self.last_status = exc.code
                if exc.code == 304 and old:
                    return json.loads(old[2]) if old[2].lstrip().startswith((b"{", b"[")) else old[2].decode("utf-8")
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
                retry_after = exc.headers.get("Retry-After", "")
                wait = int(retry_after) if retry_after.isdigit() else 2 ** attempt + random.random()
                time.sleep(min(wait, 30))
            except (URLError, TimeoutError):
                if attempt == 2: raise
                time.sleep(2 ** attempt)

    def paginated(self, url, **params):
        """Todoist API v1 results/next_cursor 모두 순회."""
        from urllib.parse import urlencode
        cursor = None
        for _ in range(30):  # 잘못된 API 응답의 무한 루프 방지
            query = dict(params)
            query["limit"] = 200
            if cursor: query["cursor"] = cursor
            join = "&" if "?" in url else "?"
            data = self.request(url + join + urlencode(query))
            if isinstance(data, list):
                yield from data
                return
            yield from data.get("results", [])
            nxt = data.get("next_cursor")
            if not nxt or nxt == cursor: return
            cursor = nxt
        raise RuntimeError("페이지 수 한도를 초과했습니다")
