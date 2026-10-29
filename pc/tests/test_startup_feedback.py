import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from gametodo import startup

class Key:
    def __init__(self,values):self.values=values
    def __enter__(self):return self
    def __exit__(self,*a):pass
class Registry:
    HKEY_CURRENT_USER=1;REG_SZ=1;KEY_SET_VALUE=2;KEY_QUERY_VALUE=1
    def __init__(self):self.paths={}
    def OpenKey(self,root,path,*a):
        if path not in self.paths:raise FileNotFoundError
        return Key(self.paths[path])
    def CreateKeyEx(self,root,path,reserved,access):return Key(self.paths.setdefault(path,{}))
    def QueryValueEx(self,key,name):
        if name not in key.values:raise FileNotFoundError
        return key.values[name],1
    def SetValueEx(self,key,name,reserved,kind,value):key.values[name]=value
    def DeleteValue(self,key,name):del key.values[name]

class StartupTests(unittest.TestCase):
    command='"C:\\Program Files\\CipherLink.exe"'
    def test_register_readback_and_remove_only_owned_entries(self):
        r=Registry();self.assertFalse(startup.state(r,self.command).registered)
        r.paths[startup.RUN]={'Other':'"C:\\Other.exe"'}
        self.assertTrue(startup.enable(r,self.command).current)
        self.assertTrue(startup.state(r,self.command).registered)
        startup.disable(r)
        self.assertEqual(r.paths[startup.RUN],{'Other':'"C:\\Other.exe"'})
    def test_windows_disabled_and_quoted_equivalent_detected(self):
        r=Registry();r.paths[startup.RUN]={'CipherLink':'"C:\\Apps\\CipherLink.exe"'}
        r.paths[startup.APPROVED]={'CipherLink':b'\x03\x00\x00\x00'+b'\0'*8}
        state=startup.state(r,'C:\\Apps\\CipherLink.exe')
        self.assertTrue(state.current and state.blocked)
        self.assertIn('사용 안 함',state.message)
    def test_legacy_is_migrated_and_foreign_collision_preserved(self):
        r=Registry();r.paths[startup.RUN]={'GameTodo':'"C:\\Apps\\QuestLink.exe"'}
        startup.enable(r,self.command)
        self.assertNotIn('GameTodo',r.paths[startup.RUN])
        r.paths[startup.RUN]['CipherLink']='"C:\\Other.exe" --name CipherLink.exe'
        with self.assertRaises(OSError):startup.enable(r,self.command)
        startup.disable(r)
        self.assertIn('CipherLink',r.paths[startup.RUN])
    def test_versioned_download_name_can_be_updated_and_removed(self):
        r=Registry()
        old='"C:\\Apps\\CipherLink-0.11.5.exe"'
        new='"C:\\Apps\\CipherLink-0.11.6.exe"'
        r.paths[startup.RUN]={'CipherLink':old}
        self.assertFalse(startup.state(r,new).current)
        self.assertTrue(startup.enable(r,new).current)
        self.assertFalse(startup.disable(r).registered)
    def test_access_failure_is_not_reported_as_unregistered(self):
        r=Registry();r.OpenKey=Mock(side_effect=PermissionError())
        self.assertIsNone(startup.state(r).registered)
    def test_log_feedback_also_updates_current_page(self):
        from gametodo.gui import Desktop
        view=SimpleNamespace(notice=Mock(),status=Mock(),notice_label=Mock(),logs=Mock())
        view._feedback=lambda message:Desktop._feedback(view,message)
        Desktop._print(view,'시작 프로그램 · 등록됨\n상세 기록')
        view.notice.set.assert_called_with('시작 프로그램 · 등록됨')
        view.status.set.assert_called_with('시작 프로그램 · 등록됨')
        view.logs.insert.assert_called_once()
