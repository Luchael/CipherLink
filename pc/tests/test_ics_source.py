import unittest
from gametodo.ics_source import parse_ics, validate_ics_url, fetch_ics

ICAL='''BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:evt-1
DTSTART;TZID=Asia/Seoul:20261027T120000
DTEND;TZID=Asia/Seoul:20261102T235900
SUMMARY:대한민국 서버 이벤트
DESCRIPTION:게임 내 모든 보상 수령시 완료
END:VEVENT
BEGIN:VEVENT
UID:evt-2
DTSTART;VALUE=DATE:20261027
DTEND;VALUE=DATE:20261031
SUMMARY:한국 서버 출석 이벤트
END:VEVENT
BEGIN:VEVENT
UID:evt-3
STATUS:CANCELLED
DTSTART;VALUE=DATE:20261101
DTEND;VALUE=DATE:20261105
SUMMARY:취소된 이벤트
END:VEVENT
BEGIN:VEVENT
UID:evt-4
DTSTART;TZID=America/New_York:20261027T120000
DTEND;TZID=America/New_York:20261102T235900
SUMMARY:미국 서버 이벤트
END:VEVENT
END:VCALENDAR'''

class TestIcs(unittest.TestCase):
    def test_kst_only(self):
        result=parse_ics(ICAL,'reverse1999','https://calendar.example.com/r1999.ics','KR')
        self.assertEqual(len(result),2)
        self.assertEqual(result[0].due_date,'2026-11-02')
        # RFC5545 all-day end date is exclusive
        self.assertEqual(result[1].due_date,'2026-10-30')
        self.assertEqual(result[0].server,'KR')

    def test_unverified_server_blocked(self):
        with self.assertRaises(ValueError):parse_ics(ICAL,'reverse1999','https://example.org/a','Global')

    def test_private_link_blocked(self):
        for url in ['http://example.org/a','https://localhost/a','https://127.0.0.1/a',
                    'https://192.168.1.22/a','https://user:pass@example.com/a','file:///a.ics']:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):validate_ics_url(url)

    def test_no_list_duplication(self):
        class FakeHTTP:
            def request(self,url,cache):
                self.url=url
                self.cache=cache
                return ICAL
        http=FakeHTTP()
        events=fetch_ics(http,'stella',{'ics_url':'https://calendar.example.com/kr.ics','verified_server':'KR'})
        self.assertEqual(len(events),2)
        self.assertTrue(http.cache)

    def test_external_events_excluded(self):
        ics='''BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;VALUE=DATE:20261027
DTEND;VALUE=DATE:20261030
SUMMARY:오프라인 팝업스토어 이벤트
END:VEVENT
END:VCALENDAR'''
        self.assertEqual(parse_ics(ics,'stella','https://a.com/ical','KR'),[])

if __name__=='__main__':unittest.main()

class TestPrivateCalendar(unittest.TestCase):
    def test_calendar_subscription_secret_not_in_todo(self):
        class FakeHTTP:
            def request(self,url,cache):return ICAL
        events=fetch_ics(FakeHTTP(),'stella',{'ics_url':'https://calendar.google.com/calendar/ical/SecretTokenValue/basic.ics',
                                              'verified_server':'KR'})
        self.assertNotIn('SecretTokenValue',events[0].url)
        self.assertEqual(events[0].url,'https://calendar.google.com/')
