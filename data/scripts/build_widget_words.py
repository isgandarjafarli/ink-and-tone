#!/usr/bin/env python3
"""Builds widget_words.tsv, the compact word list the widgets and the watch read: one row per word
with its first definition (cut to about 40 characters) and its first example sentence.

    python3 -I scripts/data/build_widget_words.py OUT    (OUT holds words.json and sentences.json)
"""
import json, os, sys
OUT = sys.argv[1]
d = json.load(open(os.path.join(OUT, 'words.json'), encoding='utf8'))
S = json.load(open(os.path.join(OUT, 'sentences.json'), encoding='utf8'))
rows = []
def clean(s): return s.replace('\t', ' ').replace('\n', ' ')
VOWEL_START = set('aeoāáǎàēéěèōóǒò')
def joined(py):
    # one word's syllables written together, with an apostrophe before a, e, o (Xī'ān)
    parts = py.split()
    out = parts[0] if parts else ''
    for q in parts[1:]:
        if q[:1].lower() in VOWEL_START: out += "'"
        out += q
    return out
for w in d['words']:
    m = w['m'][0] if w['m'] else ''
    if len(m) > 42: m = m[:40].rsplit(' ', 1)[0] + '…'
    lv = ','.join('%s:%d' % kv for kv in sorted(w['lv'].items()))
    ex = S[w['ex'][0]] if w.get('ex') else None
    exzh = ex['zh'] if ex else ''
    expy = ' '.join(joined(t[1]) for t in ex['t'] if t[1]) if ex else ''
    exen = ex['en'] if ex else ''
    rows.append('\t'.join([str(w['id']), w['s'], w['p'], clean(m), lv, ','.join(w.get('tp', [])), str(w['f']), clean(exzh), clean(expy), clean(exen)]))
open(os.path.join(OUT, 'widget_words.tsv'), 'w', encoding='utf8').write('\n'.join(rows) + '\n')
print('tsv', os.path.getsize(os.path.join(OUT, 'widget_words.tsv')))
