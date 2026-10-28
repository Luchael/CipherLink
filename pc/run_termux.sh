#!/data/data/com.termux/files/usr/bin/bash
set -eu
cd "$(dirname "$0")"
if [ ! -f config.json ]; then cp config.example.json config.json; fi
# 최초 한 번만 python -m gametodo login-todoist 로 브라우저 로그인.
# 이후 세션/refresh_token 재사용. 화면 OCR은 기본적으로 비활성.
python -m gametodo run --config config.json
