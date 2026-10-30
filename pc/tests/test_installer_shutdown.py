import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(sys.platform == 'win32' and os.environ.get('CIPHERLINK_SHUTDOWN_INSTALLER'),
                     'Requires a built installer on Windows')
class InstallerShutdownTests(unittest.TestCase):
    def check_shutdown(self, mode):
        result = subprocess.run([
            'pwsh', '-NoProfile', '-File', str(ROOT / 'tools/test_windows_shutdown.ps1'),
            '-Installer', os.environ['CIPHERLINK_SHUTDOWN_INSTALLER'],
            '-Version', os.environ['CIPHERLINK_SHUTDOWN_VERSION'], '-Mode', mode,
        ], capture_output=True, text=True, timeout=130)
        print(result.stdout, flush=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_hidden_application_is_stopped_and_replaced(self):
        self.check_shutdown('hidden')

    def test_visible_application_refusing_shutdown_is_stopped_and_replaced(self):
        self.check_shutdown('visible')
