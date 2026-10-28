"""Windows 앱 표시 이름/아이콘 회귀 검사. 실기기 GUI/EXE 빌드 테스트는 별개."""
import struct
import unittest
from pathlib import Path
from unittest import mock

from gametodo import branding

ROOT = Path(__file__).resolve().parents[1]


class CipherLinkBrandTests(unittest.TestCase):
    def test_new_name_and_asset_files(self):
        self.assertEqual(branding.APP_NAME, '사이퍼링크')
        self.assertEqual(branding.EXE_NAME, 'CipherLink')
        self.assertIn('사이퍼링크', branding.WINDOW_TITLE)
        self.assertTrue(branding.icon_resource('cipherlink.png').is_file())
        self.assertTrue(branding.icon_resource('cipherlink.ico').is_file())

    def test_icon_windows_multisize_ico(self):
        data = (ROOT / 'assets/cipherlink.ico').read_bytes()
        self.assertEqual(struct.unpack_from('<HH', data), (0, 1))
        self.assertEqual(struct.unpack_from('<H', data, 4)[0], 7)
        self.assertEqual((ROOT / 'assets/cipherlink.png').read_bytes()[:8], b'\x89PNG\r\n\x1a\n')

    def test_gui_uses_mobile_png_for_tk_window(self):
        fake_root = mock.Mock()
        fake_icon = object()
        with mock.patch.object(branding.tk, 'PhotoImage', return_value=fake_icon) as p:
            result = branding.apply_window_icon(fake_root)
        self.assertIs(result, fake_icon)
        self.assertEqual(p.call_args.kwargs['master'], fake_root)
        self.assertTrue(str(p.call_args.kwargs['file']).endswith('cipherlink.png'))
        fake_root.iconphoto.assert_called_once_with(True, fake_icon)

    def test_build_script_names_executable_and_embeds_assets(self):
        script = (ROOT / 'build_windows.bat').read_bytes().decode('cp949')
        self.assertIn('--name CipherLink', script)
        self.assertIn('--icon "assets\\cipherlink.ico"', script)
        self.assertIn('assets\\cipherlink.png;assets', script)
        self.assertIn('dist\\CipherLink.exe', script)
        self.assertNotIn('--name QuestLink', script)

    def test_old_markers_remain_compatible(self):
        from gametodo.todoist import MARKER
        from gametodo.banner_sync import BANNER_MARKER
        self.assertEqual(MARKER, 'GameTodo-ID: ')
        self.assertEqual(BANNER_MARKER, 'GameTodo-Banner-ID: ')


if __name__ == '__main__':
    unittest.main()
