#!/usr/bin/env python3
"""Builds words.json and sentences.json from open sources. This is the script that made the
bundled files on 16 November 2026; clean_meanings.py, build_widget_words.py and
credit_sentences.py then ran on its output.

Inputs (in DATA dir):
  hsk.json                         complete-hsk-vocabulary (MIT): words, HSK levels, frequency, parts of speech
  cedict_1_0_ts_utf-8_mdbg.txt     CC-CEDICT (CC BY-SA 4.0): definitions and readings
  cmn_sentences.tsv, eng_sentences.tsv, cmn-eng_links.tsv   Tatoeba (CC BY 2.0 FR)
Outputs (in OUT dir):
  words.json, sentences.json, chars_used.txt (the characters the font subset needs), stats.txt

What it changes: definitions are shortened and tidied, Tatoeba's Chinese sentences are converted
to simplified characters with OpenCC and split into words, readings are added with pypinyin, and
topics are assigned by the rules below. Characters and strokes are built separately, by
build_chars.py and build_strokes.py.

    pip install opencc-python-reimplemented pypinyin
    python3 -I scripts/data/build_words.py DATA OUT
"""
import json, os, re, sys, unicodedata, collections, random
from opencc import OpenCC
from pypinyin import pinyin as py_pinyin, Style

DATA, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
t2s = OpenCC('t2s')
HAN = re.compile(r'[㐀-鿿]')

# ---------------------------------------------------------------- pinyin utils
TONE_MARKS = {'a': 'āáǎà', 'e': 'ēéěè', 'i': 'īíǐì', 'o': 'ōóǒò', 'u': 'ūúǔù', 'ü': 'ǖǘǚǜ'}
def num_to_mark(syl):
    """peng2 -> péng ; lu:4 -> lǜ ; r5 -> r"""
    syl = syl.replace('u:', 'ü').replace('v', 'ü')
    m = re.match(r'^([a-zA-Zü]+)([1-5])$', syl)
    if not m:
        return syl
    base, tone = m.group(1), int(m.group(2))
    if tone == 5:
        return base
    low = base.lower()
    if 'a' in low: idx = low.index('a')
    elif 'e' in low: idx = low.index('e')
    elif 'ou' in low: idx = low.index('o')
    else:
        idx = max(i for i, ch in enumerate(low) if ch in 'aeiouü') if any(ch in 'aeiouü' for ch in low) else -1
    if idx < 0:
        return base
    ch = low[idx]
    mark = TONE_MARKS[ch][tone - 1]
    if base[idx].isupper():
        mark = mark.upper()
    return base[:idx] + mark + base[idx + 1:]

def tone_of(syl):
    for ch in unicodedata.normalize('NFC', syl.lower()):
        for v, marks in TONE_MARKS.items():
            if ch in marks:
                return marks.index(ch) + 1
    return 5

# ---------------------------------------------------------------- CEDICT
cedict = collections.defaultdict(list)   # simplified -> [(pinyin_num, [defs])]
for line in open(os.path.join(DATA, 'cedict_1_0_ts_utf-8_mdbg.txt'), encoding='utf8'):
    if line.startswith('#'):
        continue
    m = re.match(r'^(\S+) (\S+) \[([^\]]+)\] /(.*)/\s*$', line)
    if not m:
        continue
    trad, simp, pnum, defs = m.groups()
    cedict[simp].append((pnum, defs.split('/')))

def cedict_pinyin(word):
    ents = cedict.get(word)
    if not ents:
        return None
    # prefer lowercase reading (not a proper noun) and one that is not only "variant of"/"surname"
    def bad(e):
        d = ' '.join(e[1]).lower()
        return (e[0][:1].isupper(), d.startswith('variant of') or d.startswith('old variant') or d.startswith('surname'))
    e = sorted(ents, key=bad)[0]
    return ' '.join(num_to_mark(s) for s in e[0].split())

# ---------------------------------------------------------------- meaning cleaning
DROP = ('variant of', 'old variant of', 'surname ', 'used in ', 'see ', 'abbr. for', 'japanese variant',
        'erhua variant', 'archaic variant', 'cl:', '(tw)', 'taiwan pr.', 'also pr.', 'also written')
