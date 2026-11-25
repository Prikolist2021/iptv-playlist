#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IPTV-конвейер (автоматизированный). Скачивание + фильтрация + публикация."""
import os, re, sys, subprocess
from concurrent.futures import ThreadPoolExecutor

DIR = os.environ.get('IPTV_DIR', os.path.expanduser('~/iptv'))
DROP_WINK = True; DROP_TIMESHIFT = True; DROP_BIGCITY = False
KEEP_PER_NAME = 1; MODE = 'theme'; SEPARATE_INT = True; SORT = True
USE_FORCE_DROP = True; AUDIO_THREADS = 16

# ================= скачивание плейлиста =================
def download_playlist(url='https://raw.githubusercontent.com/IPTVRU2026/IPTVMIR/main/IPTV_MEGA_PLAYLIST.m3u'):
    """Скачивает плейлист из интернета"""
    import urllib.request
    print(f'Скачивание: {url}')
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = urllib.request.urlopen(req, timeout=30).read()
        with open(p('IPTV_MEGA_PLAYLIST.m3u'), 'wb') as f:
            f.write(data)
        print(f'Скачано: {len(data)} байт')
        return True
    except Exception as e:
        print(f'Ошибка скачивания: {e}')
        return False

# ================= парсер/IO =================
RE_GROUP = re.compile(r'group-title="([^"]*)"')

def parse_extinf(line):
    tail = line.rsplit('"', 1)[-1]
    name = tail.split(',', 1)[1].strip() if ',' in tail else (line.split(',', 1)[1].strip() if ',' in line else '')
    m = RE_GROUP.search(line)
    return name, (m.group(1).strip() if m else '')

def load(path):
    items, ext, extra = [], None, []
    with open(path, encoding='utf-8', errors='replace') as f:
        for raw in f:
            s = raw.strip()
            if s.startswith('#EXTINF'):
                ext, extra = s, []
            elif s.startswith('#') or not s:
                if ext is not None and s: extra.append(s)
            else:
                if ext is not None:
                    n, g = parse_extinf(ext)
                    items.append({'ext': ext, 'extra': extra, 'url': s, 'name': n, 'group': g})
                ext, extra = None, []
    return items

def save(path, items, group_of=None):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for it in items:
            ext = it['ext']
            if group_of is not None:
                g = group_of(it)
                if 'group-title=' in ext:
                    ext = RE_GROUP.sub(lambda m: 'group-title="%s"' % g, ext, count=1)
                else:
                    ext = re.sub(r'(#EXTINF:\s*-?\d+)', lambda m: m.group(1) + ' group-title="%s"' % g, ext, count=1)
            f.write(ext + '\n')
            for e in it['extra']: f.write(e + '\n')
            f.write(it['url'] + '\n')

def p(name): return os.path.join(DIR, name)
def low(s): return s.lower().replace('ё', 'е')
def writelog(name, lines):
    with open(p(name), 'w', encoding='utf-8') as f: f.write('\n'.join(lines) + '\n')

