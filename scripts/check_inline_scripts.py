#!/usr/bin/env python3
"""Vérifie que WordPress ne cassera pas les <script> écrits dans les pages.

À l'affichage, WordPress (wptexturize) prend tout signe « < » pour le début d'une balise HTML,
jusqu'au « > » suivant, même à l'intérieur d'un <script>. Dans ce passage, il remplace chaque « & »
par « &#038; » : un « a < b && c » devient « a < b &#038;&#038; c » et tout le script plante.

Usage : python3 scripts/check_inline_scripts.py pages/<slug>.html [...]
Code de sortie 1 si un script serait altéré (la page ne doit pas être publiée en l'état).
Correction habituelle : écrire la comparaison dans l'autre sens (« b > a » au lieu de « a < b »).
"""
import re
import sys

SCRIPT = re.compile(r"<script\b[^>]*>(.*?)</script>", re.S | re.I)
# Même découpage que WordPress (get_html_split_regex) : commentaire HTML, ou « < » jusqu'au « > » suivant.
PSEUDO_TAG = re.compile(r"<(?:!--.*?(?:-->|$)|[^>]*>?)", re.S)
# Même remplacement que wptexturize : tout « & » qui ne ressemble pas déjà à une entité.
AMPERSAND = re.compile(r"&(?!#(?:\d+|x[a-f0-9]+);|[a-z1-4]{1,8};)", re.I)


def problems(text):
    found = []
    for script in SCRIPT.finditer(text):
        for tag in PSEUDO_TAG.finditer(script.group(1)):
            if AMPERSAND.search(tag.group(0)):
                line = text.count("\n", 0, script.start(1) + tag.start()) + 1
                found.append((line, tag.group(0)))
    return found


def main():
    paths = sys.argv[1:]
    if not paths:
        sys.exit(__doc__)
    total = 0
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line, snippet in problems(f.read()):
                total += 1
                extract = " ".join(snippet.split())[:120]
                print(f"::error file={path},line={line}::Script cassé par WordPress : un « & » suit un « < » avant le « > » suivant : {extract}")
    if total:
        sys.exit(f"{total} script(s) seraient altérés par WordPress : publication arrêtée.")
    print(f"Scripts vérifiés ({len(paths)} page(s)) : rien que WordPress puisse altérer.")


if __name__ == "__main__":
    main()
