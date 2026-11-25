#!/usr/bin/env python3
"""Builds App/Resources/chars.json from the Unicode Han Database (Unihan), under the Unicode
License v3.

Each character gets its stroke count (from strokes.pack where it has the character, so it matches
the animation, otherwise Unihan's kTotalStrokes), a reading and a gloss, and its Kangxi radical
with the radical's English name (kRSUnicode, CJKRadicals.txt).

When the character is also a word in the app's list, the reading and gloss come from that word
(the most frequent one if there are several), so the two screens agree. Otherwise they come from
Unihan's kMandarin (first reading) and kDefinition.

    python3 -I scripts/data/build_chars.py UNIHAN_DIR CJKRadicals.txt App/Resources/words.json \
        Shared/Resources/strokes.pack App/Resources/chars.json
"""
import glob
import json
import os
import re
import struct
import sys
import unicodedata


def unihan(folder: str) -> dict:
    data: dict = {}
    for path in glob.glob(os.path.join(folder, "Unihan_*.txt")):
        for line in open(path, encoding="utf8"):
            if line.startswith("U+"):
                cp, field, value = line.rstrip("\n").split("\t", 2)
                data.setdefault(chr(int(cp[2:], 16)), {})[field] = value
    return data


def radicals(path: str) -> dict:
    """Radical number ("85", or "120'" for a simplified form) to (ideograph, English name).
    The file gives code points in hex: number; radical character (may be empty); ideograph."""
    out = {}
    for line in open(path, encoding="utf8"):
        if line.startswith("#") or not line.strip():
            continue
        num, rad, ideo = [x.strip() for x in line.split(";")]
        rad, ideo = (chr(int(x, 16)) if x else "" for x in (rad, ideo))
        name = unicodedata.name(rad, "").lower() if rad else ""
        name = re.sub(r"^(kangxi radical|cjk radical) ", "", name)
        name = re.sub(r"\b(c-simplified|j-simplified|simplified)\b ?", "", name).strip()
        out[num] = (ideo, name)
    return out


def stroke_counts(pack: str) -> dict:
    raw = open(pack, "rb").read()
    n = struct.unpack("<I", raw[:4])[0]
    index = json.loads(raw[4:4 + n])
    out = {}
    for key, (offset, length) in index.items():
        if key == "notice":
            continue
        blob = json.loads(raw[4 + n + offset:4 + n + offset + length])
        out[chr(int(key, 16))] = len(blob["s"])
    return out


def main(folder: str, radical_file: str, words: str, pack: str, out: str) -> None:
    han = unihan(folder)
    rads = radicals(radical_file)
    strokes = stroke_counts(pack)
    word_list = json.load(open(words, encoding="utf8"))["words"]
    wanted = sorted({ch for w in word_list for ch in w["s"]})
    as_word = {}
    for w in sorted(word_list, key=lambda w: w.get("f") or 10**9, reverse=True):
        if len(w["s"]) == 1:
            as_word[w["s"]] = w
    result, missing = {}, []
    for ch in wanted:
        u = han.get(ch, {})
        if "kDefinition" not in u or "kMandarin" not in u:
            missing.append(ch)
            continue
        w = as_word.get(ch)
        entry = {
            "n": strokes.get(ch) or int(u.get("kTotalStrokes", "0").split()[0]),
            "p": w["p"].lower() if w else u["kMandarin"].split()[0],
            "m": "; ".join(w["m"][:3]) if w else re.sub(r"\bi\b", "I", u["kDefinition"]),
        }
        rs = u.get("kRSUnicode", "").split()
        if rs:
            num = rs[0].split(".")[0]
            if num in rads:
                entry["r"] = rads[num][0]
                if rads[num][1]:
                    entry["rn"] = rads[num][1]
        result[ch] = entry
    with open(out, "w", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(result)} characters; no Unihan entry for {len(missing)}: {''.join(missing)}")


if __name__ == "__main__":
    main(*sys.argv[1:])
