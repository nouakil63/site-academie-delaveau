#!/usr/bin/env python3
"""Remplace un texte dans le gabarit d'un formulaire Contact Form 7 (API REST de CF7).

Usage :
  python3 scripts/cf7_replace.py "Titre" "texte à remplacer" "nouveau texte" [--apply] [--prop form|mail.body|mail_2.body]
  python3 scripts/cf7_replace.py "Titre" --show        affiche le gabarit, l'email et l'email 2 (lecture seule)
Sans --apply : simulation, rien n'est modifié (affiche le passage concerné).
Seule la propriété visée (par défaut le gabarit « form ») est modifiée ; le reste (Stripe…) est intact.

Variables d'environnement : WP_URL (optionnel), WP_USER, WP_APP_PASSWORD.
"""
import base64
import json
import os
import re
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


def text_of(value):
    if isinstance(value, dict):
        return value.get("body") or value.get("content") or ""
    return value or ""


def get_prop(full, prop):
    props = full["properties"]
    if prop == "form":
        return text_of(props["form"])
    key, field = prop.split(".")
    return (props.get(key) or {}).get(field, "")


def main():
    argv = sys.argv[1:]
    apply = "--apply" in argv
    show = "--show" in argv
    prop = "form"
    if "--prop" in argv:
        prop = argv[argv.index("--prop") + 1]
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--prop")]
    if not args or (not show and len(args) != 3):
        sys.exit(__doc__)
    title = args[0]
    forms = call("GET", "contact-forms?per_page=100")
    matches = [f for f in forms if f.get("title") == title]
    print("Formulaires visibles :", ", ".join(f'{f["id"]} « {f["title"]} »' for f in forms))
    if len(matches) != 1:
        sys.exit(f"{len(matches)} formulaire(s) nommé(s) « {title} » : arrêt.")
    form_id = matches[0]["id"]
    full = call("GET", f"contact-forms/{form_id}")
    if show:
        print("\n===== config_errors =====")
        print(json.dumps(full.get("config_errors"), ensure_ascii=False, indent=1))
        for key in ("mail", "mail_2"):
            m = full["properties"].get(key) or {}
            print(f"\n===== {key} (réglages) =====")
            for field in ("active", "recipient", "sender", "additional_headers", "use_html", "exclude_blank"):
                v = m.get(field)
                print(f"{field}: " + re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "<adresse>", str(v)) + ("   <-- VIDE" if v in ("", None) and field in ("recipient", "sender") else ""))
        for p in ("form", "mail.subject", "mail.body", "mail_2.active", "mail_2.subject", "mail_2.body"):
            print(f"\n===== {p} =====")
            # Dépôt public : les journaux sont visibles de tous, on masque les adresses.
            print(re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "<adresse masquée>", str(get_prop(full, p))))
        return
    old, new = args[1], args[2]
    content = get_prop(full, prop)
    count = content.count(old)
    print(f"Formulaire {form_id}, {prop} : {count} occurrence(s) de « {old} ».")
    if count == 0:
        sys.exit("Texte introuvable : rien n'est modifié.")
    i = content.index(old)
    print("Contexte actuel :", content[max(0, i - 80): i + len(old) + 80].replace("\n", " ⏎ "))
    if not apply:
        print("Simulation : relancer avec --apply pour modifier.")
        return
    updated = content.replace(old, new)
    if prop == "form":
        body = {"form": updated}
    else:
        key, field = prop.split(".")
        current = dict(full["properties"].get(key) or {})
        current[field] = updated
        body = {key: current}
    body["context"] = "save"
    resp = call("POST", f"contact-forms/{form_id}", body)
    print("Réponse :", {k: resp.get(k) for k in ("id", "status", "into", "invalid_fields", "config_errors", "message") if k in resp})
    check = get_prop(call("GET", f"contact-forms/{form_id}"), prop)
    if new in check and (old not in check or old in new):
        print(f"Modifié ({prop}) : « {old} » → « {new} ».")
    else:
        sys.exit("La vérification après modification a échoué.")


if __name__ == "__main__":
    main()
