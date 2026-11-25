#!/usr/bin/env python3
"""Builds Shared/Resources/strokes.pack from Make Me a Hanzi's graphics.txt.

graphics.txt is under the Arphic Public License, which asks that a changed copy say how and when
it was changed. The pack keeps every stroke outline and median exactly as graphics.txt has them,
for the simplified characters in the word list only, and stores them in a format the app can read
one character at a time. It carries that notice inside the file, under the key "notice".

Format: a 4-byte little-endian index length, a JSON index {hex code point: [offset, length]},
then one compact JSON object per character: {"s": [SVG path, ...], "m": [[[x, y], ...], ...]}.

    python3 -I scripts/data/build_strokes.py graphics.txt App/Resources/words.json Shared/Resources/strokes.pack
"""
import datetime
import json
import struct
import sys

SOURCE = "https://github.com/skishore/makemeahanzi/blob/master/graphics.txt"


def notice(count: int, commit: str) -> str:
    today = datetime.date.today().isoformat()
    return (f"Stroke outlines and medians from Make Me a Hanzi graphics.txt ({SOURCE}, commit {commit}), "
            "under the Arphic Public License, a copy of which ships with the app as ThirdPartyNotices.txt. "
            f"Changed on {today}: kept {count} characters (the simplified characters in the app's word list), "
            "dropped every other field, and repacked them into this indexed file. "
            "The outlines and medians themselves are unchanged.")


def main(graphics: str, words: str, out: str, commit: str = "unknown") -> None:
    wanted = {ch for w in json.load(open(words, encoding="utf8"))["words"] for ch in w["s"]}
    found = {}
    for line in open(graphics, encoding="utf8"):
        d = json.loads(line)
        if d["character"] in wanted:
            found[d["character"]] = {"s": d["strokes"], "m": d["medians"]}
    index, blobs, offset = {}, [], 0
    for ch in sorted(found):
        blob = json.dumps(found[ch], ensure_ascii=False, separators=(",", ":")).encode()
        index[format(ord(ch), "x")] = [offset, len(blob)]
        blobs.append(blob)
        offset += len(blob)
    text = notice(len(found), commit).encode()
    index["notice"] = [offset, len(text)]
    blobs.append(text)
    head = json.dumps(index, separators=(",", ":")).encode()
    with open(out, "wb") as f:
        f.write(struct.pack("<I", len(head)))
        f.write(head)
        for b in blobs:
            f.write(b)
    print(f"{len(found)} characters, {offset + len(text)} bytes of data")


if __name__ == "__main__":
    main(*sys.argv[1:])