# ================= правила =================
WEBCAM_URL  = re.compile(r'camsh\.gts\.tv|cctv\.|video\.iluki\.ru|city\.vtvn\.ru|/hls_\d+_\d+/|forpost\d*\.ru|/hls/\d{3,}/', re.I)
WEBCAM_NAME = re.compile(r'\bул\.|\bмкр\b|перекресток|перекрёсток|вечный огонь|путепровод|площадь ленина|\bстройк', re.I)
ADULT       = re.compile(r'18\+|\bxxx\b|\badult\b|эротик|для взрослых|porn', re.I)
FLAGS       = re.compile(r'[\U0001F1E6-\U0001F1FF]{2}')
OK_FLAGS    = {'🇷🇺', '🇧🇾', '🇺🇦'}
FOREIGN_GROUP = re.compile(r'турци|турецк|армени|armenia|азербайдж|azerb|грузия|georgia|казахстан|kazakh|узбекистан|uzbek|молдов|молдав|литва|латвия|эстони|германи|german|франци|france|испани|spain|итали|italy|индия|\bindia\b|китай|china|корея|korea|япони|japan|араб|arab|израил|israel|\busa\b|америк|britain|великобрит|польш|poland|румын|romania|болгари|сербия|хорвати|греция|туркмен|таджики|киргиз|чехия|czech|словак|венгр|нидерланд|португал|бразил|зарубеж|zarub', re.I)
FOREIGN_LETTERS = re.compile(r'[қғүұәөһңіїєґўћђљњџҚҒҮҰӘӨҺҢІЇЄҐЎЋЂЉЊЏ]|[Ա-ֆև]|[ა-ჰ]|[ăâîșţțĂÂÎȘŢȚ]|çğşıİöüäñõáéíóúãêôàèìòùëïÿļņģķžųęłśźżćńřěůőűÇĞŞÖÜÄÑÕÁÉÍÓÚÃÊÔÀÈÌÒÙËÏŸĻŅĢĶŽŲĘŁŚŹŻĆŃŘĚŮŐŰ')
NONRU_RF    = re.compile(r'\bтнв\b|\bбст\b|курай|\btmtv\b|чаваш ен|чуваш|белсат|belsat', re.I)
UA_DROP     = re.compile(r'1\+1|2\+2|\bictv\b|\bстб\b|новий|суспільне|суспiльне|україна|уніан|эспресо|еспресо|прямий|\bрада\b|плюсплюс|піксель|\bтсн\b|freedom|freeдом|\bм1\b|\bм2\b|\bк1\b|\bк2\b|\bzoom\b|24 канал|\bнло\b|\bтет\b|\bинтер\b', re.I)
KZ_DROP     = re.compile(r'\bктк\b|хабар|31 канал|7 канал|\bбалапан\b|\bqaz', re.I)
BY_KEEP     = re.compile(r'беларусь|\bонт\b|\bств\b|ctv\.by|первый информационный', re.I)
NEWS_KEEP   = re.compile(r'москва\s*24|москва доверие|^санкт-петербург$|^360|россия\s*24|мир\s*24|известия|рбк', re.I)
LOOP_KEEP   = re.compile(r'кинозал|^\[sc\]|мода\s*\d|музыка\s*\d|танцы\s*\d|обучалка|документалка', re.I)
TWO_DIGITS  = re.compile(r'\s\d{2}\s*$')
KEEP_EXTRA  = re.compile(r'leomax|shopping|shop ?& ?show|ювелирочка|тв ?1000', re.I)
CYR         = re.compile(r'[а-яё]', re.I)

def intl_rule(n):
    if re.search(r'rt\s*д(ок)?\b|rt documentary russian|rtd russian', n): return 'keep'
    if re.match(r'^rt\b|^rtд|^russia today', n): return 'drop'
    if 'brics' in n:
        return 'drop' if re.search(r'english|portugu|\beng\b|\bpt\b|espanol|arabic', n) else 'keep'
    if 'deutsche welle' in n or re.match(r'^dw\b', n):
        return 'keep' if re.search(r'russia|рус|\bru\b', n) else 'drop'
    if 'euronews' in n:
        return 'keep' if re.search(r'\bru\b|рус|россия', n) else 'review'
    return None

