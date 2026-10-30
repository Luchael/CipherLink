import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('release_metadata',ROOT/'tools/release_metadata.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

class ReleaseMetadataTests(unittest.TestCase):
    def test_pc_android_versions_match_and_signer_is_fixed(self):
        version,code=release.project_version(ROOT)
        self.assertRegex(version,r'^\d+\.\d+\.\d+$')
        self.assertGreater(code,30)
        config=json.loads((ROOT/'release-config.json').read_text(encoding='utf-8'))
        self.assertEqual(config['android_package'],'com.gametodo.nativeapp.preview')
        self.assertEqual(config['android_signer_sha256'],'2f5505f8e8b1b8b00ea9ed27d6e2ce733ad8b8f46aa19797eb8a5a68de5897cb')

    def test_manifest_requires_both_and_detects_file_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            apk=folder/'CipherLink-Android.apk';apk.write_bytes(b'fixture-apk')
            with self.assertRaises(ValueError):release.manifest(folder,'0.11.3',31)
            exe=folder/'CipherLink-Windows.exe';exe.write_bytes(b'fixture-exe')
            result=release.manifest(folder,'0.11.3',31)
            self.assertEqual(result['android']['sha256'],hashlib.sha256(apk.read_bytes()).hexdigest())
            exe.write_bytes(b'changed-exe')
            self.assertNotEqual(result['windows']['sha256'],release.manifest(folder,'0.11.3',31)['windows']['sha256'])
            exe.write_bytes(b'')
            with self.assertRaises(ValueError):release.manifest(folder,'0.11.3',31)

    def test_windows_only_release_does_not_advertise_android(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            (folder/'CipherLink-Windows.exe').write_bytes(b'exe')
            with self.assertRaises(ValueError):release.manifest(folder,'0.11.8',36,windows_only=True)
            (folder/'CipherLink-Windows-Setup.exe').write_bytes(b'installer')
            result=release.manifest(folder,'0.11.8',36,windows_only=True)
            self.assertNotIn('android',result)
            self.assertIsNone(result['android_version_code'])
            self.assertIn('windows_installer',result)

    def test_stale_windows_version_resource_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'pc/gametodo').mkdir(parents=True);(root/'android/app').mkdir(parents=True);(root/'pc/assets').mkdir()
            (root/'pc/gametodo/__init__.py').write_text('__version__ = "0.11.7"')
            (root/'android/app/build.gradle.kts').write_text('versionName = "0.11.7"\nversionCode = 35')
            (root/'pc/assets/version_info.txt').write_text('filevers=(0,11,5,0)')
            with self.assertRaises(ValueError):release.project_version(root)

    def test_mismatched_versions_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'pc/gametodo').mkdir(parents=True);(root/'android/app').mkdir(parents=True)
            (root/'pc/gametodo/__init__.py').write_text('__version__ = "0.11.3"',encoding='utf-8')
            (root/'android/app/build.gradle.kts').write_text('versionName = "0.11.2"\nversionCode = 30',encoding='utf-8')
            with self.assertRaises(ValueError):release.project_version(root)

class PrivatePublicationTests(unittest.TestCase):
    def test_public_repository_never_publishes(self):
        import sys
        from unittest.mock import patch
        with patch.object(sys,'path',[str(ROOT/'tools')]+sys.path):
            import publish_release
        version,_=release.project_version(ROOT)
        with patch.object(sys,'argv',['publish_release.py',version,'--finalize']), \
             patch.object(publish_release,'command',return_value='false') as remote:
            with self.assertRaisesRegex(SystemExit,'still public'):publish_release.main()
        self.assertEqual(remote.call_count,1)
        self.assertNotIn('edit',remote.call_args.args[0])

    def test_missing_binary_stays_draft(self):
        import sys
        from unittest.mock import patch
        with patch.object(sys,'path',[str(ROOT/'tools')]+sys.path):
            import publish_release
        version,_=release.project_version(ROOT)
        with patch.object(sys,'argv',['publish_release.py',version,'--finalize']), \
             patch.object(publish_release,'command',side_effect=['true',json.dumps({'isDraft':True,'assets':[{'name':'CipherLink-Android.apk'}]})]) as remote:
            with self.assertRaisesRegex(SystemExit,'Both binaries'):publish_release.main()
        self.assertEqual(remote.call_count,2)

    def test_complete_private_release_can_publish(self):
        import sys
        from unittest.mock import patch
        with patch.object(sys,'path',[str(ROOT/'tools')]+sys.path):
            import publish_release
        version,_=release.project_version(ROOT)
        metadata={'isDraft':True,'assets':[{'name':name} for name in
                  ['CipherLink-Windows-Setup.exe','CipherLink-Windows.exe','CipherLink-Android.apk','SHA256SUMS.txt','update.json']]}
        with patch.object(sys,'argv',['publish_release.py',version,'--finalize']), \
             patch.object(publish_release,'command',side_effect=['true',json.dumps(metadata),'']) as remote:
            publish_release.main()
        self.assertIn('edit',remote.call_args.args[0])
        self.assertIn('--draft=false',remote.call_args.args[0])