def clean_meanings(ms, limit=3):
    out = []
    for m in ms:
        s = m.strip()
        low = s.lower()
        if not s or any(low.startswith(p) for p in DROP):
            continue
        s = re.sub(r'\s*\[[^\]]*\]', '', s)                 # pinyin in brackets
        s = re.sub(r'([㐀-鿿]+)\|([㐀-鿿]+)', r'\2', s)  # trad|simp -> simp
        s = re.sub(r'\(Tw\)\s*', '', s)
        s = re.sub(r'\s+', ' ', s).strip(' ;,')
        if len(s) > 70:
            s = s[:67].rsplit(' ', 1)[0] + '…'
        if s and s.lower() not in (o.lower() for o in out):
            out.append(s)
        if len(out) >= limit:
            break
    return out

# ---------------------------------------------------------------- HSK words
raw = json.load(open(os.path.join(DATA, 'hsk.json'), encoding='utf8'))
SYLLABI = {'newest': 'h26', 'new': 'h30', 'old': 'h20'}

def levels(w):
    out = {}
    for l in w['level']:
        k, n = l.rsplit('-', 1)
        key = SYLLABI.get(k)
        if key:
            n = int(n)
            out[key] = min(out.get(key, 99), n)
    return out

POS_NAMES = {'n': 'noun', 'v': 'verb', 'vn': 'verb, noun', 'a': 'adjective', 'an': 'adjective, noun', 'ad': 'adjective, adverb',
             'd': 'adverb', 'b': 'adjective', 'q': 'measure word', 't': 'time word', 'f': 'direction word', 'c': 'conjunction',
             'r': 'pronoun', 'p': 'preposition', 's': 'place word', 'm': 'number', 'z': 'descriptive', 'u': 'particle',
             'y': 'particle', 'e': 'interjection', 'o': 'sound word', 'l': 'expression', 'i': 'idiom', 'nr': 'name',
             'ns': 'place name', 'nz': 'proper noun', 'k': 'suffix', 'h': 'prefix', 'g': 'morpheme', 'qv': 'measure word',
             'mq': 'number + measure', 'qt': 'measure word', 'cc': 'conjunction', 'tg': 'time word'}

