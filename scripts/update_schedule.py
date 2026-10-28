#!/usr/bin/env python3
"""Publish a stable-UID Lakers Chinese iCalendar from NBA's public schedule JSON.

No third-party dependencies. Defaults to the 2026-27 season and rolls forward
when an upcoming season has a reasonably complete published schedule.
"""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parents[1]
DOCS = BASE_DIR / 'docs'
ICS_PATH = DOCS / 'lakers.ics'
STATE_PATH = DOCS / 'metadata.json'
LOCAL_TZ = ZoneInfo('Asia/Shanghai')
LAKERS_ID = '1610612747'
MIN_SEASON = 2026
MIN_GAMES = 50
FEEDS = (
    'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json',
    'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json',
)
TEAM_NAMES = {
    'ATL': '老鹰', 'BKN': '篮网', 'BOS': '凯尔特人', 'CHA': '黄蜂',
    'CHI': '公牛', 'CLE': '骑士', 'DAL': '独行侠', 'DEN': '掘金',
    'DET': '活塞', 'GSW': '勇士', 'HOU': '火箭', 'IND': '步行者',
    'LAC': '快船', 'LAL': '湖人', 'MEM': '灰熊', 'MIA': '热火',
    'MIL': '雄鹿', 'MIN': '森林狼', 'NOP': '鹈鹕', 'NYK': '尼克斯',
    'OKC': '雷霆', 'ORL': '魔术', 'PHI': '76人', 'PHX': '太阳',
    'POR': '开拓者', 'SAC': '国王', 'SAS': '马刺', 'TOR': '猛龙',
    'UTA': '爵士', 'WAS': '奇才',
}


# 球馆中文常用译名。保留历史名称，兼容 NBA 赛程接口中的旧冠名。
# 对于无法确定的英文场馆名称，使用中文提示，不猜测具体球馆。
ARENA_ZH = {
    'State Farm Arena': '州立农业保险球馆',
    'Barclays Center': '巴克莱中心',
    'TD Garden': '道明花园球馆',
    'Spectrum Center': '光谱中心',
    'United Center': '联合中心',
    'Rocket Arena': '火箭球馆',
    'Rocket Mortgage FieldHouse': '火箭抵押贷款球馆',
    'American Airlines Center': '美国航空中心',
    'Ball Arena': '波尔球馆',
    'Little Caesars Arena': '小凯撒球馆',
    'Chase Center': '大通中心',
    'Toyota Center': '丰田中心',
    'Gainbridge Fieldhouse': '盖恩布里奇球馆',
    'Intuit Dome': '直觉巨蛋',
    'Crypto.com Arena': '加密网竞技场',
    'FedExForum': '联邦快递球馆',
    'Kaseya Center': '卡西亚中心',
    'AmericanAirlines Arena': '美国航空球馆',
    'Fiserv Forum': '费哲球馆',
    'Target Center': '塔吉特中心',
    'Smoothie King Center': '冰沙王中心',
    'Madison Square Garden': '麦迪逊广场花园',
    'Paycom Center': '派康中心',
    'Kia Center': '起亚中心',
    'Xfinity Mobile Arena': '无限移动球馆',
    'Wells Fargo Center': '富国银行中心',
    'Mortgage Matchup Center': '抵押贷款对决中心',
    'Footprint Center': '足迹中心',
    'Moda Center': '摩达中心',
    'Golden 1 Center': '黄金一号中心',
    'Frost Bank Center': '弗罗斯特银行中心',
    'AT&T Center': '美国电话电报中心',
    'Scotiabank Arena': '丰业银行体育馆',
    'Delta Center': '达美中心',
    'Capital One Arena': '第一资本球馆',
    'Golden State Warriors': '勇士主场球馆',
}

