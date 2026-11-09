#!/usr/bin/env python3
"""Change l'adresse (slug) et le titre d'une page WordPress, et peut laisser une redirection à l'ancienne adresse.

Usage : python3 scripts/rename_page.py ANCIEN_SLUG NOUVEAU_SLUG "Nouveau titre" [--redirection]

- Renomme la page dans WordPress (slug + titre).
- Met à jour pages/manifest.json et renomme pages/ANCIEN_SLUG.html en pages/NOUVEAU_SLUG.html.
- Avec --redirection : crée une page publiée à l'ancienne adresse qui renvoie vers la nouvelle
  (WordPress ne redirige pas les anciennes adresses des pages), et l'ajoute au dépôt.

Variables d'environnement : WP_URL (optionnel), WP_USER, WP_APP_PASSWORD.
"""
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import wp_sync  # noqa: E402  (réutilise l'authentification et l'appel à l'API)

PAGES = wp_sync.PAGES


def redirect_html(target, title):
    return f"""<!-- wp:html -->
<!-- Redirection permanente vers {target} (gérée par scripts/rename_page.py). -->
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{target}">
<script>window.location.replace({target!r});</script>
<p style="font-family:Manrope,Arial,sans-serif;padding:140px 24px;text-align:center">
Cette page a changé d’adresse : <a href="{target}">{title}</a>.
</p>
<!-- /wp:html -->
"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 3:
        sys.exit(__doc__)
    old, new, title = args
    redirect = "--redirection" in sys.argv
    manifest = wp_sync.load_manifest()
    if old not in manifest:
        sys.exit(f"« {old} » absente de manifest.json.")
    if new in manifest:
        sys.exit(f"« {new} » existe déjà dans manifest.json.")
    entry = manifest.pop(old)

    updated = wp_sync.api("POST", f"pages/{entry['id']}", {"slug": new, "title": title})
    if updated["slug"] != new:
        sys.exit(f"WordPress a attribué le slug « {updated['slug']} » au lieu de « {new} » : arrêt, à vérifier.")
    entry.update({"titre": title, "url": updated["link"], "modified_gmt": updated["modified_gmt"]})
    manifest[new] = entry
    subprocess.run(["git", "mv", str(PAGES / f"{old}.html"), str(PAGES / f"{new}.html")], check=True)
    print(f"renommée  {old} -> {new}  ({updated['link']})")
    wp_sync.save_manifest(manifest)  # enregistré tout de suite : le renommage est fait côté WordPress

    if redirect:
        content = redirect_html(updated["link"], title)
        created = wp_sync.api("POST", "pages", {
            "slug": old, "title": f"{title} (redirection)", "status": "publish", "content": content,
        })
        if created["slug"] != old:
            print(f"ATTENTION : la redirection a reçu le slug « {created['slug']} » (ancienne adresse non couverte).")
        (PAGES / f"{created['slug']}.html").write_text(content, encoding="utf-8")
        manifest[created["slug"]] = {
            "id": created["id"], "titre": f"{title} (redirection)",
            "statut": created["status"], "template": created.get("template", ""),
            "url": created["link"], "modified_gmt": created["modified_gmt"],
        }
        print(f"redirection {created['link']} -> {updated['link']}")

    wp_sync.save_manifest(manifest)


if __name__ == "__main__":
    main()
