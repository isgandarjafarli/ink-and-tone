#!/usr/bin/env python3
"""Renames the subset of LXGW WenKai that the app ships.

The SIL Open Font License reserves the names 霞鹜, 霞鶩, 落霞孤鹜, 落霞孤鶩 and LXGW, so a modified
copy (a subset counts) has to use another name. This keeps the copyright (name ID 0), the licence
(IDs 13 and 14) and the designer credits, and changes only the font's own names.

    python3 -I scripts/data/rename_font.py SUBSET.ttf Shared/Resources/SealKai-Subset.ttf
"""
import sys

from fontTools.ttLib import TTFont

FAMILY = "Seal Kai"
POSTSCRIPT = "SealKai-Regular"
NOTE = ("A subset of LXGW WenKai (https://github.com/lxgw/LxgwWenKai), cut down to the characters "
        "the app uses and renamed as the SIL Open Font License 1.1 requires.")


def main(src: str, dst: str) -> None:
    font = TTFont(src)
    name = font["name"]
    version = name.getDebugName(5) or "Version 1"
    # The Chinese names and the sample text use the reserved names, so keep only the English
    # records, and drop the sample text and the typographic names.
    name.names = [r for r in name.names if r.langID == 0x409 and r.nameID not in (16, 17, 18, 19, 21, 22)]
    for nid, text in {1: FAMILY, 2: "Regular", 3: f"{FAMILY}:{version}", 4: FAMILY,
                      5: f"{version}; subset", 6: POSTSCRIPT, 10: NOTE}.items():
        name.setName(text, nid, 3, 1, 0x409)
    font.save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
