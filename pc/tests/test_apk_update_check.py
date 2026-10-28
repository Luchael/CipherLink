import importlib.util
from pathlib import Path
import sys
import unittest

source = Path(__file__).resolve().parents[2] / 'tools/check_apk_update.py'
spec = importlib.util.spec_from_file_location('cipherlink_apk_check', source)
check = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = check
spec.loader.exec_module(check)


class ApkUpdateTests(unittest.TestCase):
    def test_higher_version_does_not_fix_different_signer(self):
        old = check.Identity('com.gametodo.nativeapp', 23, frozenset({'original'}))
        new = check.Identity('com.gametodo.nativeapp', 27, frozenset({'cloud'}))
        self.assertEqual(check.check_update(old, new), 'SIGNATURE_MISMATCH')

    def test_separate_install_is_not_misrepresented_as_an_update(self):
        old = check.Identity('com.gametodo.nativeapp', 23, frozenset({'original'}))
        new = check.Identity('com.gametodo.nativeapp.preview', 27, frozenset({'cloud'}))
        self.assertEqual(check.check_update(old, new), 'SEPARATE_APPLICATION')

    def test_same_cloud_signer_higher_version_is_metadata_compatible(self):
        old = check.Identity('com.gametodo.nativeapp', 25, frozenset({'cloud'}))
        new = check.Identity('com.gametodo.nativeapp', 27, frozenset({'cloud'}))
        self.assertEqual(check.check_update(old, new), 'UPDATE_METADATA_COMPATIBLE')

    def test_downgrade_or_repeated_version_not_published_as_a_new_update(self):
        old = check.Identity('app', 27, frozenset({'cloud'}))
        for version in (26, 27):
            with self.subTest(version=version):
                self.assertEqual(check.check_update(old, check.Identity('app', version, old.signers)),
                                 'VERSION_NOT_HIGHER')
