#!/usr/bin/env python3
"""Ajoute (ou met à jour) les composants partagés dans les pages.

Composants (dossier components/) :
  popup-preinscription  fenêtre centrée des pré-inscriptions (accueil uniquement)
  brevo-masque          masque la pop-up newsletter Brevo (toutes les pages publiées)
  menu-saison           libellé « Pré-inscription 2027-2028 » du bouton du menu (toutes les pages publiées)

Usage :
  python3 scripts/popup.py                    met à jour tous les composants
  python3 scripts/popup.py --remove NOM       retire le composant NOM de toutes les pages
Puis commiter : le push sur main publie les pages modifiées.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / "pages"


def published_pages():
    manifest = json.loads((PAGES_DIR / "manifest.json").read_text(encoding="utf-8"))
    return sorted(slug for slug, meta in manifest.items() if meta.get("statut") == "publish")


# Pages où chaque composant apparaît.
COMPONENTS = {
    "popup-preinscription": lambda: ["accueil-2"],
    "brevo-masque": published_pages,
    "menu-saison": published_pages,
}


def block_re(name):
    return re.compile(rf"\n*<!-- wp:html -->\n<!-- {name}:start.*?<!-- {name}:end -->\n<!-- /wp:html -->\n*", re.S)


def apply(name, remove=False):
    pattern = block_re(name)
    snippet = (ROOT / "components" / f"{name}.html").read_text(encoding="utf-8").strip()
    block = f"\n\n<!-- wp:html -->\n{snippet}\n<!-- /wp:html -->\n"
    targets = set() if remove else set(COMPONENTS[name]())
    for path in sorted(PAGES_DIR.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        has = bool(pattern.search(text))
        want = path.stem in targets
        if not has and not want:
            continue
        if has and want:
            inner = re.compile(rf"<!-- {name}:start.*?<!-- {name}:end -->", re.S)
            new = inner.sub(lambda _: snippet, text, count=1)  # mise à jour sur place
        else:
            base = pattern.sub("\n", text).rstrip("\n") + "\n"
            new = base.rstrip("\n") + block if want else base
        if new != text:
            path.write_text(new, encoding="utf-8")
            print(f"{name:22} {'à jour ' if want else 'retiré '} {path.stem}")


def main():
    if "--remove" in sys.argv:
        apply(sys.argv[sys.argv.index("--remove") + 1], remove=True)
    else:
        for name in COMPONENTS:
            apply(name)


if __name__ == "__main__":
    main()
