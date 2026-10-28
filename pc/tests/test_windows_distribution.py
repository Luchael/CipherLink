"""Windows distribution contracts; these do not execute a Windows EXE."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gametodo.gui import Desktop


class DistributionUiTests(unittest.TestCase):
    def test_frozen_account_page_has_no_package_install_button(self):
        ui = Desktop.__new__(Desktop)
        ui._button = Mock()
        with patch.object(sys, "frozen", True, create=True):
            ui._draw_login_tools(Mock())
        labels = [call.args[1] for call in ui._button.call_args_list]
        self.assertIn("기존 HoYoLAB 브라우저 가져오기", labels)
        self.assertNotIn("로그인 모듈 설치", labels)

    def test_source_account_page_keeps_explicit_package_install(self):
        ui = Desktop.__new__(Desktop)
        ui._button = Mock()
        with patch.object(sys, "frozen", False, create=True):
            ui._draw_login_tools(Mock())
        self.assertIn("로그인 모듈 설치",
                      [call.args[1] for call in ui._button.call_args_list])

    def test_frozen_install_callback_never_starts_pip(self):
        ui = Desktop.__new__(Desktop)
        ui._print = Mock()
        ui._worker = Mock()
        with patch.object(sys, "frozen", True, create=True), \
             patch("gametodo.gui.messagebox.askyesno") as prompt:
            ui._install_login_modules()
        prompt.assert_not_called()
        ui._worker.assert_not_called()
        message = ui._print.call_args.args[0]
        self.assertIn("최신 배포판", message)
        self.assertNotIn("소스 설치판", message)
        self.assertNotIn("pip", message)

    def test_endfield_diagnostic_never_prints_character_identifiers(self):
        ui = Desktop.__new__(Desktop)
        ui._worker = lambda title, fn: results.append(fn())
        results = []
        roles = [{"nickname": "private-nickname", "role_id": "private-role-9999",
                  "server_id": "private-server"}]
        with patch("gametodo.gui.read_secret", return_value="fixture-only"), \
             patch("gametodo.skport.Skport") as provider, \
             patch("gametodo.account_setup.list_asia_endfield_roles", return_value=roles):
            provider.return_value.binding.return_value = {}
            ui._check_endfield_login()
        self.assertEqual(results, ["SKPORT 인증 및 아시아 캐릭터 바인딩 확인: 1개"])
        for secret in ("private-nickname", "private-role-9999", "9999", "private-server", "fixture-only"):
            self.assertNotIn(secret, results[0])


class WindowsBuildContractTests(unittest.TestCase):
    def test_build_checks_dependencies_resources_and_tests_before_packaging(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "build_windows.bat").read_bytes().decode("cp949")
        packaging = script.index("python -m PyInstaller")
        for prerequisite in ("python -m unittest discover -s tests -q",
                             "import tkinter, genshin, arkprts, browser_cookie3, playwright.sync_api",
                             "required build resources", "requirements-endgame.txt"):
            self.assertLess(script.index(prerequisite), packaging)
        self.assertIn("CIPHERLINK_BUILD_NONINTERACTIVE", script)
        self.assertIn("SHA256SUMS.txt", script)
        self.assertTrue((root / "build_windows.bat").read_bytes().endswith(b"\r\n"))


if __name__ == "__main__":
    unittest.main()
