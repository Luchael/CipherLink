"""로컬 SQLite 캐시. 설정 및 민감한 스크린샷은 DB에 보관하지 않음."""
import sqlite3
from pathlib import Path
from threading import Lock


class Store:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=20)
        self.lock = Lock()
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=20000")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS http_cache (
              url TEXT PRIMARY KEY, etag TEXT, modified TEXT, body BLOB
            );
            CREATE TABLE IF NOT EXISTS events (
              event_key TEXT PRIMARY KEY, task_id TEXT, last_due TEXT
            );
            CREATE TABLE IF NOT EXISTS completed_occurrences (
              occurrence_key TEXT PRIMARY KEY, task_id TEXT NOT NULL,
              completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS evidence (
              event_key TEXT PRIMARY KEY, first_seen REAL, last_seen REAL, count INTEGER
            );
        """)
        self.db.execute("""CREATE TABLE IF NOT EXISTS banners (
            banner_key TEXT PRIMARY KEY, task_id TEXT, end_at TEXT,
            closed_at TEXT)
        """)
        # v0.8.1: 기존 DB를 파괴하지 않고 출처/제목/시작일 검증 칼럼만 추가.
        existing = {row[1] for row in self.db.execute("PRAGMA table_info(banners)")}
        for column in ("title", "start_date", "source_url"):
            if column not in existing:
                self.db.execute(f"ALTER TABLE banners ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
        self.db.commit()

    def record_banner(self, key: str, task_id: str, end_at: str,
                      title: str = "", start_date: str = "", source_url: str = ""):
        """기존 종료 기록을 보존하면서 픽업 종료 예정시각만 갱신."""
        with self.lock:
            self.db.execute("""INSERT INTO banners
                (banner_key,task_id,end_at,title,start_date,source_url)
                VALUES(?,?,?,?,?,?) ON CONFLICT(banner_key) DO UPDATE SET
                task_id=excluded.task_id,end_at=excluded.end_at,
                title=CASE WHEN excluded.title!='' THEN excluded.title ELSE banners.title END,
                start_date=CASE WHEN excluded.start_date!='' THEN excluded.start_date ELSE banners.start_date END,
                source_url=CASE WHEN excluded.source_url!='' THEN excluded.source_url ELSE banners.source_url END""",
                (key, task_id, end_at, title, start_date, source_url))
            self.db.commit()

    def open_banners(self):
        """Todoist 설명에는 종료 메타데이터를 넣지 않으므로 로컬 원장으로 조회."""
        with self.lock:
            return self.db.execute("""SELECT banner_key,task_id,end_at,title,start_date,source_url FROM banners
                WHERE closed_at IS NULL""").fetchall()

    def has_closed_banner(self, key: str) -> bool:
        with self.lock:
            row = self.db.execute("SELECT closed_at FROM banners WHERE banner_key=?", (key,)).fetchone()
            return bool(row and row[0])

    def record_closed_banner(self, key: str, task_id: str):
        with self.lock:
            self.db.execute("""INSERT INTO banners(banner_key,task_id,end_at,closed_at)
                VALUES(?,?, '',CURRENT_TIMESTAMP)
                ON CONFLICT(banner_key) DO UPDATE SET closed_at=CURRENT_TIMESTAMP""",
                (key, task_id))
            self.db.commit()

    def next_banner_end(self):
        """닫히지 않은 가챠 가운데 앞으로 다가오는 가장 빠른 종료 시각."""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone(timedelta(hours=9)))
        with self.lock:
            rows = self.db.execute("SELECT end_at FROM banners WHERE closed_at IS NULL").fetchall()
        upcoming = []
        for row in rows:
            try:
                ending = datetime.fromisoformat(row[0])
                if ending.tzinfo and ending > now:
                    upcoming.append(ending)
            except (TypeError, ValueError):
                pass
        return min(upcoming) if upcoming else None

    def cached(self, url):
        with self.lock:
            return self.db.execute("SELECT etag,modified,body FROM http_cache WHERE url=?", (url,)).fetchone()

    def cache(self, url, etag, modified, body):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO http_cache VALUES (?,?,?,?)", (url, etag, modified, body))
            self.db.commit()

    def event_task(self, key):
        with self.lock:
            return self.db.execute("SELECT task_id,last_due FROM events WHERE event_key=?", (key,)).fetchone()

    def record_event(self, key, task_id, due):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO events VALUES (?,?,?)", (key, str(task_id), due))
            self.db.commit()

    def evidence_seen(self, key: str, now: float, min_interval: float = 8, max_age: float = 300) -> bool:
        """한 화면의 연속 프레임을 중복 증거로 세지 않음. 2회 관측 필요."""
        with self.lock:
            last = self.db.execute("SELECT first_seen,last_seen,count FROM evidence WHERE event_key=?", (key,)).fetchone()
            if last and now - last[1] < min_interval:
                return False
            if last and now - last[0] <= max_age:
                first, count = last[0], last[2] + 1
            else:
                first, count = now, 1
            self.db.execute("INSERT OR REPLACE INTO evidence VALUES (?,?,?,?)", (key, first, now, count))
            self.db.commit()
            return count >= 2

    def has_completed(self, key: str) -> bool:
        """같은 계정/게임/콘텐츠/서버회차에 완료를 이미 보냈는가?"""
        with self.lock:
            return self.db.execute(
                "SELECT 1 FROM completed_occurrences WHERE occurrence_key=?", (key,)
            ).fetchone() is not None

    def record_completion(self, key: str, task_id: str) -> None:
        """Todoist가 완료 성공을 응답한 뒤에만 기록. 반복 실행은 무해하다."""
        with self.lock:
            self.db.execute(
                "INSERT OR IGNORE INTO completed_occurrences(occurrence_key,task_id) VALUES(?,?)",
                (key, str(task_id)))
            self.db.commit()