# Topic rules: (topic id, label, regex on meanings, pos set)
TOPICS = [
    ('grammar', 'Grammar words', None, {'u', 'y', 'p', 'c', 'cc', 'k', 'h', 'q', 'qv', 'qt', 'e'}),
    ('numbers', 'Numbers & time', r'\b(one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|million|billion|number|half|o\'clock|minute|hour|second|day|week|month|year|morning|afternoon|evening|night|noon|today|tomorrow|yesterday|monday|sunday|weekend|calendar|date|time|season|spring|summer|autumn|winter|century|moment|early|late|age)\b', {'m', 't', 'tg', 'mq'}),
    ('people', 'People & family', r'\b(father|mother|dad|mom|mum|son|daughter|brother|sister|husband|wife|child|children|kid|baby|family|parent|grandfather|grandmother|grandpa|grandma|uncle|aunt|cousin|friend|neighbor|neighbour|man|woman|person|people|guest|boy|girl|marry|marriage|wedding|relative|lover|boyfriend|girlfriend|elder|youth)\b', None),
    ('food', 'Food & drink', r'\b(eat|drink|food|meal|rice|noodle|noodles|tea|coffee|milk|water|juice|beer|wine|fruit|apple|banana|vegetable|meat|beef|pork|chicken|fish|egg|bread|cake|dumpling|soup|sugar|salt|cook|cooking|kitchen|restaurant|breakfast|lunch|dinner|delicious|hungry|thirsty|taste|sweet|sour|bitter|spicy|menu|bowl|cup|chopsticks|dish|snack|candy)\b', None),
    ('home', 'Home & daily life', r'\b(home|house|room|bed|door|window|table|chair|sofa|kitchen|bathroom|toilet|wash|clean|sleep|wake|clothes|clothing|shirt|trousers|pants|shoe|shoes|hat|dress|wear|key|lamp|light|television|tv|phone|telephone|computer|fridge|refrigerator|furniture|bag|umbrella|towel|soap|mirror|rent|apartment|live)\b', None),
    ('travel', 'Travel & places', r'\b(travel|trip|tour|tourist|airport|plane|airplane|flight|train|station|bus|taxi|car|bike|bicycle|ticket|hotel|map|road|street|city|country|village|town|china|beijing|park|bridge|left|right|north|south|east|west|place|passport|luggage|visit|abroad|subway|ship|boat|drive|arrive|leave|journey)\b', {'s', 'ns', 'f'}),
    ('school', 'School & work', r'\b(school|student|teacher|class|lesson|study|learn|exam|test|homework|university|college|book|read|write|word|character|dictionary|question|answer|work|job|office|company|boss|colleague|meeting|manager|business|employee|salary|profession|career|research|science|knowledge|education|skill|project|plan|report)\b', None),
    ('health', 'Body & health', r'\b(body|head|eye|ear|nose|mouth|tooth|teeth|hand|foot|leg|arm|heart|face|hair|back|stomach|sick|ill|illness|disease|hospital|doctor|nurse|medicine|pain|hurt|healthy|health|cold|fever|cough|injury|exercise|tired|rest|blood|skin|patient)\b', None),
    ('nature', 'Nature & weather', r'\b(weather|rain|snow|wind|cloud|cloudy|sunny|sun|moon|star|sky|hot|cold|warm|cool|temperature|mountain|river|lake|sea|ocean|tree|flower|grass|plant|animal|dog|cat|bird|horse|cow|pig|sheep|fish|forest|earth|environment|nature|stone|fire|air|ice|island|field)\b', None),
    ('feelings', 'Feelings & character', r'\b(happy|sad|angry|afraid|fear|worry|worried|love|like|hate|feel|feeling|emotion|glad|pleased|upset|lonely|nervous|calm|excited|surprised|proud|shy|brave|kind|honest|polite|lazy|smart|clever|stupid|careful|serious|hope|wish|miss|sorry|embarrassed|satisfied|disappointed|confident|mood)\b', None),
    ('shopping', 'Shopping & money', r'\b(buy|sell|shop|store|market|supermarket|money|price|cheap|expensive|pay|cost|yuan|dollar|bank|card|cash|discount|bargain|customer|goods|receipt|spend|save|economy|tax|income|wealth|rich|poor)\b', None),
    ('talk', 'Talking & media', r'\b(say|speak|talk|tell|ask|call|chat|discuss|explain|language|chinese|english|letter|email|message|news|newspaper|magazine|internet|online|website|film|movie|song|sing|music|radio|photo|picture|story|introduce|agree|suggest|express|opinion|communicate|translate)\b', None),
    ('hobbies', 'Sports & hobbies', r'\b(sport|sports|play|game|ball|football|soccer|basketball|tennis|swim|swimming|run|running|dance|dancing|draw|drawing|paint|art|hobby|chess|match|team|win|lose|race|climb|fishing|camera|travel|party|holiday|vacation|festival|celebrate)\b', None),
    ('society', 'Society & world', r'\b(country|nation|government|law|police|army|war|peace|politics|political|president|leader|society|social|culture|history|tradition|religion|policy|rights|citizen|public|population|international|world|economy|industry|technology|organization|official|election|crime|court|military)\b', None),
]

topic_re = [(tid, label, re.compile(rx, re.I) if rx else None, pos) for tid, label, rx, pos in TOPICS]

def topics_for(word, meanings, pos):
    out = []
    text = ' '.join(meanings)
    for tid, label, rx, ps in topic_re:
        hit = (ps and set(pos) & ps) or (rx and rx.search(text))
        if tid == 'grammar' and not (ps and set(pos) & ps):
            hit = False
        if hit:
            out.append(tid)
            if tid == 'grammar':
                return out
    if len(word) == 4 and ('l' in pos or 'i' in pos or any('(idiom)' in d for _, ds in cedict.get(word, []) for d in ds)):
        out.append('idioms')
    return out[:3]