# 缺失场馆名称时，按球队提供常规主场信息（仅供初始赛程补充）。
HOME_ARENA_BY_TEAM = {
    'ATL': '州立农业保险球馆', 'BKN': '巴克莱中心', 'BOS': '道明花园球馆',
    'CHA': '光谱中心', 'CHI': '联合中心', 'CLE': '火箭球馆',
    'DAL': '美国航空中心', 'DEN': '波尔球馆', 'DET': '小凯撒球馆',
    'GSW': '大通中心', 'HOU': '丰田中心', 'IND': '盖恩布里奇球馆',
    'LAC': '直觉巨蛋', 'LAL': '加密网竞技场', 'MEM': '联邦快递球馆',
    'MIA': '卡西亚中心', 'MIL': '费哲球馆', 'MIN': '塔吉特中心',
    'NOP': '冰沙王中心', 'NYK': '麦迪逊广场花园', 'OKC': '派康中心',
    'ORL': '起亚中心', 'PHI': '无限移动球馆', 'PHX': '抵押贷款对决中心',
    'POR': '摩达中心', 'SAC': '黄金一号中心', 'SAS': '弗罗斯特银行中心',
    'TOR': '丰业银行体育馆', 'UTA': '达美中心', 'WAS': '第一资本球馆',
}


def chinese_arena(name):
    """Translate known arena names; never expose an untranslated English venue."""
    raw = str(name or '').strip()
    if not raw or raw.upper() in {'TBD', 'TBA', 'N/A'}:
        return ''
    if not any('A' <= c <= 'Z' or 'a' <= c <= 'z' for c in raw):
        return raw
    normalized = ' '.join(raw.casefold().split())
    for english, chinese in sorted(ARENA_ZH.items(), key=lambda pair: -len(pair[0])):
        if english.casefold() in normalized:
            return chinese
    return '比赛场馆待确认'


def chinese_stage(game):
    """Convert league-provided English game labels into short Chinese labels."""
    label = str(game.get('gameLabel') or '').lower()
    if any(word in label for word in ('finals', 'championship')):
        return '总决赛'
    if any(word in label for word in ('play-in', 'play in')):
        return '附加赛'
    if any(word in label for word in ('playoffs', 'playoff')):
        return '季后赛'
    if any(word in label for word in ('cup', 'tournament')):
        return '杯赛'
    return '常规赛'




def is_lakers(team):
    return str(team.get('teamId', '')) == LAKERS_ID or team.get('teamTricode') == 'LAL'


def parse_utc(value):
    if not value or str(value).upper() in ('TBD', 'TBA'):
        return None
    try:
        t = datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
        return t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def season_start_year(value):
    if value is None:
        return -1
    try:
        return int(str(value)[:4])
    except ValueError:
        return -1


def is_valid_game(game):
    if not (is_lakers(game.get('homeTeam') or {}) or is_lakers(game.get('awayTeam') or {})):
        return False
    label = str(game.get('gameLabel') or '').lower()
    if 'preseason' in label or str(game.get('gameId', '')).startswith('001'):
        return False
    return bool(parse_utc(game.get('gameDateTimeUTC')))


def extract_games(payload):
    league = payload.get('leagueSchedule') or {}
    season = str(league.get('seasonYear') or '')
    games = [g for item in (league.get('gameDates') or []) for g in item.get('games', []) if is_valid_game(g)]
    unique = {str(g.get('gameId')): g for g in games if g.get('gameId')}
    return season, list(unique.values())


def get_candidates():
    candidates = []
    for url in FEEDS:
        request = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; LakersChineseCalendar/1.0)',
            'Accept': 'application/json',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com',
        })
        try:
            with urlopen(request, timeout=35) as response:
                obj = json.load(response)
            season, games = extract_games(obj)
            year = season_start_year(season)
            if year >= MIN_SEASON and len(games) >= MIN_GAMES:
                candidates.append((year, len(games), season, games, url))
                print(f'数据源可用：{url}，{season}，湖人{len(games)}场')
            else:
                print(f'忽略赛季不匹配或不足{MIN_GAMES}场的数据：{url}，{season}，{len(games)}场')
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            print(f'下载数据失败：{url}：{exc}')
    if not candidates:
        raise RuntimeError('没有取得有效的 NBA 赛程，保留上一次已发布的文件。')
    _, _, season, games, source = max(candidates, key=lambda x: (x[0], x[1]))
    return season, games, source