def classify(it):
    n, g, u = low(it['name']), it['group'].lower(), it['url'].lower()
    if ADULT.search(n) or ADULT.search(g): return 'drop', '18+'
    if WEBCAM_URL.search(u) or WEBCAM_NAME.search(n): return 'drop', 'веб-камера'
    r = intl_rule(n)
    if r == 'keep': return 'keep', 'международный (рус.)'
    if r == 'drop': return 'drop', 'иностр. дорожка'
    if BY_KEEP.search(n): return 'keep', 'Беларусь (защищён)'
    if NEWS_KEEP.search(n): return 'keep', 'крупные новостные'
    if LOOP_KEEP.search(n): return 'keep', 'петля (защищена)'
    if UA_DROP.search(n): return 'drop', 'украиноязычный'
    if KZ_DROP.search(n):
        return 'drop', ('регион РФ (РТРС)' if re.search(r'челябинск|красноярск', n) else 'Казахстан (иностр.)')
    if NONRU_RF.search(n): return 'drop', 'не рус. дорожка (нац. язык)'
    bad_flags = [f for f in FLAGS.findall(it['group']) if f not in OK_FLAGS]
    if bad_flags or FOREIGN_GROUP.search(g): return 'drop', 'иностр. группа'
    if FOREIGN_LETTERS.search(it['name']): return 'drop', 'иностр. буквы'
    if TWO_DIGITS.search(n) and not KEEP_EXTRA.search(n): return 'drop', 'числовой суффикс (петля/регион)'
    if 'украин' in g or '🇺🇦' in it['group']: return 'review', 'группа Украина'
    if CYR.search(n): return 'keep', 'кириллица'
    return 'review', 'латиница/неясно'

def stage_clean(download=False):
    if download or not os.path.exists(p('IPTV_MEGA_PLAYLIST.m3u')):
        if not download_playlist():
            print('Ошибка: не удалось скачать/найти плейлист')
            return
    items = load(p('IPTV_MEGA_PLAYLIST.m3u'))
    keep, review, drop, adult = [], [], [], 0
    for it in items:
        verdict, reason = classify(it)
        if verdict == 'keep': keep.append(it)
        elif verdict == 'review': review.append((it, reason))
        else:
            if reason == '18+': adult += 1
            else: drop.append('%s | %s | %s | %s' % (it['name'], reason, it['group'], it['url']))
    save(p('ru.m3u'), keep); save(p('ru.review.m3u'), [it for it, _ in review])
    rep = ['Всего: %d' % len(items), 'Оставлено (ru.m3u): %d' % len(keep),
           'На разбор (ru.review.m3u): %d' % len(review),
           'Удалено: %d' % (len(drop) + adult), '18+: %d (названия не перечисляются)' % adult, '', '== удалённые ==']
    rep += drop
    rep += ['', '== на разбор =='] + ['%s | %s | %s' % (it['name'], r, it['group']) for it, r in review]
    writelog('ru.report.txt', rep)
    print('clean: всего %d -> ru %d, review %d, удалено %d (18+: %d)' % (len(items), len(keep), len(review), len(drop) + adult, adult))

RESCUE_WL = re.compile(r'^(discovery|animal planet|nat ?geo|national geographic|tlc\b|id xtra|investigation discovery|history\b|h2\b|viasat|da vinci|nano\b|nick|cartoon|boomerang|jim ?jam|gulli|tiji|baby tv|english club|fox|sony|paramount|amedia|filmbox|tv ?1000|vip (premiere|megahit|comedy)|shot ?tv|black\b|red\b|sci-?fi|turbo|cinema\b|dorama|bollywood|zee\b|eurosport|russian extreme|ultra hd cinema|hd life|bridge|europa plus|ru\.tv|russian music box|music box ru|o2tv|world fashion|shopping live|leomax|shop ?& ?show|khl\b)', re.I)

def stage_rescue():
    keep = load(p('ru.m3u')); added = []
    for it in load(p('ru.review.m3u')):
        if RESCUE_WL.search(low(it['name'])):
            keep.append(it); added.append('%s | %s' % (it['name'], it['url']))
    save(p('ru_final.m3u'), keep); writelog('added.txt', added)
    print('rescue: +%d из review -> ru_final %d' % (len(added), len(keep)))

FORCE_DROP = ['мир белогорья', 'первый псковский', 'первый ростовский', 'первый крымский',
              'первый канал армения', 'юургу тв', 'юургу-тв', 'ютв']
