"""
preparer_deploiement.py — tout ce qu'il faut faire avant de publier l'app.

Le lien que l'on envoie aux utilisateurs n'existe qu'apres deux etapes : le
code doit etre sur GitHub, et Streamlit Cloud doit savoir ou le trouver. Ce
script fait la premiere, verifie que rien ne manque pour la seconde, et affiche
le bloc de secrets a recopier.

    python preparer_deploiement.py

Il ne fait rien d'irreversible sans demander. Les secrets ne quittent jamais
cette machine : ils sont lus sur le disque et affiches dans ce terminal, nulle
part ailleurs.
"""

import re
import secrets
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent
SECRETS = RACINE / ".streamlit" / "secrets.toml"

# Adresse publique de l'application. Streamlit Cloud ne la communique a aucune
# commande locale : elle n'existe que dans son tableau de bord. On la note donc
# ici, une fois, pour qu'elle soit affichable sans aller la rechercher.
# A changer si tu renommes l'app dans Settings -> General -> App URL.
URL_PUBLIQUE = "https://gantt-python-app-hekfuuz3lvxpzaxmx3fmnx.streamlit.app/"

# Fichiers pousses : la liste est explicite, pour ne pas emporter par megarde
# la base locale, les exports ou les rapports de test.
A_POUSSER = [
    "app.py",
    "backend",
    ".streamlit/config.toml",
    ".github",
    "requirements.txt",
    "runtime.txt",
    "README.md",
    "verifier_planning.py",
    "test_reference.py",
    "test_fichiers_excel.py",
    "stress_test_solveur.py",
    "benchmark_v2.py",
    "run_all_tests.py",
    "check_supabase.py",
    "supabase_schema.sql",
    "enable_rls.sql",
    "assets",
]


def titre(texte: str) -> None:
    print(f"\n{'─' * 66}\n{texte}\n{'─' * 66}")


