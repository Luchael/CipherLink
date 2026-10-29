import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('downloads',ROOT/'tools/update_download_links.py')
downloads=importlib.util.module_from_spec(spec);spec.loader.exec_module(downloads)

class ActualDownloadTests(unittest.TestCase):
    def metadata(self):
        base='https://github.com/Luchael/CipherLink/releases/'
        return {'isDraft':True,'url':base+'tag/untagged-fixture','assets':[
            {'name':name,'size':42,'url':base+'download/untagged-fixture/'+name}
            for name in ('CipherLink-Windows-Setup.exe','CipherLink-Windows.exe')]}
    def test_existing_files_only_with_login_notice_and_installer_first(self):
        text=downloads.render_release(self.metadata(),'0.11.7')
        self.assertIn('로그인',text)
        self.assertLess(text.index('Windows-Setup.exe'),text.index('/CipherLink-Windows.exe'))
        self.assertNotIn('[Android',text)
        self.assertIn('아직 GitHub에 업로드되지',text)
    def test_old_release_completion_cannot_replace_newer_downloads(self):
        old=downloads.render_release(self.metadata(),'0.11.7')
        readme='intro\n'+old+'\nother content'
        self.assertEqual(downloads.update_readme(readme,downloads.render_release(self.metadata(),'0.11.6'),'0.11.6'),readme)
        changed=downloads.update_readme(readme,downloads.render_release(self.metadata(),'0.11.8'),'0.11.8')
        self.assertTrue(changed.startswith('intro\n') and changed.endswith('\nother content'))
    def test_unexpected_signed_external_or_missing_files_are_rejected(self):
        for url in ('https://example.com/file.exe','https://github.com/other/repo/releases/download/v1/file.exe','https://github.com/Luchael/CipherLink/releases/download/v1/file.exe?token=fixture'):
            metadata=self.metadata();metadata['assets'][0]['url']=url
            with self.assertRaises(ValueError):downloads.render_release(metadata,'0.11.7')
        metadata=self.metadata();metadata['assets']=[]
        with self.assertRaises(ValueError):downloads.render_release(metadata,'0.11.7')