def stamp(date):
    return date.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def escape_ics(s):
    return str(s).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def fold(line):
    """Fold physical lines to max 75 octets (RFC 5545), preserving UTF-8."""
    out = []
    curr = ''
    for char in line:
        if len((curr + char).encode('utf-8')) > 75:
            out.append(curr)
            curr = ' ' + char
        else:
            curr += char
    out.append(curr)
    return out


def read_seed_events(path):
    """Preserve old event UIDs when transitioning the bundled 80-game seed to NBA IDs."""
    if not path.exists():
        return []
    result, event, lines = [], None, []
    in_alarm = False
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if line.startswith(' ') or line.startswith('\t'):
            if lines:
                lines[-1] += line[1:]
        else:
            lines.append(line)
    for line in lines:
        if line == 'BEGIN:VEVENT':
            event = {}
            in_alarm = False
        elif line == 'BEGIN:VALARM':
            in_alarm = True
        elif line == 'END:VALARM':
            in_alarm = False
        elif line == 'END:VEVENT' and event is not None:
            uid = event.get('UID', '')
            if 'lal-2026-27-' in uid and '@user-calendar.example' in uid:
                bits = uid.split('@')[0].split('-')
                opp = bits[-1].upper()
                home = '主场' in (event.get('SUMMARY', '') + event.get('DESCRIPTION', ''))
                start = parse_utc(datetime.strptime(event['DTSTART'], '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc).isoformat())
                result.append({'uid': uid, 'opp': opp, 'home': home, 'start': start})
            event = None
        elif event is not None and not in_alarm and ':' in line:
            key, value = line.split(':', 1)
            event[key.split(';')[0]] = value
    return result


def pick_seed_uid(seeds, used, opponent, home, start):
    compatible = [s for s in seeds if s['uid'] not in used and s['opp'] == opponent and s['home'] == home and s['start']]
    if not compatible:
        return None
    choice = min(compatible, key=lambda x: abs((x['start'] - start).total_seconds()))
    if abs((choice['start'] - start).total_seconds()) <= 72 * 3600:
        used.add(choice['uid'])
        return choice['uid']
    return None


def build_calendar(games, season, previous_state=None, seeds=None, now=None):
    previous_state = previous_state or {}
    seeds = seeds or []
    now = now or datetime.now(timezone.utc)
    current_stamp = stamp(now)
    old_events = previous_state.get('events', {})
    new_events = {}
    events = []
    used_seeds = set()
    for game in sorted(games, key=lambda g: (g.get('gameDateTimeUTC') or '', str(g.get('gameId')))):
        gid = str(game['gameId'])
        start = parse_utc(game.get('gameDateTimeUTC'))
        if start is None:
            continue
        home = is_lakers(game.get('homeTeam') or {})
        opponent = game.get('awayTeam') if home else game.get('homeTeam')
        opponent = opponent or {}
        code = str(opponent.get('teamTricode') or '').upper()
        opponent_name = TEAM_NAMES.get(code, '待定球队')
        side = '主场' if home else '客场'
        summary = f'湖人VS{opponent_name}'
        local = start.astimezone(LOCAL_TZ)
        phase = chinese_stage(game)
        desc = (f'{phase}｜湖人{side}\n'
                f'北京时间：{local:%m月%d日 %H:%M}\n'
                '具体赛程以联盟公告为准。')
        venue = chinese_arena(game.get('arenaName'))
        link = f'https://www.nba.com/game/{gid}'
        status_text = str(game.get('gameStatusText') or '').lower()
        status = 'CANCELLED' if ('cancel' in status_text or 'postpon' in status_text) else 'CONFIRMED'
        fingerprint_data = {'start': stamp(start), 'summary': summary, 'desc': desc,
                            'venue': venue, 'status': status, 'link': link}
        fingerprint = hashlib.sha256(json.dumps(fingerprint_data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        old = old_events.get(gid)
        if old:
            uid = old['uid']
            modified = old.get('updated', current_stamp) if old.get('fingerprint') == fingerprint else current_stamp
            sequence = int(old.get('sequence', 0)) + (old.get('fingerprint') != fingerprint)
        else:
            uid = pick_seed_uid(seeds, used_seeds, code, home, start) or f'nba-lal-{gid}@lakers-cn-calendar.example'
            sequence = 0
            modified = current_stamp
        new_events[gid] = {'uid': uid, 'fingerprint': fingerprint, 'sequence': sequence, 'updated': modified}
        props = [
            'BEGIN:VEVENT', f'UID:{uid}', f'DTSTAMP:{modified}', f'LAST-MODIFIED:{modified}',
            f'SEQUENCE:{sequence}', f'DTSTART:{stamp(start)}',
            # No DTEND: an instantaneous event shows the tipoff time alone in most calendars.
            f'SUMMARY:{escape_ics(summary)}', f'DESCRIPTION:{escape_ics(desc)}',
            f'URL:{link}', 'CATEGORIES:篮球,湖人赛程', f'STATUS:{status}',
        ]
        if venue:
            props.append(f'LOCATION:{escape_ics(venue)}')
        props += ['BEGIN:VALARM', 'ACTION:DISPLAY', f'DESCRIPTION:{escape_ics(summary)}',
                  'TRIGGER:-PT30M', 'END:VALARM', 'END:VEVENT']
        events.extend(props)
    if len(new_events) < MIN_GAMES:
        raise RuntimeError(f'有效赛事仅{len(new_events)}场，已拒绝覆盖原有日历。')
    lines = [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//湖人中文赛程//自动更新//ZH-CN',
        'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
        'X-WR-CALNAME:湖人赛程',
        'X-WR-TIMEZONE:Asia/Shanghai',
        'X-WR-CALDESC:中文赛程；北京时间；定期同步。',
        'REFRESH-INTERVAL;VALUE=DURATION:PT6H', 'X-PUBLISHED-TTL:PT6H',
        *events, 'END:VCALENDAR',
    ]
    ical = ('\r\n'.join(row for line in lines for row in fold(line)) + '\r\n').encode('utf-8')
    return ical, {'schema': 1, 'season': season, 'events': new_events}


def update():
    DOCS.mkdir(parents=True, exist_ok=True)
    previous = json.loads(STATE_PATH.read_text(encoding='utf-8')) if STATE_PATH.exists() else {}
    seeds = read_seed_events(ICS_PATH) if not previous else []
    season, games, source = get_candidates()
    ical, state = build_calendar(games, season, previous, seeds)
    current_ical = ICS_PATH.read_bytes() if ICS_PATH.exists() else b''
    state_text = json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    prior_state_text = STATE_PATH.read_text(encoding='utf-8') if STATE_PATH.exists() else ''
    if ical != current_ical:
        ICS_PATH.write_bytes(ical)
    if state_text != prior_state_text:
        STATE_PATH.write_text(state_text, encoding='utf-8')
    print(f'{season}：{len(state["events"])}场；订阅文件：{ICS_PATH}；来源：{source}')
    print('内容有变化' if ical != current_ical else '内容无变化')


if __name__ == '__main__':
    try:
        update()
    except Exception as exc:
        # Keep publishing the bundled/previous successful snapshot if the NBA CDN fails.
        if ICS_PATH.exists() and ICS_PATH.stat().st_size > 5000:
            print(f'警告：{exc}；本轮保留并发布上一次成功的赛程。')
        else:
            raise
