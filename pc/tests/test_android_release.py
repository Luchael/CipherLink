import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import android_release
import prepare_release
from check_apk_update import Identity


class AndroidReleaseTests(unittest.TestCase):
    def test_wrong_signer_or_old_package_is_never_released(self):
        config = {'android_package': 'com.gametodo.cipherlink', 'android_signer_sha256': 'new-signer'}
        with tempfile.TemporaryDirectory() as temporary:
            apk = Path(temporary) / 'fixture.apk'
            with zipfile.ZipFile(apk, 'w') as archive:
                archive.writestr('fixture', 'synthetic')
            cases = [Identity('com.gametodo.nativeapp.preview', 37, frozenset(['new-signer'])),
                     Identity('com.gametodo.cipherlink', 37, frozenset(['old-signer'])),
                     Identity('com.gametodo.cipherlink', 36, frozenset(['new-signer']))]
            for identity in cases:
                with patch.object(android_release, 'inspect', return_value=identity):
                    with self.assertRaises(ValueError):
                        android_release.verify(apk, Path('tools'), 37, config)
            with patch.object(android_release, 'inspect', return_value=Identity(
                    'com.gametodo.cipherlink', 37, frozenset(['new-signer']))):
                android_release.verify(apk, Path('tools'), 37, config)

    def test_signing_failures_do_not_echo_private_process_output(self):
        response = subprocess.CompletedProcess([], 1, b'fixture-secret', b'fixture-password')
        with patch.object(android_release.subprocess, 'run', return_value=response):
            with self.assertRaises(RuntimeError) as error:
                android_release.command(['fixture'])
        self.assertNotIn('fixture-secret', str(error.exception))
        self.assertNotIn('fixture-password', str(error.exception))

    def test_completed_version_skips_builds_and_never_moves_existing_tag(self):
        head = 'a' * 40
        assets = [{'name': name, 'size': 42} for name in (
            'CipherLink-Windows-Setup.exe', 'CipherLink-Windows.exe', 'CipherLink-Android.apk', 'SHA256SUMS.txt', 'update.json')]
        existing = subprocess.CompletedProcess([], 0, head, '')
        published = subprocess.CompletedProcess([], 0, json.dumps({'isDraft': False, 'assets': assets}), '')
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'output'
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(out), 'REQUESTED_VERSION': ''}), \
                 patch.object(prepare_release, 'project_version', return_value=('0.11.9', 37)), \
                 patch.object(prepare_release, 'run', side_effect=[head, '', head]) as git, \
                 patch.object(prepare_release.subprocess, 'run', side_effect=[existing, published]):
                prepare_release.main()
            self.assertIn('publish=false', out.read_text())
            self.assertNotIn(['git', 'tag', 'v0.11.9', head], [call.args[0] for call in git.call_args_list])

    def test_mismatched_version_never_touches_remote(self):
        with patch.dict(os.environ, {'REQUESTED_VERSION': '0.11.8'}), \
             patch.object(prepare_release, 'project_version', return_value=('0.11.9', 37)), \
             patch.object(prepare_release, 'run') as remote:
            with self.assertRaises(ValueError):
                prepare_release.main()
        remote.assert_not_called()
