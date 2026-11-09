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

## Composants partagés (`components/`)

Insérés dans les pages par `python3 scripts/popup.py` (à relancer après toute modification, puis commiter).

- **popup-preinscription** — fenêtre centrée annonçant les pré-inscriptions, sur l'accueil uniquement. Apparaît après 5 secondes ou 35 % de défilement, attend que le bandeau cookies soit fermé, ne revient pas pendant 7 jours après fermeture (plus du tout après un clic sur « Je me pré-inscris »).
- **brevo-masque** — masque la pop-up newsletter Brevo sur toutes les pages publiées. Solution provisoire : Brevo continue de la charger, et elle reste visible sur les articles du blog. La vraie correction est de la désactiver dans Brevo, puis `python3 scripts/popup.py --remove brevo-masque`.

Pages concernées par chaque composant : dictionnaire `COMPONENTS` dans `scripts/popup.py`.

## Secrets requis (Settings → Secrets and variables → Actions)

- `WP_USER` : compte WordPress dédié (rôle Éditeur)
- `WP_APP_PASSWORD` : mot de passe d'application de ce compte
