#!/usr/bin/env python3
"""Remplace un texte dans le gabarit d'un formulaire Contact Form 7 (API REST de CF7).

Usage : python3 scripts/cf7_replace.py "Titre du formulaire" "texte à remplacer" "nouveau texte" [--apply]
Sans --apply : simulation, rien n'est modifié (affiche le formulaire trouvé et le passage concerné).
Seul le gabarit du formulaire (« form ») est modifié : mails, messages et réglages (Stripe…) restent intacts.

Variables d'environnement : WP_URL (optionnel), WP_USER, WP_APP_PASSWORD.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

SITE = os.environ.get("WP_URL", "https://www.academiedelaveau.com").rstrip("/")


def call(method, path, body=None):
    user, pwd = os.environ.get("WP_USER"), os.environ.get("WP_APP_PASSWORD")
    if not user or not pwd:
        sys.exit("WP_USER et WP_APP_PASSWORD doivent être définis.")
    token = base64.b64encode(f"{user}:{pwd.replace(' ', '')}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Accept": "application/json", "User-Agent": "site-academie-delaveau-sync/1.0"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{SITE}/wp-json/contact-form-7/v1/{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"Erreur {e.code} sur {method} {path} : {e.read()[:400].decode(errors='replace')}")


def main():
    args = [a for a in sys.argv[1:] if a != "--apply"]
    if len(args) != 3:
        sys.exit(__doc__)
    title, old, new = args
    apply = "--apply" in sys.argv
    forms = call("GET", "contact-forms?per_page=100")
    matches = [f for f in forms if f.get("title") == title]
    print("Formulaires visibles :", ", ".join(f'{f["id"]} « {f["title"]} »' for f in forms))
    if len(matches) != 1:
        sys.exit(f"{len(matches)} formulaire(s) nommé(s) « {title} » : arrêt.")
    form_id = matches[0]["id"]
    full = call("GET", f"contact-forms/{form_id}")
    content = full["properties"]["form"]
    if isinstance(content, dict):
        content = content.get("body") or content.get("content") or ""
    count = content.count(old)
    print(f"Formulaire {form_id} : {count} occurrence(s) de « {old} ».")
    if count == 0:
        sys.exit("Texte introuvable : rien n'est modifié.")
    i = content.index(old)
    print("Contexte actuel :", content[max(0, i - 80): i + len(old) + 80].replace("\n", " ⏎ "))
    if not apply:
        print("Simulation : relancer avec --apply pour modifier.")
        return
    updated = content.replace(old, new)
    resp = call("POST", f"contact-forms/{form_id}", {"form": updated, "context": "save"})
    print("Réponse :", {k: resp.get(k) for k in ("id", "status", "into", "invalid_fields", "config_errors", "message") if k in resp})
    check = call("GET", f"contact-forms/{form_id}")["properties"]["form"]
    if isinstance(check, dict):
        check = check.get("body") or check.get("content") or ""
    if new in check and old not in check:
        print(f"Modifié : « {old} » → « {new} ».")
    else:
        sys.exit("La vérification après modification a échoué.")


if __name__ == "__main__":
    main()
