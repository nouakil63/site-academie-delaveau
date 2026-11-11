#!/usr/bin/env python3
"""Crée ou met à jour un formulaire Contact Form 7 à partir de forms/<nom>.json (API REST de CF7).

Usage :
  python3 scripts/cf7_form.py forms/pre-inscription-2027-2028.json [autres.json…] [--apply]
Sans --apply : simulation, affiche ce qui serait fait sans rien modifier.

- Le formulaire est retrouvé par son titre exact (« title »). Absent : il est créé.
- Création : le destinataire et l'expéditeur de l'email sont repris du formulaire « mail_from_form »
  s'il existe, sinon l'email part à l'adresse d'administration du site.
- Mise à jour : le gabarit, le sujet, le corps, les en-têtes de l'email et les réglages supplémentaires
  sont remplacés ; le destinataire et l'expéditeur réglés dans WordPress sont conservés.

Variables d'environnement : WP_URL (optionnel), WP_USER, WP_APP_PASSWORD.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cf7_replace import call, text_of  # noqa: E402  (même authentification que cf7_replace.py)

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
DEFAULT_RECIPIENT = "[_site_admin_email]"
DEFAULT_SENDER = "[_site_title] <wordpress@academiedelaveau.com>"


def mask(value):
    # Dépôt public : les journaux des Actions sont visibles de tous.
    return EMAIL.sub("<adresse>", str(value))


def joined(value):
    return "\n".join(value) if isinstance(value, list) else (value or "")


def norm(text):
    return "\n".join(line.rstrip() for line in str(text).replace("\r\n", "\n").strip().split("\n"))


def load(path):
    spec = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    mail = dict(spec["mail"])
    mail["body"] = joined(mail.get("body"))
    return {
        "title": spec["title"],
        "locale": spec.get("locale", "fr_FR"),
        "mail_from_form": spec.get("mail_from_form"),
        "form": joined(spec["form"]),
        "mail": mail,
        "additional_settings": joined(spec.get("additional_settings")),
    }


def field_names(template):
    return set(re.findall(r"\[[a-z_]+\*?\s+([a-z0-9_-]+)", template))


def full_mail(spec_mail, recipient, sender, attachments=""):
    return {
        "active": True,
        "subject": spec_mail.get("subject", ""),
        "sender": sender,
        "recipient": recipient,
        "body": spec_mail.get("body", ""),
        "additional_headers": spec_mail.get("additional_headers", ""),
        "attachments": attachments,
        "use_html": bool(spec_mail.get("use_html", False)),
        "exclude_blank": bool(spec_mail.get("exclude_blank", False)),
    }


def report(resp):
    errors = resp.get("config_errors")
    if errors:
        print("Avertissements de Contact Form 7 :", mask(json.dumps(errors, ensure_ascii=False)))


def sync(spec, forms, apply):
    title = spec["title"]
    matches = [f for f in forms if f.get("title") == title]
    if len(matches) > 1:
        sys.exit(f"{len(matches)} formulaires nommés « {title} » : arrêt (supprimez les doublons dans WordPress).")

    if not matches:
        reference = [f for f in forms if spec["mail_from_form"] and f.get("title") == spec["mail_from_form"]]
        recipient, sender = DEFAULT_RECIPIENT, DEFAULT_SENDER
        if len(reference) == 1:
            ref_mail = call("GET", f"contact-forms/{reference[0]['id']}")["properties"].get("mail") or {}
            recipient = ref_mail.get("recipient") or recipient
            sender = ref_mail.get("sender") or sender
            origin = f"repris de « {spec['mail_from_form']} »"
        else:
            origin = "valeurs par défaut (adresse d'administration du site)"
        print(f"« {title} » n'existe pas : création. Destinataire et expéditeur : {origin} → {mask(recipient)} / {mask(sender)}.")
        if not apply:
            print("Simulation : relancer avec --apply pour créer le formulaire.")
            return
        body = {
            "title": title,
            "locale": spec["locale"],
            "form": spec["form"],
            "mail": full_mail(spec["mail"], recipient, sender),
            "additional_settings": spec["additional_settings"],
            "context": "save",
        }
        resp = call("POST", "contact-forms", body)
        form_id = resp.get("id")
        if not form_id:
            sys.exit("La création n'a pas renvoyé d'identifiant : " + mask(json.dumps(resp, ensure_ascii=False)[:400]))
        report(resp)
    else:
        form_id = matches[0]["id"]
        current = call("GET", f"contact-forms/{form_id}")
        props = current["properties"]
        mail = props.get("mail") or {}
        same = (
            norm(text_of(props.get("form"))) == norm(spec["form"])
            and norm(text_of(props.get("additional_settings"))) == norm(spec["additional_settings"])
            and norm(mail.get("body", "")) == norm(spec["mail"]["body"])
            and all(norm(mail.get(k, "")) == norm(spec["mail"].get(k, "")) for k in ("subject", "additional_headers"))
            and all(bool(mail.get(k)) == bool(spec["mail"].get(k)) for k in ("use_html", "exclude_blank"))
        )
        if same:
            print(f"« {title} » (formulaire {form_id}) est déjà à jour.")
            return
        print(f"« {title} » (formulaire {form_id}) : mise à jour du gabarit, de l'email et des réglages (destinataire et expéditeur conservés).")
        if not apply:
            print("Simulation : relancer avec --apply pour mettre à jour.")
            return
        body = {
            "form": spec["form"],
            "mail": full_mail(spec["mail"], mail.get("recipient") or DEFAULT_RECIPIENT, mail.get("sender") or DEFAULT_SENDER, mail.get("attachments", "")),
            "additional_settings": spec["additional_settings"],
            "context": "save",
        }
        report(call("POST", f"contact-forms/{form_id}", body))

    saved = call("GET", f"contact-forms/{form_id}")
    missing = field_names(spec["form"]) - field_names(text_of(saved["properties"].get("form")))
    if missing:
        sys.exit(f"Vérification échouée : champs absents du formulaire enregistré : {', '.join(sorted(missing))}.")
    print(f"OK : « {title} » est le formulaire {form_id} (shortcode [contact-form-7 title=\"{title}\"]).")


def main():
    argv = sys.argv[1:]
    apply = "--apply" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        sys.exit(__doc__)
    forms = call("GET", "contact-forms?per_page=100")
    for path in paths:
        print(f"== {path}")
        sync(load(path), forms, apply)


if __name__ == "__main__":
    main()