RTRS_URL   = re.compile(r'rt-[a-z]{2,}-[a-z0-9]{2,}-htlive|/CH_R\d{2}_', re.I)
TIMESHIFT  = re.compile(r'\+\s*\d($|[^0-9a-z])|\bтаймшифт\b', re.I)
PAREN      = re.compile(r'\(([^)]*)\)')
PAREN_OK   = re.compile(r'^(hd|fhd|uhd|sd|4k|8k|\d{3,4}p?|\d{4}|\d+\+|резерв|backup|not 24/7|geo.*|россия|рф|ru|russia|рус.*|original|ориг.*)$', re.I)
REGION_STEMS = ('калуг псков ростов белогор крым севастопол симферопол ялт керч феодоси евпатори челябинск красноярск '
 'новосибирск екатеринбург казан самар омск томск перм уфа воронеж волгоград краснодар сочи тульск рязан иванов костром '
 'ярославл владимир твер смоленск брянск курск орловск липецк тамбов пенз саратов саранск киров чебоксар йошкар сыктывкар '
 'архангельск мурманск петрозаводск вологд череповец новгород калининград астрахан ставропол майкоп махачкал грозны нальчик '
 'владикавказ элист абакан кемеров барнаул алтай иркутск улан-удэ читинск якутск благовещенск хабаровск владивосток сахалин '
 'магадан камчат анадыр биробиджан сургут нижневартовск нефтеюганск ханты югор юургу тюмен курган салехард ноябрьск норильск '
 'братск ангарск ачинск бузулук орск пышм салда глазов всеволожск врангел верхняя тагил златоуст миасс магнитогорск стерлитамак '
 'нижнекамск альметьевск бугульм донбасс донецк луганск мариупол запорож херсон одесс львов харьков днепр винниц полтав чернигов '
 'сумы тернополь хмельницк черкасск кропивницк николаев ужгород луцк ровно житомир белгород обнинск киржач армени армян').split()
REGION_WORDS = re.compile(r'областн|губерни|вестник|^\d{1,2} регион', re.I)

def forced(n):
    for f in FORCE_DROP:
        if len(f) <= 4:
            if re.search(r'\b' + re.escape(f) + r'\b', n): return f
        elif f in n: return f
    return None

def regional_verdict(it):
    n, g, u = low(it['name']), it['group'].lower(), it['url']
    if USE_FORCE_DROP:
        f = forced(n)
        if f: return 'FORCE_DROP: ' + f
    if RTRS_URL.search(u): return 'РТРС-регион (URL)'
    if DROP_WINK and 'wink' in g: return 'WINK+Архив'
    if DROP_TIMESHIFT and TIMESHIFT.search(n): return 'таймшифт'
    for part in PAREN.findall(n):
        part = part.strip()
        if part and not PAREN_OK.match(part): return 'врезка/город в скобках: (%s)' % part
    if NEWS_KEEP.search(n) or BY_KEEP.search(n) or LOOP_KEEP.search(n): return None
    if DROP_BIGCITY and re.match(r'^(москва|санкт-петербург)', n): return 'мегаполис'
    for s in REGION_STEMS:
        if s in n: return 'регион (имя): ' + s
    if REGION_WORDS.search(n): return 'регион (областной/городской)'
    if FOREIGN_LETTERS.search(it['name']): return 'иностр. буквы'
    return None

def stage_regional():
    items = load(p('ru_final.m3u')); keep, removed = [], []
    for it in items:
        v = regional_verdict(it)
        if v: removed.append('%s | %s | %s' % (it['name'], v, it['url']))
        else: keep.append(it)
    save(p('ru_federal.m3u'), keep); writelog('regional_removed.txt', removed)
    writelog('kept_names.txt', sorted({it['name'] for it in keep}, key=str.lower))
    print('regional: %d -> %d (удалено %d)' % (len(items), len(keep), len(removed)))

QUALITY = re.compile(r'\b(uhd|fhd|hd|sd|4k|8k|hevc|h265|h\.?264|2160p?|1080p?|720p?|576p?|480p?|360p|240p)\b', re.I)
ALIASES = {'первый': 'первыйканал', '5канал': 'пятыйканал', 'россиякультура': 'россияк', 'khl': 'кхл'}

