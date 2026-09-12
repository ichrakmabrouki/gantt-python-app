"""
check_supabase.py — diagnostic rapide de la connexion Supabase.

Usage :  python check_supabase.py

Lit SUPABASE_URL / SUPABASE_KEY depuis .streamlit/secrets.toml (ou depuis les
variables d'environnement), puis verifie dans l'ordre :
  1. les secrets sont bien presents et bien formes
  2. le nom de domaine se resout (DNS)
  3. l'API REST repond

Ce script n'a besoin ni de streamlit ni de supabase-py : uniquement la
bibliotheque standard Python.
"""

import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SECRETS_PATH = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"


def read_secrets() -> dict:
    """Lit les secrets depuis secrets.toml, sinon depuis l'environnement."""
    secrets = {}
    if SECRETS_PATH.exists():
        try:
            import tomllib  # Python >= 3.11
            secrets = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  !  Lecture de {SECRETS_PATH.name} impossible : {exc}")
    for key in ("SUPABASE_URL", "SUPABASE_KEY"):
        if not secrets.get(key) and os.getenv(key):
            secrets[key] = os.getenv(key)
    return secrets


def masked(value: str, keep: int = 6) -> str:
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}...{value[-keep:]}"


def main() -> int:
    print("=" * 62)
    print("DIAGNOSTIC SUPABASE")
    print("=" * 62)

    # ── 1. Secrets ────────────────────────────────────────────────────────────
    secrets = read_secrets()
    url = str(secrets.get("SUPABASE_URL") or "").strip()
    key = str(secrets.get("SUPABASE_KEY") or "").strip()

    if not url or not key:
        print("\n[1/3] Secrets ................................. ECHEC")
        print(f"      SUPABASE_URL manquant : {not url}")
        print(f"      SUPABASE_KEY manquant : {not key}")
        print(f"\n      Cree le fichier {SECRETS_PATH} avec :")
        print('        SUPABASE_URL = "https://xxxxxxxx.supabase.co"')
        print('        SUPABASE_KEY = "<cle anon>"')
        print("\n      En ligne (Streamlit Cloud) : Settings > Secrets.")
        return 1

    host = urlparse(url).hostname or ""
    print("\n[1/3] Secrets ................................. OK")
    print(f"      URL  : {url}")
    print(f"      Cle  : {masked(key)}  ({len(key)} caracteres)")
    if SECRETS_PATH.exists():
        import time
        mtime = SECRETS_PATH.stat().st_mtime
        age_days = (time.time() - mtime) / 86400
        stamp = time.strftime("%d/%m/%Y a %H:%M", time.localtime(mtime))
        print(f"      Fichier modifie le {stamp} ({age_days:.0f} jour(s))")
        if age_days > 1:
            print("      !  Si tu viens de creer une nouvelle cle dans Supabase,")
            print("         cette date devrait etre d'aujourd'hui. Sinon, c'est que")
            print("         la nouvelle cle n'a pas ete collee/enregistree ici.")
    if not host.endswith(".supabase.co"):
        print("      !  L'URL ne ressemble pas a une URL Supabase standard.")

    # ── 2. DNS ────────────────────────────────────────────────────────────────
    try:
        ip = socket.gethostbyname(host)
        print("\n[2/3] Resolution DNS ......................... OK")
        print(f"      {host} -> {ip}")
    except socket.gaierror as exc:
        print("\n[2/3] Resolution DNS ......................... ECHEC")
        print(f"      {host} ne se resout pas ({exc})")
        print("\n      >>> C'est exactement l'erreur que l'application affiche")
        print("          sous la forme : [Errno -2] Name or service not known")
        print("\n      Causes possibles, par ordre de probabilite :")
        print("        1. Projet Supabase EN PAUSE (plan gratuit : pause")
        print("           automatique apres ~7 jours sans activite).")
        print("           -> https://supabase.com/dashboard puis 'Restore'.")
        print("        2. Projet supprime -> en recreer un et mettre a jour")
        print("           SUPABASE_URL / SUPABASE_KEY.")
        print("        3. Faute de frappe dans l'URL du projet.")
        print("        4. DNS local / VPN / pare-feu qui bloque.")
        return 2

    # ── 3. API REST ───────────────────────────────────────────────────────────
    endpoint = url.rstrip("/") + "/rest/v1/"
    request = urllib.request.Request(
        endpoint,
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15, context=ssl.create_default_context()) as resp:
            print("\n[3/3] API REST ............................... OK")
            print(f"      HTTP {resp.status} sur {endpoint}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        if exc.code in (401, 403):
            print("\n[3/3] API REST ............................... ECHEC")
            print(f"      HTTP {exc.code} : la cle SUPABASE_KEY est invalide,")
            print("      expiree, ou ne correspond pas a ce projet.")
            print("      -> Dashboard > Project Settings > API > cle 'anon public'.")
            print(f"      Reponse : {body}")
            return 3
        print("\n[3/3] API REST ............................... AVERTISSEMENT")
        print(f"      HTTP {exc.code} — le serveur repond, l'URL est donc bonne.")
        print(f"      Reponse : {body}")
    except Exception as exc:
        print("\n[3/3] API REST ............................... ECHEC")
        print(f"      {type(exc).__name__}: {exc}")
        return 3

    # ── Bonus : la table users existe-t-elle ? ────────────────────────────────
    users_endpoint = url.rstrip("/") + "/rest/v1/users?select=username&limit=1"
    request = urllib.request.Request(
        users_endpoint,
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"\n      Table 'users' accessible ({len(data)} ligne(s) lue(s)).")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        print(f"\n      !  Table 'users' : HTTP {exc.code} — {body}")
        print("         (table absente, ou bloquee par une politique RLS)")
    except Exception as exc:
        print(f"\n      !  Table 'users' : {type(exc).__name__}: {exc}")

    print("\n" + "=" * 62)
    print("Connexion Supabase operationnelle. Tu peux lancer l'application :")
    print("  streamlit run app.py")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
