# Site Académie Delaveau

Le HTML des pages de https://www.academiedelaveau.com est versionné ici et publié automatiquement sur WordPress.

## Fonctionnement

- `pages/<slug>.html` : contenu brut de chaque page WordPress.
- `pages/manifest.json` : identifiant WordPress de chaque page et date de dernière modification connue. Ne pas modifier à la main.
- À chaque push sur `main` qui modifie un `pages/*.html`, l'Action **Publier sur WordPress** envoie les pages modifiées (et seulement elles).

## Règle importante

GitHub est la source. Si une page est modifiée dans l'admin WordPress, la publication de cette page est **bloquée** (pour ne pas écraser le changement). Dans ce cas :
1. Actions → **Importer depuis WordPress** → Run workflow (récupère l'état actuel du site) ;
2. refaire la modification par-dessus.

Pour publier quand même en écrasant WordPress : Actions → **Publier sur WordPress** → Run workflow, indiquer le slug et cocher *force*.

## Limites

- Créer ou supprimer une page se fait dans WordPress, puis relancer l'import.
- Seul le contenu des pages est synchronisé (pas le titre, le modèle, les menus, les médias, les extensions).

## Pop-up des pré-inscriptions

La pop-up est définie dans `components/popup-preinscription.html` et affichée uniquement sur l'accueil.
Elle apparaît après 6 secondes ou 35 % de défilement, attend que le bandeau cookies soit fermé, et ne revient pas pendant 7 jours après fermeture.

- Modifier le texte : éditer `components/popup-preinscription.html`, puis `python3 scripts/popup.py`, puis commiter.
- Changer les pages concernées : liste `PAGES` dans `scripts/popup.py`.
- La retirer : `python3 scripts/popup.py --remove`, puis commiter.

## Secrets requis (Settings → Secrets and variables → Actions)

- `WP_USER` : compte WordPress dédié (rôle Éditeur)
- `WP_APP_PASSWORD` : mot de passe d'application de ce compte