def norm_key(name):
    n = low(name).replace('[sc]', 'sc')
    n = re.sub(r'\[[^\]]*\]', ' ', n)
    n = re.sub(r'\(([^)]*)\)', lambda m: ' ' if re.search(r'\d{3,4}p?|hd|uhd|4k|sd|резерв|backup', m.group(1), re.I) else ' ' + m.group(1) + ' ', n)
    n = QUALITY.sub(' ', n)
    n = re.sub(r'[^a-zа-я0-9]+', '', n)
    if n.startswith('360'): n = '360'
    if not n: n = re.sub(r'[^a-zа-я0-9]+', '', low(name)) or 'unknown'
    return ALIASES.get(n, n)

def score(it):
    n, u, s = low(it['name']), it['url'].lower(), 0
    for pat, v in ((r'2160|\b4k\b|uhd', 400), (r'1080|fhd', 300), (r'\b720\b|720p|\bhd\b', 200), (r'576|480|\bsd\b', 50)):
        if re.search(pat, n): s = v; break
    if re.search(r'2160|4k|ultrahd', u): s = max(s, 380)
    elif '1080' in u: s = max(s, 280)
    elif '720' in u: s = max(s, 180)
    if u.startswith('https'): s += 5
    if '.m3u8' in u: s += 2
    return s

def stage_dedupe():
    items = load(p('ru_federal.m3u')); groups, seen_url = {}, set()
    keep, removed = [], []
    for it in items:
        if it['url'] in seen_url:
            removed.append('%s | дубль URL | %s' % (it['name'], it['url'])); continue
        seen_url.add(it['url']); groups.setdefault(norm_key(it['name']), []).append(it)
    for k, lst in groups.items():
        lst.sort(key=lambda it: -score(it))
        keep += lst[:KEEP_PER_NAME]
        for it in lst[KEEP_PER_NAME:]:
            removed.append('%s | хуже качества | %s | оставлен: %s (%s)' % (it['name'], it['url'], lst[0]['name'], lst[0]['url']))
    save(p('ru_clean.m3u'), keep); writelog('dedupe_removed.txt', removed)
    print('dedupe: %d -> %d (схлопнуто %d)' % (len(items), len(keep), len(removed)))

INTL_RE = re.compile(r'euronews|deutsche welle|^dw\b|brics|^rt\s*д|^rtд|rtd\b|rt documentary', re.I)
THEMES = [
 ('11 Беларусь',        r'беларусь|\bонт\b|\bств\b|ctv\.by|первый информационный'),
 ('02 Новости',         r'россия\s*24|москва\s*24|москва доверие|^санкт-петербург|^360|рбк|известия|мир\s*24|новост|дождь|настоящее время'),
 ('04 Спорт',           r'матч|спорт|sport|футбол|football|fight|бокс|boxing|кхл|khl|ufc|mma|мма|экстрим|extreme|\bстарт|setanta|nba|олимп'),
 ('05 Дети',            r'мульт|карусель|disney|nick|cartoon|boomerang|jim ?jam|gulli|tiji|baby|детск|смайлик|чижик|рыжий|обучалка|^о!$|в гостях у сказки|капитан фантастика|время приключений'),
 ('03 Кино и сериалы',  r'кино|film|cinema|tv ?1000|\bvip\b|amedia|paramount|sony|fox|sci-?fi|turbo|shot ?tv|\bblack|\bred\b|комедия|ужас|боевик|триллер|драма|мелодрама|детектив|фантастик|фэнтези|дорама|аниме|bollywood|zee\b|сериал|^\[sc\]|русский роман|русский бестселлер|иллюзи|премьера|остросюжет'),
 ('06 Познавательные',  r'discovery|animal planet|nat ?geo|national geographic|viasat|history|\bh2\b|id xtra|investigation|da vinci|nano|наука|история|познават|образовательн|приключен|travel|путешеств|зоопарк|живая планета|живой планет|моя планета|планета|космос|техно|эврика|просвещение|культура|россия к|доктор|здоровье|документ|english club|тайна|загадк|в мире|природа|nature|hd life|rtg|океан|galaxy|terra'),
 ('07 Музыка',          r'муз|music|mtv|bridge|ru\.tv|europa plus|шансон|ля-минор|жара|\bo2|хит|радио|radio|танцы|рок|rock'),
 ('09 Религия',         r'спас|союз|три ангела|надежда|tbn|возрождение|благо|церковь|ислам|хузур|мурад|милосердие|логос'),
 ('10 Хобби и стиль',   r'еда|кухня|кухн|food|кулинар|рецепт|усадьба|загород|охота|рыбалк|рыболов|авто|drive|мотор|гараж|дача|\bсад|огород|ремонт|мода|стиль|fashion|дизайн|интерьер|оружие|мужской|женский|hobby|точка отрыва'),
 ('08 Развлечения',     r'тнт|^стс|пятница|^че\b|^ю\b|тв\s*3|домашний|2х2|сарафан|квн|камеди|comedy|анекдот|юмор|смех|tlc|ностальгия|ретро|^время$|телекафе|вопросы и ответы|психолог|развлеч|шоу|shopping|leomax|shop|магазин|ювелир'),
 ('01 Федеральные',     r'^первый|^россия\s*1|^нтв|^пятый|^5 канал|^отр|тв центр|^твц|рен тв|^звезда|^мир\b|^суббота'),
]
THEMES = [(g, re.compile(r, re.I)) for g, r in THEMES]
OTHER = '99 Прочее'

