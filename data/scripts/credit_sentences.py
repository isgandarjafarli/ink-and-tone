#!/usr/bin/env python3
"""Adds Tatoeba credits to App/Resources/sentences.json.

Tatoeba's terms ask for each sentence's author to be named. For every pair this adds the English
sentence's id ("e") and both authors' usernames ("by": [Chinese author, English author]; an empty
string where Tatoeba lists no owner). It reads the per-language exports from
https://downloads.tatoeba.org/exports/per_language/:

    cmn/cmn_sentences_detailed.tsv, eng/eng_sentences_detailed.tsv, cmn/cmn-eng_links.tsv

    python3 -I scripts/data/credit_sentences.py EXPORT_DIR App/Resources/sentences.json
"""
import collections
import json
import os
import sys


def owners(path: str, keep=None) -> dict:
    out = {}
    for line in open(path, encoding="utf8"):
        f = line.rstrip("\n").split("\t")
        i = int(f[0])
        if keep is None or i in keep:
            out[i] = (f[2], "" if f[3] == "\\N" else f[3])
    return out


def main(folder: str, sentences: str) -> None:
    links = collections.defaultdict(list)
    for line in open(os.path.join(folder, "cmn-eng_links.tsv")):
        a, b = line.split()
        links[int(a)].append(int(b))
    cmn = owners(os.path.join(folder, "cmn_sentences_detailed.tsv"))
    eng = owners(os.path.join(folder, "eng_sentences_detailed.tsv"), {b for v in links.values() for b in v})
    data = json.load(open(sentences, encoding="utf8"))
    unmatched = 0
    for s in data:
        zh_author = cmn.get(s["src"], ("", ""))[1]
        match = [e for e in links.get(s["src"], []) if e in eng and eng[e][0] == s["en"]]
        if match:
            s["e"] = match[0]
            s["by"] = [zh_author, eng[match[0]][1]]
        else:
            unmatched += 1
            s["by"] = [zh_author, ""]
    with open(sentences, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(data)} sentences, {unmatched} without a matching English sentence")


if __name__ == "__main__":
    main(*sys.argv[1:])