words = []
wid = {}
for w in raw:
    lv = levels(w)
    if not lv:
        continue
    s = w['simplified']
    forms = w['forms']
    def badform(fm):
        m0 = (fm['meanings'] or [''])[0].lower()
        return (any(m0.startswith(p) for p in DROP), fm['transcriptions']['pinyin'][:1].isupper())
    common = {'长': 'cháng'}.get(s) or (py_pinyin(s, style=Style.TONE)[0][0] if len(s) == 1 else None)
    forms_sorted = sorted(forms, key=lambda fm: (badform(fm)[0], common is not None and fm['transcriptions']['pinyin'].lower() != common, badform(fm)[1]))
    f0 = forms_sorted[0]
    meanings = clean_meanings(f0['meanings'])
    if not meanings:
        for fm in forms_sorted[1:]:
            meanings = clean_meanings(fm['meanings'])
            if meanings:
                break
    if not meanings:
        meanings = clean_meanings([d for _, ds in cedict.get(s, []) for d in ds]) or [m for m in f0['meanings'][:1]]
    alt = []
    for fm in forms_sorted[1:]:
        p = fm['transcriptions']['pinyin']
        if p != f0['transcriptions']['pinyin'] and not badform(fm)[0]:
            ms = clean_meanings(fm['meanings'], 2)
            if ms:
                alt.append({'p': p, 'm': ms})
    cls = []
    for c in f0.get('classifiers', []) or []:
        c = c.split('|')[-1] if '|' in c else c
        if c not in cls:
            cls.append(c)
    pos = w.get('pos', [])
    rec = {
        'id': len(words) + 1,
        's': s,
        'p': f0['transcriptions']['pinyin'],
        'm': meanings,
        'lv': lv,
        'f': w.get('frequency', 99999),
    }
    tr = f0.get('traditional')
    if tr and tr != s:
        rec['t'] = tr
    if pos:
        rec['pos'] = sorted({POS_NAMES.get(p, '') for p in pos if POS_NAMES.get(p)}, key=lambda x: [POS_NAMES.get(p) for p in pos].index(x))[:2]
    if cls:
        rec['cl'] = cls[:2]
    if alt:
        rec['alt'] = alt[:2]
    tps = topics_for(s, meanings, pos)
    if tps:
        rec['tp'] = tps
    words.append(rec)
    wid.setdefault(s, rec)

print('words', len(words))

# ---------------------------------------------------------------- segmentation dictionary
lex = set(cedict.keys()) | set(wid.keys())
MAXLEN = 6
def segment(text):
    toks = []
    i = 0
    while i < len(text):
        ch = text[i]
        if not HAN.match(ch):
            j = i
            while j < len(text) and not HAN.match(text[j]):
                j += 1
            toks.append(text[i:j])
            i = j
            continue
        for L in range(min(MAXLEN, len(text) - i), 0, -1):
            cand = text[i:i + L]
            if L == 1 or cand in lex:
                toks.append(cand)
                i += L
                break
    return toks

# ---------------------------------------------------------------- Tatoeba
cmn = {}
for line in open(os.path.join(DATA, 'cmn_sentences.tsv'), encoding='utf8'):
    parts = line.rstrip('\n').split('\t')
    if len(parts) == 3:
        cmn[int(parts[0])] = parts[2]
links = collections.defaultdict(list)
for line in open(os.path.join(DATA, 'cmn-eng_links.tsv'), encoding='utf8'):
    a, b = line.split()
    links[int(a)].append(int(b))
need_eng = {b for bs in links.values() for b in bs}
eng = {}
for line in open(os.path.join(DATA, 'eng_sentences.tsv'), encoding='utf8'):
    i, _, rest = line.partition('\t')
    if int(i) in need_eng:
        eng[int(i)] = rest.split('\t', 1)[1].rstrip('\n')

# level of a token under the default syllabus (h26), falling back to h30, else 10 (unknown)
def tok_level(t):
    r = wid.get(t)
    if r:
        return r['lv'].get('h26', r['lv'].get('h30', r['lv'].get('h20', 7)))
    if not HAN.search(t):
        return 0
    # a token not in HSK lists: use the hardest char level if every char is a known HSK word, else 10
    if len(t) > 1 and all(c in wid for c in t):
        return max(tok_level(c) for c in t)
    return 10

sents = []
seen = set()
for sid, zh in cmn.items():
    if sid not in links:
        continue
    zs = t2s.convert(zh).strip()
    if zs in seen:
        continue
    n_han = len(HAN.findall(zs))
    if n_han < 4 or n_han > 24:
        continue
    if re.search(r'[A-Za-z]{2,}', zs):       # skip sentences with latin words / names
        continue
    en_opts = [eng[e] for e in links[sid] if e in eng]
    if not en_opts:
        continue
    en = min(en_opts, key=len)
    if len(en) > 120:
        continue
    seen.add(zs)
    toks = segment(zs)
    diff = max([tok_level(t) for t in toks] or [0])
    sents.append({'tid': sid, 'zh': zs, 'en': en, 'toks': toks, 'diff': diff, 'n': n_han})
