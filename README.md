# Site Académie Delaveau

Le HTML des pages de https://www.academiedelaveau.com est versionné ici et publié automatiquement sur WordPress.

## Fonctionnement

- `pages/<slug>.html` : contenu brut de chaque page WordPress.
- `pages/manifest.json` : identifiant WordPress de chaque page et date de dernière modification connue. Ne pas modifier à la main.
- À chaque push sur `main` qui modifie un `pages/*.html`, l'Action **Publier sur WordPress** envoie les pages modifiées (et seulement elles).
- Avant d'envoyer, elle vérifie les `<script>` des pages (`scripts/check_inline_scripts.py`) : à l'affichage, WordPress prend tout « < » pour le début d'une balise et y remplace les « & » par `&#038;`, ce qui casse le script. Dans un script de page, écrire `b > a` plutôt que `a < b`.

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

- **menu-saison** — remplace le libellé « Pré-inscription 2026 » du bouton du menu (extension `adl_smart_menu`) par « Pré-inscription 2027-2028 », sur toutes les pages publiées. À changer dans `LABEL` à chaque nouvelle saison ; la vraie correction est dans l'extension du menu.

Pages concernées par chaque composant : dictionnaire `COMPONENTS` dans `scripts/popup.py`.

## Formulaire de pré-inscription

La page `pre-inscription-2027-2028` contient son propre formulaire en 4 étapes (HTML, style et script dans la page ; il remplace l'extension `[preinscription_academie]`).

- Les boutons restent toujours actifs : s'il manque une information, la liste des champs à compléter s'affiche sous les boutons.
- L'envoi passe par le formulaire Contact Form 7 « Pré-inscription 2027-2028 », présent sur la page mais invisible. Chaque demande est enregistrée dans **admin WordPress → Flamingo → Messages entrants** (les demandes classées comme spam par reCAPTCHA sont dans l'onglet *Indésirables*) et envoyée par email.
- Ce formulaire CF7 est défini dans `forms/pre-inscription-2027-2028.json` (gabarit, email, réglages Flamingo). Il est créé ou mis à jour automatiquement par l'Action **Publier sur WordPress** quand ce fichier change, avant la publication des pages : si la création échoue, la page n'est pas publiée. Le destinataire et l'expéditeur de l'email se règlent dans WordPress (onglet *E-mail* du formulaire) et ne sont jamais écrasés ; à la création, ils sont repris du formulaire « Inscriptions stage 2026 ».
- Ajouter un champ : l'ajouter dans la page **et** dans `forms/pre-inscription-2027-2028.json` (même `name`), dans le même commit.
- Ne pas modifier le gabarit de ce formulaire dans WordPress : il serait remplacé à la prochaine publication.

## Modifier un formulaire Contact Form 7

Actions → **Modifier un formulaire Contact Form 7** → Run workflow : titre du formulaire, texte à remplacer, nouveau texte.
Laisser « appliquer » décoché pour une simulation (affiche le passage trouvé), puis relancer en cochant. Seul le gabarit du formulaire change (mails et réglages Stripe intacts).

## Renommer une page (changer son adresse)

Actions → **Renommer une page** → Run workflow : ancienne adresse, nouvelle adresse, nouveau titre.
Avec « redirection » coché, une page à l'ancienne adresse renvoie vers la nouvelle (WordPress ne le fait pas pour les pages). Le dépôt est mis à jour automatiquement ; penser ensuite à remplacer les liens dans les pages.

## Secrets requis (Settings → Secrets and variables → Actions)

- `WP_USER` : compte WordPress dédié (rôle Éditeur)
- `WP_APP_PASSWORD` : mot de passe d'application de ce compte
