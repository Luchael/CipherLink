"""v0.8.3: 다중 캐릭터 선택과 서버명/ID 판정 회귀 테스트."""
import unittest
from gametodo.account_setup import list_asia_endfield_roles, select_asia_endfield_role

class EndfieldRolesTests(unittest.TestCase):
    def example(self, records):
        return {"data":{"list":[{"appCode":"endfield", "bindingList":[
            {"defaultRole":records[0],"roles":records}
        ]}]}}

    def test_server_id_2_is_asia(self):
        binding=self.example([{"roleId":"123456", "serverId":"2", "serverName":"글로벌", "nickname":"한글닉"}])
        self.assertEqual(select_asia_endfield_role(binding),("123456","2"))

    def test_non_asia_not_selected(self):
        binding=self.example([{"roleId":"123456", "serverId":"3", "serverName":"America", "nickname":"A"}])
        self.assertEqual(list_asia_endfield_roles(binding),[])

    def test_mixed_accounts(self):
        binding=self.example([{"roleId":"123456", "serverId":"2", "serverName":"Asia", "nickname":"A"},
                              {"roleId":"999999", "serverId":"2", "serverName":"Asia", "nickname":"B"},
                              {"roleId":"777777", "serverId":"3", "serverName":"America", "nickname":"C"}])
        roles=list_asia_endfield_roles(binding)
        self.assertEqual({x['nickname'] for x in roles},{"A","B"})
        self.assertIsNone(select_asia_endfield_role(binding))

    def test_default_role_duplicate_is_deduplicated(self):
        binding=self.example([{"roleId":"123456", "serverId":"2", "serverName":"Asia", "nickname":"A"}])
        self.assertEqual(len(list_asia_endfield_roles(binding)),1)

    def test_unrelated_game_is_ignored(self):
        binding={"data":{"list":[{"appCode":"other","bindingList":[{"roles":[
            {"roleId":"123456", "serverId":"2", "serverName":"Asia"}]}]}]}}
        self.assertEqual(list_asia_endfield_roles(binding),[])

if __name__=='__main__': unittest.main()
