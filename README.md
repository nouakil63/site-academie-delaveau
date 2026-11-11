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
- L'envoi passe par l'extension **Pré-inscriptions Académie Delaveau** (voir plus bas) : chaque demande arrive dans **admin WordPress → Pré-inscriptions** et par email.
- Ajouter un champ : l'ajouter dans la page avec un `name`, et dans la liste `fields()` de l'extension (`wordpress/adl-preinscriptions/adl-preinscriptions.php`) pour qu'il soit enregistré, puis mettre l'extension à jour dans WordPress.
- Les candidatures reçues avant l'installation de l'extension (11 novembre 2026) sont dans **Flamingo → Messages entrants** (formulaire « Pré-inscription 2027-2028 ») et dans les emails ; ce formulaire Contact Form 7 n'est plus utilisé.

## Extension « Pré-inscriptions Académie Delaveau » (`wordpress/adl-preinscriptions/`)

Reçoit les candidatures envoyées par la page (`POST /wp-json/adl/v1/preinscription`) et les range dans l'admin.

- **Installer ou mettre à jour** (une fois, par un administrateur ; le compte utilisé par GitHub ne peut pas installer d'extension) : compresser le dossier `wordpress/adl-preinscriptions` en `adl-preinscriptions.zip`, puis admin WordPress → Extensions → Ajouter → Téléverser une extension → Activer. Pour une mise à jour, WordPress propose de remplacer la version installée.
- **Candidatures** : menu *Pré-inscriptions*. Liste (parcours, contact, âge, niveau, date), filtre par parcours, fiche complète, bouton *Exporter en CSV (Excel)*. Visible des administrateurs et des éditeurs uniquement.
- **Email** à chaque candidature, avec réponse directe au candidat. Destinataires : *Pré-inscriptions → Réglages* (à l'activation, repris du formulaire CF7 de pré-inscription).
- **Anti-spam** : champ piège invisible, reCAPTCHA (clé déjà enregistrée dans Contact Form 7), 30 candidatures maximum par heure et par connexion. Rien n'est jeté : une demande douteuse est marquée « À vérifier » (sans email si le piège à robots a été rempli).
- Désactiver ou supprimer l'extension ne supprime aucune candidature.

## Modifier un formulaire Contact Form 7

Actions → **Modifier un formulaire Contact Form 7** → Run workflow : titre du formulaire, texte à remplacer, nouveau texte.
Laisser « appliquer » décoché pour une simulation (affiche le passage trouvé), puis relancer en cochant. Seul le gabarit du formulaire change (mails et réglages Stripe intacts).

## Renommer une page (changer son adresse)

Actions → **Renommer une page** → Run workflow : ancienne adresse, nouvelle adresse, nouveau titre.
Avec « redirection » coché, une page à l'ancienne adresse renvoie vers la nouvelle (WordPress ne le fait pas pour les pages). Le dépôt est mis à jour automatiquement ; penser ensuite à remplacer les liens dans les pages.

## Secrets requis (Settings → Secrets and variables → Actions)

- `WP_USER` : compte WordPress dédié (rôle Éditeur)
- `WP_APP_PASSWORD` : mot de passe d'application de ce compte
