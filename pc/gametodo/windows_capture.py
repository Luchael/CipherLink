"""Windows 게임 창이 실제로 전면에 있을 때만 저빈도로 OCR.

선택 종속성: mss, Pillow, pytesseract 및 사용자가 설치한 Tesseract 한국어 데이터.
윈도우 후킹, 게임 메모리/패킷 분석, 입력 조작은 하지 않음.
"""
import ctypes
import logging
import time

LOG = logging.getLogger(__name__)


def foreground_title():
    u32 = ctypes.windll.user32
    hwnd = u32.GetForegroundWindow()
    size = u32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(size + 1)
    u32.GetWindowTextW(hwnd, buf, size + 1)
    rect = (ctypes.c_long * 4)()
    if not u32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return "", None
    x1, y1, x2, y2 = rect
    return buf.value, (x1, y1, x2 - x1, y2 - y1)


def watch(config, observer, interval=30):
    import platform
    if platform.system() != "Windows":
        raise OSError("PC OCR 감지기는 Windows 전용입니다")
    try:
        import mss
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError("PC OCR 기능: pip install -r requirements-pc.txt 필요") from exc
    titles = config.get("window_titles", {})
    LOG.info("PC 게임 창 OCR 감시 시작 (%.0f초 주기)", interval)
    with mss.mss() as capture:
        while True:
            try:
                title, (x,y,w,h) = foreground_title()
            except (TypeError, ValueError):
                time.sleep(interval)
                continue
            active = next((game for game, names in titles.items()
                           if any(name.lower() in title.lower() for name in names)), None)
            if active and w > 250 and h > 250:
                try:
                    # 전경 창만 캡처. 스크린샷은 디스크/인터넷에 업로드하지 않음.
                    im = capture.grab({"left": max(0,x), "top": max(0,y),
                                       "width": min(w, 3840), "height": min(h, 2160)})
                    pic = Image.frombytes("RGB", im.size, im.rgb)
                    pic.thumbnail((1280, 720))  # OCR 속도와 배터리 사용량 절감
                    gray = ImageOps.grayscale(pic)
                    text = pytesseract.image_to_string(gray, lang="kor+eng", config="--psm 11")
                    changed = observer.evaluate(active, text)
                    if changed: LOG.info("완료: %s", ", ".join(changed))
                except Exception as exc:
                    LOG.warning("PC 화면 감지 실패: %s", exc)
            time.sleep(interval)
