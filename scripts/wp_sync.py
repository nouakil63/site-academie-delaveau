#!/usr/bin/env python3
"""Synchronisation des pages entre ce dépôt et WordPress (API REST).

Commandes :
  import            Récupère le HTML brut de toutes les pages dans pages/<slug>.html
                    et met à jour pages/manifest.json.
  push FICHIER...   Publie sur WordPress les fichiers pages/<slug>.html indiqués.
                    Refuse de publier une page modifiée dans l'admin WordPress
                    depuis le dernier import/push (sauf avec --force).

Variables d'environnement : WP_URL (optionnel), WP_USER, WP_APP_PASSWORD.
"""
import argparse
import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ROOT / "pages"
MANIFEST = PAGES / "manifest.json"
SITE = os.environ.get("WP_URL", "https://www.academiedelaveau.com").rstrip("/")


def auth_header():
    user, pwd = os.environ.get("WP_USER"), os.environ.get("WP_APP_PASSWORD")
    if not user or not pwd:
        sys.exit("WP_USER et WP_APP_PASSWORD doivent être définis.")
    token = base64.b64encode(f"{user}:{pwd.replace(' ', '')}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def api(method, path, body=None):
    headers = {"User-Agent": "site-academie-delaveau-sync/1.0", "Accept": "application/json", **auth_header()}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{SITE}/wp-json/wp/v2/{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=int(os.environ.get("WP_TIMEOUT", "300"))) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SyncError(f"Erreur {e.code} sur {method} {path} : {e.read()[:500].decode(errors='replace')}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise SyncTimeout(f"Pas de réponse sur {method} {path} : {e}")


class SyncError(Exception):
    pass


class SyncTimeout(SyncError):
    pass


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}


def save_manifest(m):
    MANIFEST.write_text(json.dumps(dict(sorted(m.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_import(_args):
    try:
        _import()
    except SyncError as e:
        sys.exit(str(e))


def _import():
    pages, n = [], 1
    while True:
        batch = api("GET", f"pages?context=edit&per_page=100&page={n}&status=publish,draft,private,pending,future")
        pages += batch
        if len(batch) < 100:
            break
        n += 1
    PAGES.mkdir(exist_ok=True)
    manifest = {}
    for p in pages:
        slug = p["slug"] or f"page-{p['id']}"
        (PAGES / f"{slug}.html").write_text(p["content"]["raw"], encoding="utf-8")
        manifest[slug] = {
            "id": p["id"],
            "titre": p["title"]["raw"],
            "statut": p["status"],
            "template": p["template"],
            "url": p["link"],
            "modified_gmt": p["modified_gmt"],
        }
        print(f"importée  {slug}  (id {p['id']})")
    save_manifest(manifest)
    print(f"{len(manifest)} pages importées.")


def cmd_push(args):
    manifest = load_manifest()
    errors = 0
    for f in args.files:
        path = (ROOT / f) if not os.path.isabs(f) else pathlib.Path(f)
        if path.suffix != ".html" or path.parent.resolve() != PAGES.resolve():
            continue
        slug = path.stem
        if not path.exists():
            print(f"ignorée   {slug} : fichier supprimé (la page WordPress n'est pas supprimée)")
            continue
        entry = manifest.get(slug)
        if not entry:
            print(f"ERREUR    {slug} : absente de manifest.json (créer la page dans WordPress puis relancer l'import)")
            errors += 1
            continue
        content = path.read_text(encoding="utf-8")
        try:
            current = api("GET", f"pages/{entry['id']}?context=edit&_fields=modified_gmt,content")
            if current["modified_gmt"] != entry["modified_gmt"] and not args.force:
                print(f"ERREUR    {slug} : modifiée dans WordPress le {current['modified_gmt']} (UTC) depuis le dernier import. "
                      "Relancer l'import pour récupérer ces changements, ou publier avec l'option force.")
                errors += 1
                continue
            if current["content"]["raw"] == content:
                print(f"inchangée {slug}")
                entry["modified_gmt"] = current["modified_gmt"]
                save_manifest(manifest)
                continue
            try:
                updated = api("POST", f"pages/{entry['id']}", {"content": content})
            except SyncTimeout:
                # Le serveur a pu enregistrer sans répondre à temps : on vérifie avant de conclure.
                check = api("GET", f"pages/{entry['id']}?context=edit&_fields=modified_gmt,content,link")
                if check["content"]["raw"] != content:
                    raise
                updated = check
                print(f"(réponse tardive, enregistrement vérifié) {slug}")
            entry["modified_gmt"] = updated["modified_gmt"]
            save_manifest(manifest)
            print(f"publiée   {slug}  -> {updated['link']}")
        except SyncError as e:
            print(f"ERREUR    {slug} : {e}")
            errors += 1
    save_manifest(manifest)
    if errors:
        sys.exit(f"{errors} page(s) non publiée(s).")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("import").set_defaults(func=cmd_import)
    p = sub.add_parser("push")
    p.add_argument("files", nargs="*")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_push)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
