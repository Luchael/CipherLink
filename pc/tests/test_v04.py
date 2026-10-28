"""v0.4 변경: KR 서버 계정 판정, 화면 인식 불필요, 민감정보 차단."""
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
import json

from gametodo.arknights import parse_arknights, read_arknights
from gametodo.cycles import cycle_start, cycle_label, reset_buffer, KST
from gametodo.schema_probe import to_structure
from gametodo.settings import load_settings
from gametodo.account_watch import active_games, run_account_check
from gametodo.live_data import wuthering_status


class TestAccountRegionAndReset(unittest.TestCase):
    def test_asia_at_0459(self):
        now = datetime(2026,10,27,4,59,tzinfo=KST)
        self.assertEqual(cycle_label('hsr',now), '2026-10-26')
        self.assertEqual(cycle_label('zzz',now), '2026-10-26')
        self.assertFalse(reset_buffer('genshin',now))

    def test_at_0500_reset(self):
        now=datetime(2026,10,27,5,0,tzinfo=KST)
        self.assertEqual(cycle_label('wuthering',now), '2026-10-27')
        self.assertTrue(reset_buffer('wuthering',now))
        self.assertTrue(reset_buffer('hsr',now))
        self.assertFalse(reset_buffer('hsr',now+timedelta(minutes=20)))

    def test_verified_endfield_reset_and_unknown_arknights(self):
        now=datetime(2026,10,27,11,0,tzinfo=KST)
        # v0.5: 아시아 서버 05:00 KST가 확인되어 기존 추정값 대신 확정값 사용.
        self.assertEqual(cycle_start('endfield',now).hour, 5)
        self.assertFalse(reset_buffer('endfield',now))
        self.assertEqual(cycle_label('arknights',now), '2026-10-27')
        self.assertTrue(reset_buffer('hsr',now,{'hsr':'5'}))

    def test_override_reset_hour(self):
        now=datetime(2026,10,27,11,0,tzinfo=KST)
        self.assertEqual(cycle_label('endfield',now,{'endfield':11}),'2026-10-27')

    def test_arknights_status_no_claim_assumption(self):
        st=parse_arknights({'user': {'status': {'ap':70,'maxAp':140,'level':120},
                                               'mission': {'daily': {'progress': 100}}}})
        self.assertEqual(st.source,'ArkPRTS KR')
        self.assertEqual(st.details['sanity'],'70/140')
        self.assertFalse(st.safe_to_close)  # 최대 점수 정보가 없어 판정 보류
        self.assertIsNone(st.all_rewards_claimed)

    def test_arknights_invalid_payload(self):
        for payload in ({}, {'user':[]}, {'user':{'status':[]}}):
            with self.assertRaises(ValueError):parse_arknights(payload)

    def test_arknights_uses_kr_token_once(self):
        cfg={'account_data': {'arknights': {'channel_uid':'12345'}}}
        with patch('gametodo.arknights.read_secret',return_value='secret'):
            with patch('gametodo.arknights._fetch_kr',return_value={'user': {'status': {'ap':90}}}) as read:
                uid, st = read_arknights(cfg)
        self.assertEqual(uid,'12345')
        self.assertEqual(st.details['sanity'],'정보 없음')
        read.assert_called_once_with('12345','secret')

    def test_arknights_channel_uid_must_be_numeric(self):
        with self.assertRaises(ValueError):read_arknights({'account_data':{'arknights':{'channel_uid':'abc'}}})

    def test_old_colorsweeper_setting_removed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json'
            p.write_text(json.dumps({'game_settings':{'colorsweeper':{'enabled':True}}}))
            cfg=load_settings(str(p))
            self.assertNotIn('colorsweeper',cfg['game_settings'])

    def test_colorsweeper_is_not_collected(self):
        cfg={'hoyolab':{'enabled':False},'account_data':{'enabled':True,'arknights':{'enabled':True}}}
        self.assertEqual([x[0] for x in active_games(cfg)],[])  # v0.9.9: 게임 접속 종료 위험 방지

    def test_arknights_no_auto_completion(self):
        from gametodo.live_data import Status,Gauge
        cfg={'account_data':{'enabled':True,'arknights':{'enabled':True}}}
        class Todo:
            def all_tasks(self): raise AssertionError('완료 불가능한 자료로 Todoist 조회 금지')
        with patch('gametodo.account_watch.read_arknights',return_value=('55',parse_arknights({'user':{'status':{'ap':100,'maxAp':100}}}))):
            data=run_account_check(cfg,todoist=Todo(), store=object(), now=datetime(2026,10,27,12,tzinfo=KST))
        # 0.9.9: 개인 조회가 게임 접속을 해제할 수 있으므로 계정 조회 자체를 차단한다.
        self.assertEqual(data, [])

    def test_wuthering_score_completes_regardless_of_community_checkin(self):
        result=wuthering_status({'code':200,'data':{'roleId':'123','serverId':'asia',
                      'livenessData':{'cur':100,'total':100},'hasSignIn':True}},'asia')
        self.assertIs(result.details['community_checkin_claimed'],True)
        self.assertTrue(result.safe_to_close)

    def test_schema_report_no_values(self):
        raw={'name':'my real name','userId':123456,'account_token':'secret','daily':{'score':500,
                'rewards':[{'claimed':True,'itemName':'secret item'}]}}
        out=to_structure(raw)
        serialized=json.dumps(out)
        self.assertNotIn('my real name',serialized)
        self.assertNotIn('123456',serialized)
        self.assertNotIn('secret',serialized)
        self.assertIn('claimed',serialized)
        self.assertIn('bool',serialized)

    def test_empty_structure(self):
        self.assertEqual(to_structure([])['item_count'],0)
        self.assertEqual(to_structure({'points':42}),{'points':'int'})

if __name__ == '__main__': unittest.main()