print('candidate sentences', len(sents))

# index sentences by token
by_tok = collections.defaultdict(list)
for i, s in enumerate(sents):
    for t in set(s['toks']):
        by_tok[t].append(i)

chosen = {}
use_count = collections.Counter()
for rec in sorted(words, key=lambda r: r['f']):
    lvl = rec['lv'].get('h26', rec['lv'].get('h30', rec['lv'].get('h20', 7)))
    cands = by_tok.get(rec['s'], [])
    scored = []
    for i in cands:
        s = sents[i]
        over = max(0, s['diff'] - max(lvl, 2))      # how far above the word's level
        if over > 2:
            continue
        ideal = 7 + 2 * min(lvl, 6)                   # longer sentences for higher levels
        score = over * 6 + abs(s['n'] - ideal) * 0.6 + use_count[i] * 4
        scored.append((score, i))
    scored.sort()
    picks = []
    for _, i in scored:
        if any(sents[i]['zh'][:6] == sents[j]['zh'][:6] for j in picks):
            continue
        picks.append(i)
        if len(picks) >= 3:
            break
    for i in picks:
        use_count[i] += 1
    if picks:
        rec['ex'] = picks
used = sorted({i for r in words for i in r.get('ex', [])})
remap = {old: new for new, old in enumerate(used)}
for r in words:
    if 'ex' in r:
        r['ex'] = [remap[i] for i in r['ex']]

def tok_pinyin(t, ctx=None):
    if not HAN.search(t):
        return ''
    r = wid.get(t)
    if r and len(t) > 1 and len(r['p'].split()) == len(t):
        return r['p']
    if ctx:
        return ' '.join(ctx)
    p = cedict_pinyin(t)
    if p and len(p.split()) == len(t):
        return p
    return ' '.join(x[0] for x in py_pinyin(t, style=Style.TONE))

out_sents = []
for old in used:
    s = sents[old]
    toks = []
    full = [x[0] for x in py_pinyin(s['zh'], style=Style.TONE, errors=lambda x: [''] * len(x))]
    pos = 0
    for t in s['toks']:
        r = wid.get(t)
        ctx = full[pos:pos + len(t)] if HAN.search(t) and len(full) == len(s['zh']) else None
        tp = tok_pinyin(t, ctx)
        k = len(toks)
        nxt = s['toks'][k + 1] if k + 1 < len(s['toks']) else ''
        if t == '得' and k > 0 and HAN.match(s['toks'][k - 1][-1]) and nxt[:1] not in ('到', '了', '出', '知', '分', '病', '奖'):
            tp = 'de'
        toks.append([t, tp, r['id'] if r else 0])
        pos += len(t)
    out_sents.append({'zh': s['zh'], 'en': s['en'], 't': toks, 'src': s['tid']})
print('sentences used', len(out_sents), 'words with ex', sum(1 for r in words if 'ex' in r))


# ---------------------------------------------------------------- write
json.dump({'v': 1, 'topics': [[t[0], t[1]] for t in TOPICS] + [['idioms', 'Idioms (chengyu)']], 'words': words},
          open(os.path.join(OUT, 'words.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
json.dump(out_sents, open(os.path.join(OUT, 'sentences.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
used_chars = set(''.join(r['s'] for r in words)) | set(''.join(s['zh'] for s in out_sents)) | set(''.join(r.get('t', '') for r in words))
open(os.path.join(OUT, 'chars_used.txt'), 'w', encoding='utf8').write(''.join(sorted(used_chars)))
with open(os.path.join(OUT, 'stats.txt'), 'w') as f:
    for key in ('h26', 'h30', 'h20'):
        c = collections.Counter(r['lv'][key] for r in words if key in r['lv'])
        ex = collections.Counter(r['lv'][key] for r in words if key in r['lv'] and 'ex' in r)
        f.write(key + ' ' + ' '.join('L%d:%d(ex %d)' % (k, c[k], ex[k]) for k in sorted(c)) + '\n')
    tc = collections.Counter(t for r in words for t in r.get('tp', []))
    f.write('topics ' + str(tc.most_common()) + '\n')
print(open(os.path.join(OUT, 'stats.txt')).read())
