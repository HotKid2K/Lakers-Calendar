import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_schedule as mod


def game(game_id='0022600011', date='2026-10-29T02:30:00Z', home=False):
    lakers = {'teamId': 1610612747, 'teamTricode': 'LAL', 'teamName': 'Lakers'}
    other = {'teamId': 1610612746, 'teamTricode': 'LAC', 'teamName': 'Clippers'}
    return {
        'gameId': game_id, 'gameDateTimeUTC': date,
        'gameLabel': 'Regular Season',
        'homeTeam': lakers if home else other,
        'awayTeam': other if home else lakers,
        'arenaName': 'Intuit Dome', 'gameStatus': 1,
    }


class CalendarTests(unittest.TestCase):
    def test_games_filter_and_timezone(self):
        g = game()
        data = {'leagueSchedule': {'seasonYear': '2026-27', 'gameDates': [{'games': [g, game('0012600001'), {'gameId': '0022600099', 'homeTeam': {}, 'awayTeam': {}}]}]}}
        season, games = mod.extract_games(data)
        self.assertEqual(season, '2026-27')
        self.assertEqual(len(games), 1)
        self.assertEqual(mod.parse_utc(g['gameDateTimeUTC']).astimezone(mod.LOCAL_TZ).strftime('%Y-%m-%d %H:%M'), '2026-10-29 10:30')

    def test_stable_uid_sequence_and_calendar(self):
        now = datetime(2026, 10, 29, tzinfo=timezone.utc)
        fixtures = [game(f'002260{i:04d}', f'2026-10-{(i % 26) + 1:02d}T02:30:00Z', home=bool(i % 2)) for i in range(1, 52)]
        ical, state = mod.build_calendar(fixtures, '2026-27', now=now)
        self.assertEqual(ical.count(b'BEGIN:VEVENT'), 51)
        self.assertIn('SUMMARY:湖人VS快船'.encode('utf-8'), ical)
        self.assertNotIn(b'DTEND:', ical)
        self.assertIn('LOCATION:直觉巨蛋'.encode('utf-8'), ical)
        self.assertIn('常规赛｜湖人客场'.encode('utf-8'), ical)
        self.assertNotIn(b'Intuit Dome', ical)
        self.assertNotIn(b'Regular Season', ical)
        self.assertNotIn('SUMMARY:🏀'.encode('utf-8'), ical)
        self.assertIn(b'\r\n', ical)
        self.assertTrue(all(len(line) <= 75 for line in ical.split(b'\r\n')))
        ical2, state2 = mod.build_calendar(fixtures, '2026-27', previous_state=state, now=now + timedelta(days=1))
        self.assertEqual(ical, ical2)
        self.assertEqual(state, state2)
        fixtures[0]['gameDateTimeUTC'] = '2026-11-01T02:30:00Z'
        ical3, state3 = mod.build_calendar(fixtures, '2026-27', previous_state=state, now=now + timedelta(days=1))
        key = fixtures[0]['gameId']
        self.assertEqual(state3['events'][key]['uid'], state['events'][key]['uid'])
        self.assertEqual(state3['events'][key]['sequence'], 1)
        self.assertNotEqual(ical, ical3)

    def test_seed_uid_reuse(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'seed.ics'
            path.write_text(
                'BEGIN:VCALENDAR\nBEGIN:VEVENT\n'
                'UID:lal-2026-27-20261028T2230-lac@user-calendar.example\n'
                'DTSTART:20261029T023000Z\n'
                'SUMMARY:湖人VS快船\n'
                'DESCRIPTION:湖人客场对阵快船。\n'
                'END:VEVENT\nEND:VCALENDAR\n', encoding='utf-8'
            )
            seeds = mod.read_seed_events(path)
            self.assertEqual(len(seeds), 1)
            start = mod.parse_utc('2026-10-29T02:30:00Z')
            selected = mod.pick_seed_uid(seeds, set(), 'LAC', False, start)
            self.assertEqual(selected, 'lal-2026-27-20261028T2230-lac@user-calendar.example')

    def test_chinese_arena_and_stage_fallback(self):
        self.assertEqual(mod.chinese_arena('Intuit Dome'), '直觉巨蛋')
        self.assertEqual(mod.chinese_arena('Mortgage Matchup Center'), '抵押贷款对决中心')
        self.assertEqual(mod.chinese_arena('Unlisted English Venue'), '比赛场馆待确认')
        self.assertEqual(mod.chinese_arena('特别比赛场馆'), '特别比赛场馆')
        self.assertEqual(mod.chinese_stage({'gameLabel': 'NBA Playoffs'}), '季后赛')
        self.assertEqual(mod.chinese_stage({'gameLabel': 'NBA Cup'}), '杯赛')
        self.assertEqual(mod.chinese_stage({'gameLabel': 'Regular Season'}), '常规赛')

    def test_bundled_ics_exists(self):
        bundled = Path(__file__).resolve().parents[1] / 'docs/lakers.ics'
        content = bundled.read_bytes()
        self.assertTrue(content.startswith(b'BEGIN:VCALENDAR'))
        self.assertGreaterEqual(content.count(b'BEGIN:VEVENT'), 50)
        self.assertNotIn(b'DTEND:', content)
        self.assertIn('SUMMARY:湖人VS'.encode('utf-8'), content)
        seeds = mod.read_seed_events(bundled)
        self.assertEqual(len(seeds), 80)
        self.assertEqual(content.count('LOCATION:'.encode('utf-8')), 80)
        self.assertIn('LOCATION:直觉巨蛋'.encode('utf-8'), content)
        self.assertIn('LOCATION:加密网竞技场'.encode('utf-8'), content)
        self.assertNotIn(b'Intuit Dome', content)
        self.assertEqual(sum(bool(s['home']) for s in seeds), 40)



if __name__ == '__main__':
    unittest.main()
