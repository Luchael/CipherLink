"""Windows 데스크톱용 설정/상태 화면 (표준 라이브러리 Tkinter).

- 처음 실행 시 프로젝트 설정을 자동으로 만들고, 브라우저 로그인을 안내한다.
- 비밀번호/토큰을 UI에 입력받지 않는다. Todoist OAuth, HoYoLAB 브라우저 세션 사용.
- 네트워크 요청은 워커에서 실행해 창이 멈추지 않게 한다.
- 모바일과 동일한 아이콘을 EXE에 내장하고, 소스 실행도 지원한다.
"""
from datetime import datetime, timedelta
import json
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from .credentials import read_secret
from .settings import load_settings
from .store import Store
from .diagnostics import user_error
from .branding import APP_NAME, WINDOW_TITLE, apply_window_icon

ROOT = Path.home() / ".gametodo"
COLOR_BG = "#0D1520"
COLOR_CARD = "#172434"
COLOR_TEXT = "#E9EEF8"
COLOR_MUTED = "#9CADC4"
COLOR_ACCENT = "#5DE0C4"


def app_paths():
    """기존 설치 폴더의 config.json을 먼저 사용하여 업그레이드 설정 보존."""
    cwd_cfg = Path.cwd() / "config.json"
    if cwd_cfg.exists():
        return cwd_cfg, Path.cwd() / "data" / "game_todo.db"
    ROOT.mkdir(mode=0o700, exist_ok=True)
    cfg = ROOT / "config.json"
    if not cfg.exists():
        # 환경에 파일 리소스가 없어도 기본 설정을 직접 생성한다.
        template = Path(__file__).resolve().parents[1] / "config.example.json"
        if template.exists():
            cfg.write_bytes(template.read_bytes())
        else:
            cfg.write_text(json.dumps({"section_name": "이벤트 / 기간 한정",
                                       "poll_hours": 3, "game_settings": {}}, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    return cfg, ROOT / "data" / "game_todo.db"


class Desktop:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self._brand_icon = apply_window_icon(self.root)
        self.root.geometry("1120x770")
        self.root.minsize(900, 600)
        self.root.configure(bg=COLOR_BG)
        self.cfg, self.db = app_paths()
        self.messages = queue.Queue()
        self.busy = False
        self.watcher = threading.Event()
        self.auto_started = False
        self.confirmed_todoist = False
        self.status = tk.StringVar(value="로그인이 필요한지 확인해주세요")
        self._draw()
        self.root.after(150, self._process_messages)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        # 이전에 연결했다면 실행 시 별도 조작 없이 백그라운드 조회를 시작.
        from .oauth_login import _stored
        if (_stored() and _stored().get("access_token")) or read_secret("todoist"):
            # 저장된 인증값만으로 '연결됨'이라고 단정하지 않는다.
            self.root.after(800, self._verify_todoist)

    def _label(self, parent, text, size=11, color=COLOR_TEXT, bold=False):
        return tk.Label(parent, text=text, font=("맑은 고딕", size, "bold" if bold else "normal"),
                        bg=parent.cget("bg"), fg=color, anchor="w")

    def _button(self, parent, text, command, accent=False):
        return tk.Button(parent, text=text, command=command, relief="flat", cursor="hand2",
                         font=("맑은 고딕", 10, "bold"), padx=15, pady=10,
                         bg=COLOR_ACCENT if accent else "#304058",
                         fg=COLOR_BG if accent else COLOR_TEXT, activebackground="#A5BDFF",
                         borderwidth=0)

    def _set_lookup(self, game):
        from .account_setup import write_settings
        checked = bool(self.lookup_vars[game].get())
        if game == "wuthering" and checked:
            messagebox.showinfo("명조 글로벌", "글로벌 일일 임무 조회 API가 검증되지 않아 자동 체크를 켤 수 없습니다.\n소집 기록 조회는 일퀘 진행도가 아닙니다.")
            self.lookup_vars[game].set(False)
            return
        if game == "arknights" and checked:
            approved = messagebox.askyesno("명일방주 계정 조회 동의", "한국 시간 23:59에 Yostar 게임 계정으로 하루 한 번 로그인하여 개인 데이터를 조회합니다.\n실행할 때 게임 접속이 끊길 수 있습니다.\nPC 자동화가 실행 중이어야 하며, Android 자체 조회는 아직 미지원입니다.\n이 위험을 수용하고 켜시겠습니까?")
            if not approved:
                self.lookup_vars[game].set(False)
                return
        def apply(cfg):
            ad=cfg.setdefault('account_data',{})
            ad.setdefault('game_lookup',{})[game]=checked
            if game=='arknights' and checked:
                ad['enabled']=True
                # Actual connection token still required from user login; not invented.
                ad.setdefault('arknights',{}).setdefault('enabled',False)
        write_settings(str(self.cfg),apply)
        self.status.set(f"{game}: {'조회 켜짐' if checked else '조회 꺼짐'} · 실행 중인 PC 감시에는 재시작 후 적용")

    def _draw(self):
        """Five focused desktop pages instead of an overlong button dashboard.

        Only standard Tk widgets are used: no extra install or internet needed.
        Existing callbacks and authentication vault paths remain unchanged.
        """
        shell = tk.Frame(self.root, bg=COLOR_BG)
        shell.pack(fill="both", expand=True)
        side = tk.Frame(shell, bg="#111E2D", width=222)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        brand = tk.Frame(side, bg="#111E2D")
        brand.pack(fill="x", padx=22, pady=(27, 28))
        from .branding import icon_resource
        png = icon_resource("cipherlink.png")
        if png:
            try:
                self._sidebar_icon = tk.PhotoImage(master=self.root, file=str(png))
                # The full-resolution launcher file is too large for the sidebar.
                factor = max(1, int(self._sidebar_icon.width() / 42))
                self._sidebar_icon = self._sidebar_icon.subsample(factor, factor)
                tk.Label(brand, image=self._sidebar_icon, bg="#111E2D").pack(side="left", padx=(0, 9))
            except tk.TclError:
                pass
        tk.Label(brand, text="사이퍼링크", font=("맑은 고딕", 17, "bold"),
                 fg=COLOR_TEXT, bg="#111E2D").pack(anchor="w")
        tk.Label(brand, text="CIPHERLINK  ·  PC", font=("맑은 고딕", 9),
                 fg=COLOR_MUTED, bg="#111E2D").pack(anchor="w")
        self.nav_buttons = {}
        self.pages = {}
        self._page_names = [
            ("dashboard", "⌂  대시보드"),
            ("accounts", "◎  계정 연결"),
            ("progress", "▤  게임 진행도"),
            ("sync", "↻  동기화"),
            ("settings", "⚙  설정"),
            ("logs", "≡  활동 기록"),
        ]
        tk.Label(side, text="메뉴", bg="#111E2D", fg="#788CA3",
                 font=("맑은 고딕", 9, "bold")).pack(anchor="w", padx=24, pady=(0, 8))
        for key, label in self._page_names:
            btn = tk.Button(side, text=label, command=lambda page=key: self._show_page(page),
                 anchor="w", bg="#111E2D", fg=COLOR_MUTED, relief="flat",
                 bd=0, padx=21, pady=14, cursor="hand2", highlightthickness=0,
                 font=("맑은 고딕", 11, "bold"), activebackground="#243D4C",
                 activeforeground=COLOR_ACCENT)
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = btn
        tk.Frame(side, bg="#304051", height=1).pack(side="bottom", fill="x", padx=19, pady=(0, 0))
        tk.Label(side, text="설정과 로그인 정보는 이 PC에 보관됩니다", wraplength=180,
                 justify="left", bg="#111E2D", fg="#8799AF", font=("맑은 고딕", 9)).pack(
                     side="bottom", anchor="w", padx=20, pady=(10, 18))

        right = tk.Frame(shell, bg=COLOR_BG)
        right.pack(side="left", fill="both", expand=True)
        header = tk.Frame(right, bg=COLOR_BG, height=66)
        header.pack(fill="x", padx=28, pady=(18, 0))
        self.current_page_title = tk.StringVar(value="대시보드")
        tk.Label(header, textvariable=self.current_page_title, bg=COLOR_BG, fg=COLOR_TEXT,
                 font=("맑은 고딕", 19, "bold")).pack(side="left", anchor="w")
        self.activity_text = tk.StringVar(value="●  대기 중")
        tk.Label(header, textvariable=self.activity_text, bg="#173B37", fg=COLOR_ACCENT,
                 font=("맑은 고딕", 10, "bold"), padx=14, pady=8).pack(side="right")

        self.page_holder = tk.Frame(right, bg=COLOR_BG)
        self.page_holder.pack(fill="both", expand=True, padx=25, pady=(0, 9))
        for key, _ in self._page_names:
            page = tk.Frame(self.page_holder, bg=COLOR_BG)
            page.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.pages[key] = page
        foot = tk.Frame(right, bg="#111E2D")
        foot.pack(side="bottom", fill="x")
        tk.Label(foot, text="상태", bg="#111E2D", fg=COLOR_MUTED,
                 font=("맑은 고딕", 9, "bold")).pack(side="left", padx=(26, 10), pady=13)
        tk.Label(foot, textvariable=self.status, bg="#111E2D", fg=COLOR_ACCENT,
                 font=("맑은 고딕", 10)).pack(side="left")

        self.page_contents = {}
        for key in ("accounts", "settings", "progress"):
            outer=self.pages[key]
            canvas=tk.Canvas(outer,bg=COLOR_BG,highlightthickness=0,bd=0)
            scrollbar=tk.Scrollbar(outer,orient="vertical",command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side="right",fill="y")
            canvas.pack(side="left",fill="both",expand=True)
            inside=tk.Frame(canvas,bg=COLOR_BG)
            window=canvas.create_window((0,0),window=inside,anchor="nw")
            inside.bind("<Configure>",lambda e,c=canvas:c.configure(scrollregion=c.bbox("all")))
            canvas.bind("<Configure>",lambda e,c=canvas,w=window:c.itemconfigure(w,width=e.width))
            canvas.bind("<Enter>",lambda e,c=canvas:c.bind_all("<MouseWheel>",
                lambda evt:c.yview_scroll(int(-evt.delta/120),"units")))
            canvas.bind("<Leave>",lambda e,c=canvas:c.unbind_all("<MouseWheel>"))
            self.page_contents[key]=inside
        # Dashboard: daily action first, then account status and the quick links.
        dash = self.pages["dashboard"]
        self._page_intro(dash, "게임 진행도, Todoist 및 가챠를 한곳에서 확인하세요.")
        card = self._card(dash, "오늘의 동기화", "계정 연결 후 버튼 하나로 새 가챠와 콘텐츠 완료를 반영합니다.")
        self._button(card, "지금 동기화", self._sync, True).pack(side="left", padx=(0, 12), pady=(8, 2))
        self._button(card, "가챠 미리보기", self._preview).pack(side="left", pady=(8, 2))
        card = self._card(dash, "계정 연결 상태", "저장된 세션은 앱 밖으로 전송하지 않습니다.")
        self.auth_label = self._label(card, "연결 상태 확인 중", 10, COLOR_MUTED)
        self.auth_label.pack(anchor="w", pady=8)
        self._button(card, "연결 및 진단 열기", lambda: self._show_page("accounts")).pack(anchor="w")
        self._update_auth()
        card = self._card(dash, "앱 동작", "진행도 확인은 읽기 전용입니다. 현재 회차의 목표 점수 충족을 한 번 확인하면 완료합니다.")
        self._button(card, "자동 확인 켜기", self._auto_start).pack(side="left", padx=(0, 10), pady=(8, 0))
        self._button(card, "자동 확인 끄기", self._auto_stop).pack(side="left", pady=(8, 0))

        account = self.page_contents["accounts"]
        self._page_intro(account, "공식 로그인 화면에서 인증합니다. 비밀번호는 앱이 받지 않습니다.")
        for name, desc, command in [
            ("Todoist", "작업 생성·완료를 위한 공식 로그인", self._todoist_login),
            ("HoYoLAB", "원신 · 스타레일 · 젠레스 게임 계정 연결", self._hoyo_embedded),
            ("엔드필드 / SKPORT", "GRYPHLINE 인증과 아시아 캐릭터 바인딩", self._skport_embedded),
            ("명일방주 한국 서버", "Yostar 이메일 인증 · 게임 세션 충돌 가능", self._arknights_login),
        ]:
            card = self._card(account, name, desc)
            self._button(card, "공식 계정 연결", command, True).pack(anchor="w", pady=(7, 1))
        card = self._card(account, "게임 진행도", "연결한 계정의 일일·주간·엔드 콘텐츠 진행도를 카드로 확인합니다.")
        self._button(card, "상세 진행도 보기", self._load_progress, True).pack(anchor="w",pady=7)

        progress = self.page_contents["progress"]
        self._page_intro(progress, "점수와 목표를 한눈에 확인하세요. 조회만 하며 Todoist를 변경하지 않습니다.")
        self._button(progress, "진행도 새로고침", self._load_progress, True).pack(anchor="w",padx=4,pady=(0,15))
        self.progress_body = tk.Frame(progress,bg=COLOR_BG)
        self.progress_body.pack(fill="both",expand=True)
        self._label(self.progress_body,"게임 계정을 연결한 뒤 새로고침을 눌러주세요.",12).pack(anchor="w",padx=8,pady=15)

        sync = self.pages["sync"]
        self._page_intro(sync, "일반 이벤트는 제외하고 현재 캐릭터 픽업만 관리합니다.")
        card = self._card(sync,"수동 동기화","가챠 종료는 기존 자동 생성 작업만 완료 처리합니다.")
        self._button(card,"현재 가챠 확인",self._preview).pack(side="left",padx=(0,10),pady=8)
        self._button(card,"지금 동기화",self._sync,True).pack(side="left",pady=8)
        card = self._card(sync,"Todoist 작업 위치","가챠를 추가할 프로젝트와 섹션을 한 번 선택합니다.")
        self._button(card,"대상 프로젝트·섹션 선택",self._choose_section).pack(anchor="w",pady=8)
        card = self._card(sync,"자동 확인","자동 확인을 끄더라도 수동 동기화는 사용할 수 있습니다.")
        self._button(card,"자동 확인 켜기",self._auto_start).pack(side="left",padx=(0,10),pady=8)
        self._button(card,"자동 확인 끄기",self._auto_stop).pack(side="left",pady=8)
        self._label(sync,"명조 가챠는 한국어·KST 공개 일정 확인에 실패하면 등록을 보류합니다. 실제 일정 응답 검증은 아직 완료되지 않았습니다.",
                    10,COLOR_MUTED).pack(anchor="w",padx=14,pady=8)

        settings_page=self.page_contents["settings"]
        self._page_intro(settings_page,"각 게임의 계정 API 자동 조회를 독립적으로 관리합니다.")
        from . import __version__
        self._card(settings_page,f"사이퍼링크 {__version__}","업데이트는 앱을 종료한 뒤 새 EXE로 교체하세요. 설정과 데이터 폴더는 유지합니다.")
        card=self._card(settings_page,"게임별 계정 조회","ON/OFF는 다음 동기화부터 적용됩니다.")
        from .lookup_policy import ALL as lookup_games, enabled as lookup_enabled
        live_cfg=load_settings(str(self.cfg))
        self.lookup_vars={}
        labels={"genshin":"원신","hsr":"스타레일","zzz":"젠레스 존 제로",
                "endfield":"엔드필드","wuthering":"명조 (진행도 미지원)","arknights":"명일방주 23:59"}
        for i,game in enumerate(lookup_games):
            var=tk.BooleanVar(value=lookup_enabled(live_cfg,game));self.lookup_vars[game]=var
            row=tk.Frame(card,bg=COLOR_CARD);row.pack(fill="x",pady=4)
            tk.Label(row,text=labels[game],font=("맑은 고딕",11),fg=COLOR_TEXT,
                     bg=COLOR_CARD,anchor="w").pack(side="left")
            tk.Checkbutton(row,text="사용",variable=var,command=lambda key=game:self._set_lookup(key),
                    bg=COLOR_CARD,fg=COLOR_ACCENT,selectcolor="#223449",activebackground=COLOR_CARD,
                    activeforeground=COLOR_ACCENT,font=("맑은 고딕",10)).pack(side="right")
        self._label(card,"명일방주는 23:59(KST)에 하루 한 번 로그인합니다. 게임 세션이 종료될 수 있습니다.",
                    9,COLOR_MUTED).pack(anchor="w",pady=(8,0))
        card=self._card(settings_page,"Windows 시작 프로그램","관리자 권한 없이 로그인 시 자동 실행합니다.")
        self._button(card,"시작 프로그램 등록",self._enable_windows_startup).pack(anchor="w",pady=7)

        logpage=self.pages["logs"]
        self._page_intro(logpage,"동기화 결과와 연결 상태를 확인하세요. 인증정보는 표시하지 않습니다.")
        logs=tk.Frame(logpage,bg=COLOR_CARD,padx=17,pady=14)
        logs.pack(fill="both",expand=True,pady=(9,0),padx=3)
        self._label(logs,"실행 기록",13,COLOR_TEXT,True).pack(anchor="w",pady=(0,8))
        self.logs=tk.Text(logs,wrap="word",bg="#0C1724",fg=COLOR_TEXT,font=("Consolas",10),
                        relief="flat",insertbackground="white",padx=12,pady=10)
        self.logs.pack(fill="both",expand=True)
        self.logs.insert("end","• 계정 연결 후 '지금 동기화'를 누르세요.\n")
        self.logs.configure(state="disabled")
        self._show_page("dashboard")

    def _show_support_status(self):
        from .support_catalog import format_support_catalog
        self._show_page('logs')
        self._print(format_support_catalog())

    def _page_intro(self,page,txt):
        tk.Label(page,text=txt,bg=COLOR_BG,fg=COLOR_MUTED,
                 font=("맑은 고딕",11),anchor="w").pack(fill="x",padx=5,pady=(0,15))

    def _card(self,page,title,description):
        frame=tk.Frame(page,bg=COLOR_CARD,padx=21,pady=17)
        frame.pack(fill="x",padx=3,pady=(0,11))
        self._label(frame,title,14,COLOR_TEXT,True).pack(anchor="w")
        tk.Label(frame,text=description,bg=COLOR_CARD,fg=COLOR_MUTED,
                 wraplength=660,justify="left",anchor="w",font=("맑은 고딕",10)).pack(anchor="w",pady=(5,7))
        return frame

    def _show_page(self,key):
        names={"dashboard":"대시보드","accounts":"계정 연결","sync":"동기화",
               "settings":"설정","logs":"활동 기록","progress":"게임 진행도"}
        page=self.pages.get(key)
        if not page:return
        page.tkraise()
        self.current_page_title.set(names[key])
        for name,btn in self.nav_buttons.items():
            active=name==key
            btn.configure(bg="#1B393F" if active else "#111E2D",
                          fg=COLOR_ACCENT if active else COLOR_MUTED)

    def _update_auth(self):
        from .oauth_login import _stored
        todoist = bool(_stored() and _stored().get("access_token")) or bool(read_secret("todoist"))
        hoyo = bool(read_secret("hoyolab"))
        skport = bool(read_secret("skport"))
        self.auth_label.config(text=("Todoist: " + ("연결됨" if self.confirmed_todoist else "연결 정보 저장됨" if todoist else "로그인 필요") +
                                     "     HoYoLAB: " + ("연결 정보 저장됨" if hoyo else "로그인 필요") +
                                     "     SKPORT: " + ("연결 정보 저장됨" if skport else "로그인 필요")))

    def _print(self, message):
        self.logs.configure(state="normal")
        self.logs.insert("end", message + "\n")
        self.logs.see("end")
        self.logs.configure(state="disabled")

    def _process_messages(self):
        try:
            while True:
                kind, data = self.messages.get_nowait()
                if kind == "done":
                    self.busy = False
                    self.activity_text.set("●  작업 완료")
                    self.status.set("작업 완료")
                    self._update_auth()
                    self._print(str(data))

                elif kind == "error":
                    self.busy = False
                    self.activity_text.set("●  확인 필요")
                    self.status.set("확인 필요")
                    self._print("[오류] " + str(data))
                    self._show_page("logs")
                elif kind == "todoist_verified":
                    self.busy = False
                    self.confirmed_todoist = True
                    self._update_auth()
                    self.status.set("Todoist API 연결 확인")
                    self._print(str(data))
                    if not self.auto_started:
                        self._auto_start()
                elif kind == "progress_data":
                    self._render_progress(data)
                elif kind == "section_list":
                    self._render_section_picker(data)
                elif kind == "skport_role_list":
                    roles, reply = data
                    self._choose_skport_role(roles, reply)
                elif kind == "ask_code":
                    # Tkinter 다이얼로그는 메인 스레드에서만 띄운다.
                    reply = simpledialog.askstring("명일방주 이메일 인증", "메일로 받은 숫자 인증 코드", show="*", parent=self.root)
                    data.put(reply or "")
                elif kind == "error_log":
                    self._print("[자동 확인 오류] " + str(data))
                elif kind == "auth_progress":
                    self.status.set(str(data))
                    self._print(str(data))
                elif kind == "status":
                    self.status.set(str(data))
        except queue.Empty:
            pass
        self.root.after(150, self._process_messages)

    def _worker(self, title, fn):
        if self.busy:
            self._print("이미 실행 중인 작업이 있어요.")
            return
        self.busy = True
        self.status.set(title)
        self.activity_text.set("●  진행 중")
        def job():
            try:
                self.messages.put(("done", fn()))
            except Exception as exc:
                # 인증정보/요청 헤더가 예외 메시지에 섞일 수 있어 예외 타입만 노출
                self.messages.put(("error", user_error(exc, title)))
        threading.Thread(target=job, daemon=True).start()

    def _todoist_login(self):
        from .oauth_login import browser_login
        def connect():
            browser_login()
            # OAuth 승인 후 실제 Todoist 데이터 API 호출 성공까지 확인.
            from .http_client import HttpClient
            from .settings import get_token
            response = HttpClient(token=get_token()).request("https://api.todoist.com/api/v1/projects?limit=1")
            if not isinstance(response, (dict, list)):
                raise RuntimeError("Todoist API 응답 검증 실패")
            self.messages.put(("todoist_verified", "Todoist 로그인 및 실제 API 연결 성공"))
            return "로그인 완료"
        self._worker("Todoist 브라우저 승인/검증", connect)

    def _hoyo_embedded(self):
        """앱 전용 Edge 프로필을 사용하므로 다른 브라우저 쿠키 복호화가 필요 없다."""
        from .embedded_login import login_hoyolab
        def notify(message):
            self.messages.put(("auth_progress", message))
        self._worker("HoYoLAB 단계별 연결", lambda: login_hoyolab(str(self.cfg), notify))

    def _skport_embedded(self):
        """SKPORT 공식 로그인에서 인증 코드를 입력하고 서버가 발급한 토큰만 저장."""
        from .embedded_login import login_skport
        def notify(message):
            self.messages.put(("auth_progress", message))
        def choose_role(roles):
            reply = queue.Queue(maxsize=1)
            self.messages.put(("skport_role_list", (roles, reply)))
            return reply.get(timeout=240)
        self._worker("SKPORT 단계별 연결", lambda: login_skport(str(self.cfg), notify, choose_role=choose_role))

    def _choose_skport_role(self, roles, reply):
        """PC 메인 스레드에서 아시아 캐릭터 선택; UID는 끝 4자리만 노출."""
        dlg = tk.Toplevel(self.root)
        dlg.title(f"{APP_NAME} · 엔드필드 계정 선택")
        dlg.geometry("460x360")
        dlg.configure(bg=COLOR_BG)
        dlg.transient(self.root)
        self._label(dlg,"연결할 아시아 서버 캐릭터",16,COLOR_TEXT,True).pack(anchor="w",padx=22,pady=(24,10))
        self._label(dlg,"여러 캐릭터가 발견되었어요. 사용할 계정을 선택하세요.",10,COLOR_MUTED).pack(anchor="w",padx=22)
        picker = tk.Listbox(dlg,bg=COLOR_CARD,fg=COLOR_TEXT,
                            selectbackground=COLOR_ACCENT,selectforeground=COLOR_BG,
                            font=("맑은 고딕",12),relief="flat",height=7)
        picker.pack(fill="both",expand=True,padx=22,pady=16)
        for item in roles:
            picker.insert("end",f"{item['nickname']}     ·     Asia     ·     …{item['role_id'][-4:]}")
        def finish(value):
            if reply.empty():
                reply.put(value)
            dlg.destroy()
        def save():
            selected = picker.curselection()
            if not selected:
                messagebox.showinfo("계정 선택","연결할 캐릭터를 선택해 주세요.",parent=dlg)
                return
            item = roles[selected[0]]
            finish((item["role_id"],item["server_id"]))
        self._button(dlg,"선택한 캐릭터 연결",save,True).pack(fill="x",padx=22,pady=(0,20))
        dlg.protocol("WM_DELETE_WINDOW", lambda: finish(None))

    def _check_endfield_login(self):
        """읽기 전용 계정 진단. 닉네임·UID·토큰을 로그에 출력하지 않는다."""
        def check():
            token = read_secret("skport")
            if not token:
                return "엔드필드 로그인 정보 없음 · '엔드필드 앱 내 로그인' 버튼을 먼저 눌러주세요."
            from .skport import Skport
            from .account_setup import list_asia_endfield_roles
            binding = Skport(token).binding()
            roles = list_asia_endfield_roles(binding)
            if not roles:
                return "SKPORT 인증 응답은 받았지만 아시아 서버 바인딩 캐릭터가 없습니다."
            return "SKPORT 인증 및 아시아 캐릭터 바인딩 확인: " + str(len(roles)) + "개"
        self._worker("SKPORT 계정 읽기 전용 진단",check)

    def _wuthering_global_info(self):
        self._print("명조는 글로벌 서버 기준입니다. 중국 KuroBBS API를 더는 호출하지 않습니다. 글로벌 게임 일퀘 상태를 제공하는 검증된 계정 API가 없어 자동 체크는 건너뜁니다.")

    def _hoyo_open(self):
        from .hoyolab_login import open_login_page
        open_login_page()
        self._print("브라우저에서 HoYoLAB 로그인 후 'HoYoLAB 로그인 연동'을 눌러주세요.")

    def _hoyo_import(self):
        from .account_setup import connect_hoyolab
        self._worker("HoYoLAB 쿠키·아시아 UID 조회", lambda: connect_hoyolab(str(self.cfg)))

    def _provider_open(self, name):
        from .account_setup import open_provider
        open_provider(name)
        self._print("공식 사이트 로그인 후 옆의 계정 연결 버튼을 누르세요. 로그인 비밀번호는 앱에 저장되지 않습니다.")

    def _skport_import(self):
        from .account_setup import connect_skport
        self._worker("SKPORT 로그인 확인", lambda: connect_skport(str(self.cfg)))

    def _kuro_import(self):
        from .account_setup import connect_kurobbs
        self._worker("KuroBBS 로그인 확인", lambda: connect_kurobbs(str(self.cfg)))

    def _arknights_login(self):
        # 공식 Yostar 이메일 로그인: 이메일/숫자 코드만 사용자에게 확인.
        # 비밀번호 또는 게임 계정 세션을 가져오기 위해 메모리를 검사하지 않는다.
        email = simpledialog.askstring("Yostar 한국 서버", "명일방주 한국 서버 계정 이메일:", parent=self.root)
        if not email:
            return
        def connect():
            import asyncio
            from .arknights import _login_kr_email
            from .account_setup import write_settings
            from .credentials import save_secret
            def code_callback():
                reply = queue.Queue(maxsize=1)
                self.messages.put(("ask_code", reply))
                return reply.get(timeout=180)
            self.messages.put(("auth_progress", "[1/4] Yostar KR 인증 메일을 발송하고 있습니다"))
            uid, token = asyncio.run(_login_kr_email(email.strip(), code_callback))
            self.messages.put(("auth_progress", "[3/4] 인증코드 검증 완료. KR 서버 계정 상태를 조회해 세션을 검증합니다"))
            from .arknights import _fetch_kr
            from .embedded_login import LoginStepError
            try:
                raw = asyncio.run(_fetch_kr(uid, token))
                if not isinstance(raw, dict) or not isinstance(raw.get("user"), dict):
                    raise ValueError("account/syncData response")
            except Exception as exc:
                raise LoginStepError("3/4 KR 계정 검증", "Yostar 인증 후 게임 데이터 조회 실패. 세션/ArkPRTS 버전/계정 서버를 확인하세요") from exc
            self.messages.put(("auth_progress", "[4/4] KR 게임 데이터 확인 후 세션을 로컬에 저장합니다"))
            save_secret("arknights", token)
            def apply(cfg):
                ad = cfg.setdefault("account_data", {})
                ad["enabled"] = True
                ad.setdefault("arknights", {}).update({"enabled": True, "channel_uid": uid})
            write_settings(str(self.cfg), apply)
            return "명일방주 한국 서버 Yostar 로그인 완료"
        self._worker("명일방주 이메일 인증", connect)

    def _draw_login_tools(self, parent):
        """배포 EXE의 사용자는 개발용 패키지 설치 작업을 하지 않는다."""
        import sys
        self._button(parent,"기존 HoYoLAB 브라우저 가져오기",self._hoyo_import).pack(side="left",padx=(0,8))
        if not getattr(sys, "frozen", False):
            self._button(parent,"로그인 모듈 설치",self._install_login_modules).pack(side="left")

    def _install_login_modules(self):
        """사용자 클릭 시에만 pip 실행. 임의 패키지를 자동 설치하지 않는다."""
        import sys
        if getattr(sys, "frozen", False):
            self._print("로그인 기능은 EXE에 포함됩니다. 기능이 누락되었다면 최신 배포판 CipherLink.exe로 교체해 주세요. 기존 계정 설정은 보존됩니다.")
            return
        if not messagebox.askyesno("게임 로그인 기능 설치", "계정 연결 라이브러리(genshin.py, browser-cookie3, arkprts, playwright)를 설치할까요?", parent=self.root):
            return
        def install():
            import subprocess
            import sys
            dep = Path(__file__).resolve().parents[1] / "requirements-login.txt"
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(dep)],
                           check=True, timeout=240)
            return "로그인 라이브러리 설치 완료. '앱 내 로그인'을 눌러 직접 연결하세요."
        self._worker("게임 로그인 모듈 설치 중", install)

    def _choose_section(self):
        """Todoist 프로젝트·섹션 ID를 직접 찾고 설정에 저장한다.

        과거 버전은 '이벤트 / 기간 한정'이라는 이름을 자동으로 검색했지만,
        Todoist 프로젝트/섹션 이름이 다르거나 중복되면 실패했다.
        사용자에게 실제 서버 목록을 보여주고 한 번 선택하도록 한다.
        """
        def fetch():
            from .http_client import HttpClient
            from .settings import get_token
            from .todoist import BASE
            http = HttpClient(token=get_token())
            projects = list(http.paginated(BASE + "/projects"))
            sections = list(http.paginated(BASE + "/sections"))
            names = {str(p["id"]): p.get("name", "(프로젝트 이름 없음)") for p in projects}
            options = []
            for section in sections:
                pid = str(section.get("project_id") or "")
                if pid in names:
                    options.append((str(section["id"]), pid,
                                    str(section.get("name", "")), names[pid]))
            self.messages.put(("section_list", options))
            return f"Todoist 섹션 {len(options)}개 확인. 넣을 곳을 선택하세요."
        self._worker("Todoist 섹션 조회 중", fetch)

    def _render_section_picker(self, options):
        if not options:
            self._print("선택 가능한 섹션이 없습니다. 먼저 Todoist에서 섹션을 생성하세요.")
            return
        win = tk.Toplevel(self.root)
        win.title(f"{APP_NAME} · Todoist 대상 섹션")
        win.geometry("560x370")
        win.configure(bg=COLOR_CARD)
        tk.Label(win, text="할 일을 추가할 Todoist 섹션을 선택하세요.",
                 fg=COLOR_TEXT, bg=COLOR_CARD, font=("맑은 고딕", 12)).pack(pady=12)
        items = tk.Listbox(win, height=12, bg="#141C2A", fg=COLOR_TEXT,
                           selectbackground=COLOR_ACCENT, selectforeground=COLOR_BG,
                           font=("맑은 고딕", 10))
        items.pack(fill="both", expand=True, padx=14)
        for sid, pid, section, project in options:
            items.insert("end", f"{project}  /  {section}")
        def save():
            from .account_setup import write_settings
            selected = items.curselection()
            if not selected:
                messagebox.showinfo("섹션 선택", "섹션을 하나 선택해 주세요.", parent=win)
                return
            sid, pid, section, project = options[selected[0]]
            write_settings(str(self.cfg), lambda cfg: cfg.update({
                "section_id": sid, "project_id": pid, "section_name": section}))
            self._print(f"Todoist 대상 변경 완료: {project} / {section}")
            win.destroy()
        self._button(win, "선택한 위치에 저장", save, True).pack(pady=12)
        win.transient(self.root)
        win.grab_set()

    def _load_progress(self):
        self._show_page("progress")
        def load():
            from .account_watch import active_games
            from .progress_view import status_rows
            from .games import GAMES
            cfg = load_settings(str(self.cfg))
            groups = []
            for game, reader in active_games(cfg):
                try:
                    _, state = reader()
                    groups.append((GAMES[game].name, status_rows(state), ""))
                except Exception as exc:
                    groups.append((GAMES[game].name, [], user_error(exc)))
            self.messages.put(("progress_data",groups))
            return "게임 진행도를 새로 불러왔어요."
        self._worker("진행도를 불러오고 있어요…",load)

    def _render_progress(self, groups):
        for child in self.progress_body.winfo_children():
            child.destroy()
        if not groups:
            self._label(self.progress_body,"조회할 계정이 없어요. 계정 연결과 게임별 조회 설정을 확인해 주세요.",12).pack(anchor="w",padx=8,pady=15)
        style = ttk.Style()
        style.configure("CipherLink.Horizontal.TProgressbar",background=COLOR_ACCENT,troughcolor="#233447",thickness=8)
        for name, rows, error in groups:
            card = self._card(self.progress_body,name,"방금 조회한 게임 기록")
            if error:
                self._label(card,"기록을 가져오지 못했어요. " + error,11,COLOR_MUTED).pack(anchor="w",pady=8)
            for item in rows:
                row = tk.Frame(card,bg=COLOR_CARD)
                row.pack(fill="x",pady=(12,5))
                self._label(row,item.title,12,COLOR_TEXT,True).pack(side="left")
                self._label(row,item.value,14,COLOR_ACCENT,True).pack(side="right")
                ttk.Progressbar(card,maximum=100,value=item.percent,style="CipherLink.Horizontal.TProgressbar").pack(fill="x",pady=(0,5))
                self._label(card,item.state,10,COLOR_MUTED).pack(anchor="w")
                if item.detail:
                    tk.Label(card,text=item.detail,bg=COLOR_CARD,fg=COLOR_MUTED,font=("맑은 고딕",9),
                             wraplength=740,justify="left",anchor="w").pack(fill="x",pady=(4,0))

    def _show_provider_status(self):
        cfg = load_settings(str(self.cfg))
        acc = cfg.get("account_data") or {}
        hoyo = cfg.get("hoyolab") or {}
        statuses = ["HoYoLAB UID: " + (", ".join((hoyo.get("uids") or {}).keys()) or "없음")]
        statuses.append("명조 글로벌: 계정 데이터 API 미확인 (기존 KuroBBS 비활성화)")
        for key, secret in (("엔드필드/SKPORT", "skport"), ("명일방주/Yostar", "arknights")):
            statuses.append(f"{key}: {'인증값 저장됨' if read_secret(secret) else '로그인 필요'}")
        statuses.append("리버스: 1999·림버스 컴퍼니·스텔라 소라: 외부 계정 상태 API 미확인, 자동 감지 제외")
        self._print("\n".join(statuses))

    def _verify_todoist(self):
        def check():
            from .http_client import HttpClient
            from .settings import get_token
            response = HttpClient(token=get_token()).request("https://api.todoist.com/api/v1/projects?limit=1")
            if not isinstance(response, (dict, list)):
                raise RuntimeError("Todoist API의 프로젝트 조회에 실패했습니다")
            self.messages.put(("todoist_verified", "Todoist API 실제 연결 정상 · 프로젝트 목록 조회 성공"))
            return "Todoist 연결 시험 끝"
        self._worker("Todoist API 연결 검사", check)

    def _perform(self, dry_run):
        from .banner_sync import sync_banners
        settings = load_settings(str(self.cfg))
        store = Store(str(self.db))
        report = sync_banners(settings, store, dry_run=dry_run)
        lines = [f"현재 픽업 {len(report['active'])}개", *(" · " + t for t in report["active"])]
        if not dry_run:
            lines += [f"등록 {len(report['created'])}개 / 변경 {len(report['updated'])}개 / 종료 완료 {len(report['closed'])}개"]
        if report["errors"]:
            lines += ["가챠 수집 실패: " + ", ".join(f"{g}({reason})" for g, reason in report["errors"].items())]
        if report.get("unsupported"):
            lines += ["출처 미검증으로 건너뜀: " + ", ".join(f"{g}({reason})" for g, reason in report["unsupported"].items())]
        if not report["active"] and not report["errors"]:
            lines.append("현재 수집한 진행 중 가챠가 없습니다. 사이트 구조 또는 실제 배너 일정을 확인하세요.")
        return "\n".join(lines)

    def _preview(self):
        self._worker("현재 가챠 검색 중", lambda: self._perform(True))

    def _sync(self):
        self._worker("Todoist 자동 등록·종료 체크 중", lambda: self._perform(False))

    def _auto_start(self):
        if self.auto_started:
            return
        self.auto_started = True
        # 이전 stop Event는 재사용하면 안 된다. 빠른 중지/재시작에서
        # 종전 워커가 살아나 중복 API 요청을 보내지 않도록 각각 별도로 둔다.
        self.watcher = threading.Event()
        stop = self.watcher
        def loop():
            from .banner_sync import sync_banners
            while not stop.is_set():
                try:
                    settings = load_settings(str(self.cfg))
                    store = Store(str(self.db))
                    report = sync_banners(settings, store)
                    self.messages.put(("status", f"자동 확인 중 · 종료 {len(report['closed'])}개"))
                    next_end = store.next_banner_end()
                    wait = 900
                    if next_end:
                        wait = min(wait, max(10, int((next_end - datetime.now(next_end.tzinfo)).total_seconds()) + 8))
                    stop.wait(max(10, wait))
                except Exception as exc:
                    self.messages.put(("error_log", user_error(exc, "백그라운드 가챠 확인")))
                    self.messages.put(("status", "자동 연결 문제 발생 · 15분 뒤 재시도"))
                    stop.wait(900)
        threading.Thread(target=loop, daemon=True).start()
        # 이전 버전의 계정 상태 조회 기능도 계속 실행(인증/계정 설정이 있는 경우만).
        def poll_accounts():
            from .http_client import HttpClient
            from .todoist import Todoist
            from .settings import get_token
            from .account_watch import run_account_check
            while not stop.is_set():
                try:
                    settings = load_settings(str(self.cfg))
                    if ((settings.get("account_data") or {}).get("enabled")
                        or (settings.get("hoyolab") or {}).get("enabled")):
                        store = Store(str(self.db))
                        api = Todoist(HttpClient(store, token=get_token()),
                                      settings["section_name"], settings.get("project_id", ""),
                                      settings.get("section_id", ""))
                        api.locate()
                        run_account_check(settings, api, store)
                    mins = 15
                    stop.wait(mins * 60)
                except Exception:
                    stop.wait(900)
        threading.Thread(target=poll_accounts, daemon=True).start()
        # PC 창이 켜져 있어도 15분 확인 주기로는 23:59를 놓치므로 전용 10초 감시.
        def ark_2359():
            from .nightly_arknights import once as ark_once
            from .http_client import HttpClient
            from .todoist import Todoist
            from .settings import get_token
            while not stop.wait(10):
                try:
                    settings=load_settings(str(self.cfg))
                    from .lookup_policy import enabled as account_enabled
                    if not account_enabled(settings,'arknights'):continue
                    if not (settings.get('account_data') or {}).get('arknights',{}).get('enabled'):continue
                    # 크레덴셜 검증 실패 시 같은 날 재로그인 시도 반복 금지.
                    store=Store(str(self.db))
                    api=Todoist(HttpClient(store,token=get_token()),
                                settings['section_name'],settings.get('project_id',''),
                                settings.get('section_id',''))
                    ark_once(settings,api,store)
                except Exception as exc:
                    self.messages.put(('error_log', '명일방주 23:59 조회 오류: '+type(exc).__name__))
        threading.Thread(target=ark_2359, daemon=True).start()
        self._print("자동 확인 시작. Todoist와 가챠 종료 시각을 동기화합니다.")

    def _auto_stop(self):
        self.watcher.set()
        self.auto_started = False
        self._print("자동 확인을 중지했습니다.")

    def _enable_windows_startup(self):
        """Windows HKCU 등록: 관리자 권한 없이 현재 사용자 로그인 시 앱 실행."""
        import os
        import sys
        if os.name != "nt":
            self._print("Windows 전용 기능입니다.")
            return
        import winreg
        if getattr(sys, "frozen", False):
            command = '"' + sys.executable + '"'
        else:
            launcher = Path(__file__).resolve().parents[1] / "gametodo_desktop.py"
            pythonw = str(Path(sys.executable).with_name("pythonw.exe"))
            command = f'"{pythonw}" "{launcher}"'
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            # 구버전에서 만든 시작 항목을 중복 실행하지 않도록, 자신이 등록한
            # GameTodo 항목만 안전하게 정리하고 새 이름으로 등록한다.
            try:
                old_cmd, _ = winreg.QueryValueEx(key, "GameTodo")
            except FileNotFoundError:
                old_cmd = ""
            if isinstance(old_cmd, str) and any(
                marker in old_cmd.lower()
                for marker in ("gametodo_desktop.py", "questlink.exe", "cipherlink.exe")
            ):
                winreg.DeleteValue(key, "GameTodo")
            winreg.SetValueEx(key, "CipherLink", 0, winreg.REG_SZ, command)
        self._print("Windows에 로그인하면 사이퍼링크가 자동 시작됩니다. 해제는 Windows 시작프로그램 설정에서 가능해요.")

    def _close(self):
        self.watcher.set()
        self.root.destroy()


def start_gui():
    root = tk.Tk()
    Desktop(root)
    root.mainloop()
