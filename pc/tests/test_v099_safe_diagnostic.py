import asyncio
import json
import unittest
from unittest.mock import AsyncMock, Mock

from gametodo.safe_diagnostic import sanitize, collect_hoyo
from gametodo.account_watch import active_games


class SafeDiagnosticTests(unittest.TestCase):
    def test_never_leak_identifiers_secrets_or_urls(self):
        payload = {
            'uid': '81012233', 'nickname':'secret_name', 'jwt_token':'abcXYZ',
            'avatar_icon':'https://server/test?access_token=abc',
            'total_star':9, 'total_score':56000, 'start_time':'2026-10-19 04:00',
            'list':[{'score':20000,'rank':'S','role_id':9876,'team':[{'name':'PII'}],
                     'info':'signed?some_token'},
                    {'score':16000,'cookie':'evil'}]
        }
        safe=sanitize(payload)
        txt=json.dumps(safe,ensure_ascii=False)
        for secret in ('81012233','secret_name','abcXYZ','server/test','9876','signed?some_token','PII'):
            self.assertNotIn(secret,txt)
        self.assertEqual(safe['total_star'],9)
        self.assertEqual(safe['list']['_array_length'],2)
        self.assertEqual(safe['list']['_first_samples'][0]['score'],20000)
        self.assertEqual(safe['list']['_first_samples'][0]['rank'],'S')

    def test_prior_cycle_probe_is_diagnostic_only(self):
        obj=type("Client", (), {})()
        obj.get_deadly_assault=AsyncMock(return_value={
            'list':[{'total_star':3}], 'total_star':9,
            'user':{'email':'redact@here'}})
        result=asyncio.run(collect_hoyo(obj,'zzz','1312345',1))
        self.assertEqual(len(result),3)  # Shiyu method unavailable + Deadly current/previous
        self.assertEqual(result[1]['requested_period'],'default')
        self.assertEqual(result[2]['requested_period'],'previous_probe_unverified')
        self.assertEqual(result[1]['schema']['total_star'],9)
        self.assertNotIn('redact@here',str(result))

    def test_arknights_never_auto_logs_in(self):
        cfg={'hoyolab':{'enabled':False},'account_data':{'enabled':True,'arknights':{'enabled':True}}}
        self.assertNotIn('arknights',[g for g,_ in active_games(cfg)])
