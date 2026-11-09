#!/usr/bin/env python3
"""Récupère une copie des pages publiques du site WordPress via l'API REST.

Pour chaque page :
  pages/<slug>/rendu.html   -> HTML complet tel que servi aux visiteurs
  pages/<slug>/page.json    -> données REST publiques (titre, contenu rendu, dates, template)

Lecture seule : ce script ne modifie rien sur le site.
Usage : python3 scripts/fetch_pages.py [URL_DU_SITE]
"""
import json
import pathlib
import sys
import urllib.request

SITE = (sys.argv[1] if len(sys.argv) > 1 else "https://www.academiedelaveau.com").rstrip("/")
OUT = pathlib.Path(__file__).resolve().parent.parent / "pages"
UA = {"User-Agent": "site-academie-delaveau-sync/1.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def main():
    pages, page_no = [], 1
    while True:
        batch = json.loads(get(f"{SITE}/wp-json/wp/v2/pages?per_page=100&page={page_no}"))
        pages += batch
        if len(batch) < 100:
            break
        page_no += 1

    OUT.mkdir(exist_ok=True)
    index = []
    for p in pages:
        slug = p["slug"] or str(p["id"])
        d = OUT / slug
        d.mkdir(exist_ok=True)
        keep = {k: p.get(k) for k in ("id", "slug", "link", "status", "template", "date", "modified", "title", "content", "excerpt", "parent", "menu_order")}
        (d / "page.json").write_text(json.dumps(keep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (d / "rendu.html").write_bytes(get(p["link"]))
        index.append({"id": p["id"], "slug": slug, "titre": p["title"]["rendered"], "url": p["link"], "modifie": p["modified"], "template": p["template"]})
        print(f"ok  {slug}")

    index.sort(key=lambda x: x["slug"])
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(index)} pages récupérées dans {OUT}")


if __name__ == "__main__":
    main()
