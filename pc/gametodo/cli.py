"""CLI 진입점. 외부 장비/서버 없이 각 기기에서 작동."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import random
import threading
import time

from .http_client import HttpClient
from .settings import get_token, load_settings
from .store import Store
from .todoist import Todoist

LOG = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))


def run_once(settings, store, dry_run):
    """이벤트가 아닌 *현재 진행 중 픽업*만 처리하는 기존 CLI 호환 함수."""
    from .banner_sync import sync_banners
    report = sync_banners(settings, store, dry_run=dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="한국 서버 게임 Todoist 자동화")
    parser.add_argument("mode", choices=("preview", "once", "run", "pc-watch", "android-bridge", "auth", "hoyolab-once", "accounts-once", "accounts-status", "accounts-schema", "arknights-login", "mobile-key", "schedule-status", "gui", "login-todoist", "login-hoyolab", "hoyolab-import", "banners-preview", "banners-once", "doctor"))
    parser.add_argument("provider", nargs="?", choices=("todoist", "hoyolab", "kurobbs", "skport", "arknights"))
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--database", default="data/game_todo.db")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    if args.mode == "gui":
        from .gui import start_gui
        start_gui()
        return
    if args.mode == "login-todoist":
        from .oauth_login import browser_login
        browser_login()
        print("Todoist 연결 완료. 키 직접 입력 없이 사용합니다.")
        return
    if args.mode == "login-hoyolab":
        from .hoyolab_login import open_login_page
        open_login_page()
        print("브라우저에서 로그인한 다음 python -m gametodo hoyolab-import 실행")
        return
    if args.mode == "hoyolab-import":
        from .hoyolab_login import import_logged_in_browser
        import_logged_in_browser()
        print("HoYoLAB 로그인 정보 저장 완료")
        return
    if args.mode == "arknights-login":
        from .arknights import login_arknights_kr
        login_arknights_kr(args.config)
        return
    if args.mode == "auth":
        import getpass
        from .credentials import save_secret
        if args.provider is None:
            parser.error("인증 대상 입력: auth todoist 또는 auth hoyolab")
        value = getpass.getpass(f"{args.provider} 토큰/HoYoLAB 쿠키 (입력 숨김): ")
        save_secret(args.provider, value)
        print(f"{args.provider} 값 저장됨 (비밀값은 출력되지 않음)")
        return
    if args.mode == "mobile-key":
        from .credentials import mobile_secret
        print("안드로이드 앱의 연결 비밀키 입력칸에 최초 1회만 입력하세요:")
        print(mobile_secret())  # 명시적으로 키 확인을 요청한 로컬 CLI에서만 출력
        return
    settings = load_settings(args.config)
    if args.mode == "doctor":
        # 개인정보가 포함되지 않는 실행 전 연결 진단. 수동 Todoist 작업은 수정하지 않는다.
        from .diagnostics import user_error
        from .credentials import read_secret
        result = {"config": "설정 읽기 성공", "section": settings["section_name"],
                  "auth_saved": {p: bool(read_secret(p)) for p in
                                 ("todoist", "hoyolab", "kurobbs", "skport", "arknights")}}
        try:
            token = get_token()
            api = Todoist(HttpClient(token=token), settings["section_name"],
                          settings.get("project_id", ""), settings.get("section_id", ""))
            api.locate()
            result["todoist"] = "API 로그인 확인 및 대상 섹션 찾음"
        except Exception as exc:
            result["todoist"] = user_error(exc, "Todoist 대상 확인")
        # 미리보기는 로그인 없이도 실행된다. 개인정보가 없는 제목만 출력.
        try:
            from .banner_sync import sync_banners
            temp_store = Store(args.database)
            preview = sync_banners(settings, temp_store, dry_run=True)
            result["banners"] = {"found": len(preview["active"]), "errors": preview["errors"]}
            temp_store.db.close()
        except Exception as exc:
            result["banners"] = user_error(exc, "가챠 출처 확인")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    store = Store(args.database)
    if args.mode == "schedule-status":
        # 비밀번호 없이도 게임별 서버 날짜가 언제 바뀌는지 확인할 수 있다.
        from .games import GAMES
        from .cycles import before_today_reset, current_period, reset_time
        now = datetime.now(KST)
        account = settings.get("account_data") or {}
        hours = account.get("reset_hours_kst") or {}
        times = account.get("reset_times_kst") or {}
        result = []
        for key, profile in GAMES.items():
            if key == "colorsweeper":
                continue
            t = reset_time(key, hours, times)
            daily = current_period(key, "daily", now, hours, times)
            weekly = current_period(key, "weekly", now, hours, times,
                                    weekdays=account.get("weekly_reset_weekdays"))
            result.append({"game": profile.name,
                           "reset_kst": t.strftime("%H:%M") if t else "미확인(자동 완료 비활성)",
                           "before_today_reset": before_today_reset(key, now, hours, times),
                           "daily_cycle": daily.key if daily else None,
                           "weekly_cycle": weekly.key if weekly else None})
        print(json.dumps({"kst": now.isoformat(), "games": result}, ensure_ascii=False, indent=2))
        return
    if args.mode == "accounts-schema":
        # 값이 아닌 필드 구조만 출력. 닉네임, 세션 쿠키, UID는 출력하지 않는다.
        from .schema_probe import to_structure
        from .account_sources import _read_hoyolab_async, _asia_uid
        from .credentials import read_secret
        import asyncio
        result = {}
        hoyo = settings.get("hoyolab") or {}
        for game, uid in (hoyo.get("uids") or {}).items():
            if game not in ("genshin", "hsr", "zzz") or not _asia_uid(game, uid):
                continue
            try:
                cookie = read_secret("hoyolab")
                if not cookie:
                    result[game] = "HoYoLAB 쿠키 미설정"
                else:
                    result[game] = to_structure(asyncio.run(_read_hoyolab_async(uid, cookie, game)))
            except Exception as exc:
                # 오류 세부메시지에 개인 정보가 포함될 수 있으므로 타입만 공개.
                result[game] = f"상태 조회 오류: {type(exc).__name__}"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.mode == "accounts-status":
        from .account_watch import run_account_check
        # 상태 조회에 Todoist 토큰 자체가 필요하지 않음.
        print(json.dumps(run_account_check(settings, read_only=True), ensure_ascii=False, indent=2))
        return
    if args.mode in ("preview", "banners-preview"):
        run_once(settings, store, True)
        return
    if args.mode in ("once", "banners-once"):
        run_once(settings, store, False)
        return

    # 게임 화면 감지 전용 모드에서도 Todoist 연결 확인.
    http = HttpClient(store, token=get_token())
    api = Todoist(http, settings["section_name"], settings.get("project_id", ""), settings.get("section_id", ""))
    api.locate()
    from .observer import Observer
    observer = Observer(settings, api, store)

    if args.mode == "accounts-once":
        from .account_watch import run_account_check
        print(json.dumps(run_account_check(settings, api, store), ensure_ascii=False, indent=2))
        return
    if args.mode == "hoyolab-once":
        from .hoyolab import check_once
        print(check_once(settings, api, store))
        return
    if args.mode == "pc-watch":
        from .windows_capture import watch
        watch(settings, observer, settings.get("screen_interval_sec", 30))
    if args.mode == "android-bridge":
        from .bridge import run_bridge
        from .credentials import mobile_secret
        run_bridge(observer, os.environ.get("LOCAL_BRIDGE_SECRET") or mobile_secret(),
                   settings.get("bridge_port", 8765))
    if args.mode == "run":
        # 계정 API는 별도 주기로 확인. 인증을 초기 한 번 저장해 PC/Termux 독립 사용.
        # 실제 게임 창이 없어도 일일 상태를 조회할 수 있음. OCR은 기본적으로 사용 안 함.
        if (settings.get("hoyolab") or {}).get("enabled") or (settings.get("account_data") or {}).get("enabled"):
            def poll_account():
                from .account_watch import run_account_check
                while True:
                    for result in run_account_check(settings, api, store):
                        LOG.info("[%s] %s", result["game"], result["action"])
                    mins = 15
                    time.sleep(mins * 60)
            threading.Thread(target=poll_account, daemon=True, name="account-game-data").start()
        # 23:59 KST daily once opt-in. This one request may disconnect the game.
        from .lookup_policy import enabled as lookup_enabled
        ark = (settings.get("account_data") or {}).get("arknights") or {}
        if lookup_enabled(settings,"arknights") and ark.get("enabled"):
            from .nightly_arknights import wait_loop as arknights_nightly
            threading.Thread(target=arknights_nightly, args=(settings,api,store),
                             daemon=True, name="arknights-2359-kst").start()
        # 휴대폰: 접근성 앱이 있을 때만 OCR 브리지를 시작합니다.
        secret = os.environ.get("LOCAL_BRIDGE_SECRET", "")
        if settings.get("enable_android_bridge", False) and os.name != "nt":
            from .credentials import mobile_secret
            secret = secret or mobile_secret()
            from .bridge import run_bridge
            threading.Thread(target=run_bridge, args=(observer, secret, settings.get("bridge_port", 8765)),
                             daemon=True, name="android-ocr-bridge").start()
        # PC: 화면 규칙을 켠 경우에만 OCR을 시작하며, 게임이 비활성일 때는 쉬게 됩니다.
        if any(r.get("enabled") for r in settings.get("screen_rules", [])) and os.name == "nt":
            from .windows_capture import watch
            threading.Thread(target=watch, args=(settings, observer, settings.get("screen_interval_sec", 30)),
                             daemon=True, name="pc-ocr-watch").start()
        # 절전: 픽업 목록은 최대 설정 시간마다 확인하되, 알려진 가챠 종료 시각은
        # 되도록 정확히 맞춰서 자동 완료한다. 화면 인식/별도 장비 사용 없음.
        while True:
            try:
                run_once(settings, store, False)
            except Exception as exc:
                LOG.error("가챠 동기화 오류: %s", type(exc).__name__)
            upcoming = store.next_banner_end()
            sleep = 900.0 + random.uniform(0, 30)
            if upcoming:
                left = (upcoming - datetime.now(KST)).total_seconds()
                if left > 0:
                    sleep = min(sleep, max(10.0, left + 8.0))
            time.sleep(max(10, sleep))


if __name__ == "__main__":
    main()
