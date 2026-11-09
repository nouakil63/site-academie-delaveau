#!/usr/bin/env python3
"""Ajoute (ou met à jour) la pop-up des pré-inscriptions dans les pages.

Source : components/popup-preinscription.html
Usage :
  python3 scripts/popup.py           ajoute / met à jour la pop-up dans PAGES
  python3 scripts/popup.py --remove  la retire de toutes les pages
Puis commiter : le push sur main publie les pages modifiées.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "components" / "popup-preinscription.html"

# Pages où la pop-up apparaît (uniquement l'accueil).
PAGES = [
    "accueil-2",
]

BLOCK = re.compile(r"\n*<!-- wp:html -->\n<!-- popup-preinscription:start.*?<!-- popup-preinscription:end -->\n<!-- /wp:html -->\n*", re.S)


def main():
    remove = "--remove" in sys.argv
    snippet = COMPONENT.read_text(encoding="utf-8").strip()
    block = f"\n\n<!-- wp:html -->\n{snippet}\n<!-- /wp:html -->\n"
    targets = sorted(p.stem for p in (ROOT / "pages").glob("*.html")) if remove else PAGES
    for slug in targets:
        path = ROOT / "pages" / f"{slug}.html"
        text = path.read_text(encoding="utf-8")
        if remove and not BLOCK.search(text):
            continue
        base = BLOCK.sub("\n", text).rstrip("\n") + "\n"
        new = base if remove else base.rstrip("\n") + block
        if new != text:
            path.write_text(new, encoding="utf-8")
            print(("retirée  " if remove else "à jour   ") + slug)


if __name__ == "__main__":
    main()
