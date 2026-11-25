#!/usr/bin/env python3
"""Final tidy of CC-CEDICT glosses in words.json: drops dictionary bookkeeping that confuses learners.

    python3 -I scripts/data/clean_meanings.py App/Resources/words.json
"""
import json, re, sys
p = sys.argv[1]
d = json.load(open(p, encoding='utf8'))
rules = [
    (re.compile(r'\(bound form\)\s*'), ''),
    (re.compile(r'\s*\(Taiwan pr\.[^)]*\)'), ''),
    (re.compile(r'\s*\(abbr\. for [^)]*\)'), ''),
    (re.compile(r'\s*\(old\)\s*'), ' '),
    (re.compile(r'\s{2,}'), ' '),
]
changed = 0
for w in d['words']:
    out = []
    for m in w['m']:
        n = m
        for rx, rep in rules: n = rx.sub(rep, n)
        n = n.strip(' ;')
        if n and n not in out: out.append(n)
        if n != m: changed += 1
    if out: w['m'] = out
json.dump(d, open(p, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
print('cleaned', changed)
