"""초기 1회 인증값 보관.

Windows: 현재 사용자 DPAPI로 암호화.
Termux/Linux: 0600 권한 파일. (Android Keystore 암호화 아님.)
재부팅 후에도 유지하지만 HoYoLAB 측 토큰 만료 시 재인증 필요.
"""
import os
from pathlib import Path

ROOT = Path.home() / ".gametodo" / "secrets"
ALLOWED = {"todoist", "hoyolab", "bridge", "kurobbs", "skport", "arknights", "todoist_oauth"}


def _path(name):
    if name not in ALLOWED:
        raise ValueError("알 수 없는 인증값")
    return ROOT / (name + ".bin")


def _dpapi(raw: bytes, decrypt=False) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    src = ctypes.create_string_buffer(raw)
    in_blob = DATA_BLOB(len(raw), ctypes.cast(src, ctypes.POINTER(ctypes.c_byte)))
    out_blob = DATA_BLOB()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
    fn.restype = wintypes.BOOL
    # UI 없이 현재 Windows 사용자 범위로 저장
    if not fn(ctypes.byref(in_blob), None, None, None, None, 0x01, ctypes.byref(out_blob)):
        raise OSError(ctypes.get_last_error(), "Windows DPAPI 실패")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel.LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))


def save_secret(name: str, value: str):
    path = _path(name)
    if not value.strip():
        raise ValueError("인증값이 비어 있음")
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        ROOT.chmod(0o700)
    except OSError:
        pass
    raw = value.strip().encode("utf-8")
    if os.name == "nt":
        raw = _dpapi(raw)
    # 배타적 생성/권한; 기존 파일 덮어쓰기에도 경로 검사(심볼릭 링크 거부)
    if path.is_symlink():
        raise ValueError("인증 경로가 심볼릭 링크임")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
    if os.name != "nt":
        path.chmod(0o600)


def read_secret(name: str) -> str | None:
    path = _path(name)
    if not path.exists():
        return None
    if path.is_symlink():
        raise ValueError("인증 경로가 심볼릭 링크임")
    raw = path.read_bytes()
    return (_dpapi(raw, decrypt=True) if os.name == "nt" else raw).decode("utf-8")


def mobile_secret() -> str:
    """브리지 비밀키는 최초 한 번 자동 발급해 이후 재사용."""
    import secrets
    value = read_secret("bridge")
    if not value:
        value = secrets.token_urlsafe(32)
        save_secret("bridge", value)
    return value
