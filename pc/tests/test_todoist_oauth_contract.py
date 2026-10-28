import unittest
from unittest.mock import patch
from gametodo import oauth_login

class OAuthContractTests(unittest.TestCase):
    def test_official_auth_host_is_independent_of_data_api(self):
        self.assertEqual(oauth_login.REGISTER_URL, 'https://todoist.com/oauth/register')
        self.assertEqual(oauth_login.AUTHORIZE_URL, 'https://todoist.com/oauth/authorize')
        self.assertEqual(oauth_login.TOKEN_URL, 'https://todoist.com/oauth/access_token')

    def test_missing_expiry_is_not_invented_as_one_hour(self):
        self.assertEqual(oauth_login.token_expiry({}, now=100), 0)
        self.assertEqual(oauth_login.token_expiry({'expires_in':3600}, now=100), 3700)
        with patch.object(oauth_login, '_stored', return_value={'access_token':'synthetic', 'expires_at':0}), \
             patch.object(oauth_login, '_post') as post:
            self.assertEqual(oauth_login.get_oauth_token(), 'synthetic')
            post.assert_not_called()