def git(*args: str, muet: bool = False) -> tuple[int, str]:
    try:
        r = subprocess.run(["git", *args], cwd=RACINE, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        print("git est introuvable. Installe-le depuis https://git-scm.com puis "
              "relance ce script.")
        sys.exit(1)
    sortie = (r.stdout or "") + (r.stderr or "")
    if not muet and sortie.strip():
        print(sortie.rstrip())
    return r.returncode, sortie


# ══════════════════════════════════════════════════════════════════════════════
# 1. SESSION_SECRET
# ══════════════════════════════════════════════════════════════════════════════
def verifier_session_secret() -> None:
    titre("1. Clé de signature des sessions")

    if not SECRETS.exists():
        print(f"{SECRETS} est introuvable. Crée-le d'abord avec SUPABASE_URL et "
              f"SUPABASE_KEY, puis relance.")
        sys.exit(1)

    contenu = SECRETS.read_text(encoding="utf-8")
    if re.search(r"^\s*SESSION_SECRET\s*=", contenu, re.M):
        print("SESSION_SECRET est déjà défini. Rien à faire.")
        return

    print("SESSION_SECRET est absent. Sans lui, les cookies de session sont")
    print("signés avec la clé Supabase : une rotation de cette clé déconnecterait")
    print("tous les utilisateurs d'un coup. On découple les deux.")
    if input("\nGénérer la clé et l'ajouter au fichier ? [o/N] ").strip().lower() not in ("o", "oui"):
        print("Ignoré. À faire à la main avant de déployer.")
        return

    valeur = secrets.token_urlsafe(48)
    separateur = "" if contenu.endswith("\n") else "\n"
    SECRETS.write_text(f'{contenu}{separateur}SESSION_SECRET = "{valeur}"\n',
                       encoding="utf-8")
    print("Ajoutée.")


# ══════════════════════════════════════════════════════════════════════════════
# 2. Ce qui part sur GitHub
# ══════════════════════════════════════════════════════════════════════════════
def pousser() -> bool:
    titre("2. Envoi du code sur GitHub")

    code, _ = git("rev-parse", "--is-inside-work-tree", muet=True)
    if code != 0:
        print("Ce dossier n'est pas un dépôt git.")
        return False

    # Garde-fou : le fichier de secrets ne doit JAMAIS partir.
    _, suivi = git("ls-files", ".streamlit/secrets.toml", muet=True)
    if suivi.strip():
        print("ARRÊT — .streamlit/secrets.toml est suivi par git. Il ne doit "
              "jamais être poussé.\nExécute :\n"
              "    git rm --cached .streamlit/secrets.toml\n"
              "puis relance ce script.")
        sys.exit(1)

    existants = [c for c in A_POUSSER if (RACINE / c).exists()]
    git("add", *existants)

    _, etat = git("diff", "--cached", "--stat", muet=True)
    if not etat.strip():
        print("Aucune modification à envoyer : GitHub est déjà à jour.")
        return True

    print("Fichiers qui vont être envoyés :\n")
    print(etat.rstrip())

    if input("\nEnvoyer ? [o/N] ").strip().lower() not in ("o", "oui"):
        git("reset", muet=True)
        print("Annulé, rien n'a été envoyé.")
        return False

    message = input("Message de commit [Mise a jour de l'application] : ").strip()
    git("commit", "-m", message or "Mise a jour de l'application")

    print("\nEnvoi en cours (git peut demander tes identifiants GitHub)...")
    code, _ = git("push")
    if code != 0:
        print("\nL'envoi a échoué. La cause est affichée juste au-dessus.")
        print("Si git parle d'authentification : GitHub n'accepte plus le mot de")
        print("passe du compte, il faut un jeton personnel créé dans")
        print("Settings → Developer settings → Personal access tokens.")
        return False

    print("\nCode envoyé.")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# 3. Le bloc à recopier dans Streamlit Cloud
# ══════════════════════════════════════════════════════════════════════════════
def afficher_secrets() -> None:
    titre("3. Secrets à recopier dans Streamlit Cloud")

    contenu = SECRETS.read_text(encoding="utf-8")
    gardees = [l for l in contenu.splitlines()
               if re.match(r"^\s*(SUPABASE_URL|SUPABASE_KEY|SESSION_SECRET)\s*=", l)]

    print("À coller tel quel dans Advanced settings → Secrets.")
    print("Ne partage cet écran avec personne : ces trois lignes donnent un")
    print("accès complet à la base de données.\n")
    for ligne in gardees:
        print("    " + ligne.strip())

    manquantes = {"SUPABASE_URL", "SUPABASE_KEY", "SESSION_SECRET"} - {
        l.split("=")[0].strip() for l in gardees}
    if manquantes:
        print(f"\nATTENTION — il manque : {', '.join(sorted(manquantes))}. "
              f"L'application ne démarrera pas en ligne sans ces valeurs.")


def marche_a_suivre() -> None:
    titre("4. Créer l'application et récupérer le lien")
    code, url = git("remote", "get-url", "origin", muet=True)
    depot = (url.strip().replace("https://github.com/", "").removesuffix(".git")
             if code == 0 else "ton-compte/ton-depot")

    print(f"""
  1. Ouvre https://share.streamlit.io et connecte-toi avec GitHub.
  2. Bouton « Create app » → « Deploy a public app from GitHub ».
  3. Remplis :
        Repository      {depot or 'ton depot'}
        Branch          main
        Main file path  app.py
  4. Advanced settings → Python version : 3.11
     Advanced settings → Secrets : colle les trois lignes de l'étape 3.
  5. Deploy. Le premier build dure 5 à 15 minutes — ortools est lourd.

  Tu obtiens alors une adresse en .streamlit.app : c'est LE lien à envoyer.
  Il fonctionne depuis n'importe quel appareil, ton PC éteint.

  Ensuite, les mises à jour sont automatiques : relancer ce script suffit,
  Streamlit Cloud redéploie tout seul à chaque envoi sur GitHub.
""")


def afficher_lien() -> None:
    titre("Le lien à envoyer aux utilisateurs")
    print(f"\n    {URL_PUBLIQUE}\n")
    print("Il fonctionne depuis n'importe quel appareil, ton PC éteint.")


if __name__ == "__main__":
    if "--lien" in sys.argv:          # python preparer_deploiement.py --lien
        print(URL_PUBLIQUE)
        sys.exit(0)


    print("Préparation du déploiement — " + str(RACINE))
    verifier_session_secret()
    pousser()
    afficher_secrets()
    # L'application existe deja : on affiche son adresse. La marche a suivre
    # pour en creer une reste accessible avec --creer, si elle doit etre
    # recreee un jour.
    if "--creer" in sys.argv:
        marche_a_suivre()
    else:
        afficher_lien()
