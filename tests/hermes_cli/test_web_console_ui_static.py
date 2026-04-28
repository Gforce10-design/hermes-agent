from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB_SRC = ROOT / "web" / "src"


def test_dashboard_navigation_defaults_to_korean_labels():
    app = (WEB_SRC / "i18n" / "en.ts").read_text(encoding="utf-8")

    for label in ["콘솔", "세션", "분석", "로그", "예약 작업", "스킬", "설정", "키/환경", "문서", "채팅"]:
        assert label in app


def test_console_page_uses_korean_command_center_copy():
    console = (WEB_SRC / "pages" / "ConsolePage.tsx").read_text(encoding="utf-8")

    for text in ["Hermes 작업 지휘실", "활성 세션", "연결 채널", "제어 대상", "에이전트 스택", "게이트웨이 상태", "제어 패널", "최근 작업", "다음 단계"]:
        assert text in console

    assert "Command center for agents" not in console


def test_console_page_exposes_mobile_first_chat_launcher_copy():
    console = (WEB_SRC / "pages" / "ConsolePage.tsx").read_text(encoding="utf-8")

    for text in [
        "모바일 작업 홈",
        "새 작업 시작",
        "최근 작업 이어가기",
        "승인 대기",
        "인프라 상태",
        "채팅에서 이어가기",
        "Access 보호됨",
    ]:
        assert text in console

    assert "href=\"/chat\"" in console
    assert "chat?resume=" in console


def test_sidebar_chat_nav_resumes_most_recent_session_instead_of_starting_fresh():
    app = (WEB_SRC / "App.tsx").read_text(encoding="utf-8")

    assert "api.getSessions(1, 0)" in app
    assert "navigate(`/chat?resume=${encodeURIComponent(sessionId)}`)" in app
    assert "handleSidebarChatNav" in app


def test_dashboard_api_and_chat_have_cookie_token_fallback():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")
    chat = (WEB_SRC / "pages" / "ChatPage.tsx").read_text(encoding="utf-8")

    assert "hermes_dashboard_session" in api
    assert "getDashboardSessionToken" in api
    assert "document.cookie" in api
    assert "getDashboardSessionToken" in chat
    assert "자동 연결 토큰" in chat