def theme_of(it):
    n = low(it['name'])
    if SEPARATE_INT and INTL_RE.search(n): return '12 Международные (рус.)'
    for g, rx in THEMES:
        if rx.search(n): return g
    return OTHER

def natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s.lower())]

def stage_regroup():
    items = load(p('ru_clean.m3u')); buckets = {}
    for it in items: buckets.setdefault(theme_of(it), []).append(it)
    order = sorted(buckets, key=lambda g: (g[:2] if g[:2].isdigit() else '98', g))
    out = []
    for g in order:
        lst = sorted(buckets[g], key=lambda it: natkey(it['name'])) if SORT else buckets[g]
        label = g
        if MODE == 'both' and g not in ('11 Беларусь', '12 Международные (рус.)', OTHER):
            label = g[:3] + 'Россия · ' + g[3:]
        for it in lst: it['_g'] = label
        out += lst
    save(p('ru_sorted.m3u'), out, group_of=lambda it: it['_g'])
    rep = ['== Сводка групп =='] + ['%s: %d' % (g, len(buckets[g])) for g in order]
    for g in order:
        rep += ['', '== %s ==' % g] + [it['name'] for it in sorted(buckets[g], key=lambda it: natkey(it['name']))]
    rep += ['', '== ХВОСТ %s (имя | старая группа | url) ==' % OTHER]
    rep += ['%s | %s | %s' % (it['name'], it['group'], it['url']) for it in buckets.get(OTHER, [])]
    writelog('groups_report.txt', rep)
    print('regroup: %d каналов, групп %d; %s: %d' % (len(out), len(order), OTHER, len(buckets.get(OTHER, []))))

# ================= API для внешнего использования =================
def run_pipeline(download=True):
    """Запускает полный конвейер"""
    print('=== Запуск конвейера ===')
    stage_clean(download)
    stage_rescue()
    stage_regional()
    stage_dedupe()
    stage_regroup()
    print('=== Конвейер завершён ===')
    return os.path.exists(p('ru_sorted.m3u'))

STAGES = {'clean': lambda: stage_clean(True), 'rescue': stage_rescue, 'regional': stage_regional,
          'dedupe': stage_dedupe, 'regroup': stage_regroup}

if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'all'
    os.makedirs(DIR, exist_ok=True)
    if arg == 'all':
        run_pipeline(download=True)
    elif arg == 'download':
        download_playlist()
    else:
        STAGES[arg]()
