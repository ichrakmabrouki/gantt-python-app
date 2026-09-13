"""
run_all_tests.py — batterie de tests complete, sans argument.

Lancer avec le bouton Run de VS Code, ou :
    python run_all_tests.py

Ecrit un rapport lisible dans RAPPORT_TESTS.md (mis a jour au fil de l'eau,
donc consultable meme si le script tourne encore).
"""

import io
import json
import os
import platform
import socket
import ssl
import sys
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
RAPPORT = RACINE / "RAPPORT_TESTS.md"

# Budget de temps du solveur selon la taille, pour que la campagne complete
# reste sous ~6 minutes.
BUDGET_SOLVEUR = [
    ("dataset_01_08pieces_cte10.xlsx", 20.0),
    ("dataset_02_12pieces_cte12.xlsx", 20.0),
    ("dataset_03_20pieces_cte15.xlsx", 20.0),
    ("dataset_04_25pieces_cte15.xlsx", 30.0),
    ("dataset_05_35pieces_cte18.xlsx", 30.0),
    ("dataset_06_45pieces_cte20.xlsx", 30.0),
    ("dataset_07_60pieces_cte22.xlsx", 45.0),
    ("dataset_08_75pieces_cte25.xlsx", 45.0),
    ("dataset_09_90pieces_cte28.xlsx", 45.0),
    ("dataset_10_100pieces_cte30.xlsx", 60.0),
]

_lignes: list[str] = []
_resultats: list[tuple[str, str, str]] = []   # (niveau, nom, statut)


def ecrire(ligne: str = "") -> None:
    """Ajoute au rapport, l'affiche, et sauvegarde immediatement."""
    _lignes.append(ligne)
    try:
        print(ligne)
    except Exception:
        print(ligne.encode("ascii", "replace").decode("ascii"))
    try:
        RAPPORT.write_text("\n".join(_lignes) + "\n", encoding="utf-8")
    except Exception:
        pass


def noter(niveau: str, nom: str, statut: str) -> None:
    _resultats.append((niveau, nom, statut))


def titre(texte: str) -> None:
    ecrire()
    ecrire(f"## {texte}")
    ecrire()


# ══════════════════════════════════════════════════════════════════════════════
# 1. ENVIRONNEMENT
# ══════════════════════════════════════════════════════════════════════════════
def test_environnement() -> None:
    titre("1. Environnement")

    ecrire(f"- Python : `{sys.version.split()[0]}` ({platform.architecture()[0]})")
    ecrire(f"- Systeme : {platform.system()} {platform.release()}")
    ecrire(f"- Dossier : `{RACINE}`")
    ecrire()

    if sys.version_info[:2] != (3, 11):
        ecrire(f"> Attention : le projet cible Python 3.11, "
               f"tu es en {sys.version_info.major}.{sys.version_info.minor}.")
        ecrire()

    ecrire("| Paquet | Version | Statut |")
    ecrire("|---|---|---|")
    paquets = ["streamlit", "pandas", "plotly", "openpyxl", "supabase",
               "PIL", "extra_streamlit_components", "ortools"]
    manquants = []
    for nom in paquets:
        try:
            mod = __import__(nom)
            version = getattr(mod, "__version__", "n/a")
            ecrire(f"| {nom} | {version} | OK |")
        except Exception as exc:
            manquants.append(nom)
            ecrire(f"| {nom} | — | ABSENT ({type(exc).__name__}) |")

    noter("1. Environnement", "Dependances installees",
          "OK" if not manquants else f"ECHEC ({', '.join(manquants)})")


# ══════════════════════════════════════════════════════════════════════════════
# 2. MODULES DU PROJET
# ══════════════════════════════════════════════════════════════════════════════
def test_imports_projet() -> None:
    titre("2. Modules du projet")

    modules = [
        "backend.converter",
        "backend.data_processor",
        "backend.database",
        "backend.gantt_builder",
        "backend.kpi_calculator",
        "backend.solver.input_parser",
        "backend.solver.model",
        "verifier_planning",
    ]
    ecrire("| Module | Statut |")
    ecrire("|---|---|")
    echecs = []
    for nom in modules:
        try:
            __import__(nom)
            ecrire(f"| `{nom}` | OK |")
        except Exception as exc:
            echecs.append(nom)
            ecrire(f"| `{nom}` | ECHEC — {type(exc).__name__}: {exc} |")

    noter("2. Modules", "Import de tous les modules",
          "OK" if not echecs else f"ECHEC ({len(echecs)})")


# ══════════════════════════════════════════════════════════════════════════════
# 3. CONNEXION SUPABASE
# ══════════════════════════════════════════════════════════════════════════════
def test_supabase() -> None:
    titre("3. Connexion Supabase")

    try:
        from check_supabase import read_secrets
        secrets = read_secrets()
    except Exception as exc:
        ecrire(f"Lecture des secrets impossible : {type(exc).__name__}: {exc}")
        noter("3. Supabase", "Lecture des secrets", "ECHEC")
        return

    url = str(secrets.get("SUPABASE_URL") or "").strip()
    cle = str(secrets.get("SUPABASE_KEY") or "").strip()
    if not url or not cle:
        ecrire("SUPABASE_URL ou SUPABASE_KEY manquant dans secrets.toml.")
        noter("3. Supabase", "Secrets presents", "ECHEC")
        return

    ecrire(f"- URL : `{url}`")
    ecrire(f"- Cle : `{cle[:6]}...{cle[-6:]}` ({len(cle)} caracteres)")
    ecrire(f"- SESSION_SECRET defini : "
           f"{'oui' if secrets.get('SESSION_SECRET') else 'NON (voir remarque)'}")
    noter("3. Supabase", "Secrets presents", "OK")

    hote = urlparse(url).hostname or ""
    try:
        ip = socket.gethostbyname(hote)
        ecrire(f"- DNS : `{hote}` -> `{ip}`")
        noter("3. Supabase", "Resolution DNS", "OK")
    except Exception as exc:
        ecrire(f"- DNS : ECHEC ({exc})")
        noter("3. Supabase", "Resolution DNS", "ECHEC")
        return

    def appel(chemin: str):
        req = urllib.request.Request(
            url.rstrip("/") + chemin,
            headers={"apikey": cle, "Authorization": f"Bearer {cle}"},
        )
        return urllib.request.urlopen(req, timeout=20,
                                      context=ssl.create_default_context())

    try:
        with appel("/rest/v1/") as rep:
            ecrire(f"- API REST : HTTP {rep.status}")
        noter("3. Supabase", "API REST joignable", "OK")
    except Exception as exc:
        ecrire(f"- API REST : ECHEC — {type(exc).__name__}: {exc}")
        noter("3. Supabase", "API REST joignable", "ECHEC")
        return

    ecrire()
    ecrire("| Table | Statut |")
    ecrire("|---|---|")
    tables = ["users", "operations", "jobs", "kpis", "prix",
              "planning_jours", "app_access_logs"]
    absentes = []
    for table in tables:
        try:
            with appel(f"/rest/v1/{table}?select=*&limit=1") as rep:
                donnees = json.loads(rep.read().decode("utf-8"))
                ecrire(f"| `{table}` | OK ({len(donnees)} ligne lue) |")
        except urllib.error.HTTPError as exc:
            corps = exc.read().decode("utf-8", "replace")[:110]
            absentes.append(table)
            ecrire(f"| `{table}` | HTTP {exc.code} — {corps} |")
        except Exception as exc:
            absentes.append(table)
            ecrire(f"| `{table}` | ECHEC — {type(exc).__name__} |")

    noter("3. Supabase", "Tables accessibles",
          "OK" if not absentes else f"PARTIEL ({', '.join(absentes)})")


# ══════════════════════════════════════════════════════════════════════════════
# 4. LECTURE DES FICHIERS EXCEL
# ══════════════════════════════════════════════════════════════════════════════
def test_parsing() -> dict:
    titre("4. Lecture et validation des fichiers Excel")

    from backend.solver.input_parser import parse_excel_to_dict, validate_excel_data

    dossier = RACINE / "generated_test_excels"
    if not dossier.exists():
        ecrire(f"Dossier introuvable : `{dossier}`")
        noter("4. Parsing", "Dossier de datasets", "ECHEC")
        return {}

    ecrire("| Dataset | Pieces | Operations | Machines | cte | Somme durees | Horizon | Valide |")
    ecrire("|---|---|---|---|---|---|---|---|")

    donnees, echecs = {}, 0
    for nom, _ in BUDGET_SOLVEUR:
        chemin = dossier / nom
        if not chemin.exists():
            ecrire(f"| {nom} | — | — | — | — | — | — | FICHIER ABSENT |")
            echecs += 1
            continue
        try:
            data = parse_excel_to_dict(str(chemin))
            ok, msg = validate_excel_data(data)
            p = data["params"]
            somme = sum(data["pt"].values())
            horizon = somme + data["cte"] * p["nbOps"] * 2
            nb_machines = len({m for _, m in data["modes"]})
            ecrire(f"| {nom.replace('.xlsx','')} | {p['nbJobs']} | {p['nbOps']} | "
                   f"{nb_machines} | {data['cte']} | {somme} | {horizon} | "
                   f"{'oui' if ok else 'NON — ' + msg} |")
            if ok:
                donnees[nom] = data
            else:
                echecs += 1
        except Exception as exc:
            ecrire(f"| {nom.replace('.xlsx','')} | — | — | — | — | — | — | "
                   f"ERREUR {type(exc).__name__} |")
            echecs += 1

    noter("4. Parsing", f"Lecture des {len(BUDGET_SOLVEUR)} datasets",
          "OK" if echecs == 0 else f"ECHEC ({echecs})")

    horizons = [sum(d["pt"].values()) + d["cte"] * d["params"]["nbOps"] * 2
                for d in donnees.values()]
    if horizons:
        depassements = [h for h in horizons if h > 10000]
        ecrire()
        ecrire(f"> Rappel : {len(depassements)} dataset(s) ont un horizon superieur "
               f"a 10000, l'ancienne valeur de `M_big` codee en dur. "
               f"Horizon maximal observe : {max(horizons)}.")

    return donnees


# ══════════════════════════════════════════════════════════════════════════════
# 5. SOLVEUR + VALIDITE DU PLANNING
# ══════════════════════════════════════════════════════════════════════════════
def test_solveur(donnees: dict) -> None:
    titre("5. Solveur et validite des plannings")

    if not donnees:
        ecrire("Aucun dataset exploitable, etape ignoree.")
        noter("5. Solveur", "Resolution", "IGNORE")
        return

    from backend.solver.model import solve_flexible_jobshop
    from verifier_planning import verifier_planning

    ecrire("| Dataset | Budget | Temps reel | Operations | Makespan | Planning valide |")
    ecrire("|---|---|---|---|---|---|")

    resolus, valides, details = 0, 0, []
    for nom, budget in BUDGET_SOLVEUR:
        data = donnees.get(nom)
        if data is None:
            continue

        court = nom.replace(".xlsx", "").replace("dataset_", "")
        depart = time.time()
        sortie = io.StringIO()
        vrai_stdout = sys.stdout
        try:
            sys.stdout = sortie            # le solveur print son makespan
            df = solve_flexible_jobshop(data, max_time_seconds=budget)
            sys.stdout = vrai_stdout
            duree = time.time() - depart
            resolus += 1

            violations = verifier_planning(data, df)
            makespan = int(df["EndTime"].max()) if len(df) else 0
            if violations:
                details.append((court, violations))
                verdict = f"NON — {len(violations)} violation(s)"
            else:
                valides += 1
                verdict = "oui"

            ecrire(f"| {court} | {budget:.0f} s | {duree:.1f} s | {len(df)} | "
                   f"{makespan} min | {verdict} |")
        except Exception as exc:
            sys.stdout = vrai_stdout
            duree = time.time() - depart
            ecrire(f"| {court} | {budget:.0f} s | {duree:.1f} s | — | — | "
                   f"ECHEC {type(exc).__name__}: {str(exc)[:60]} |")

    total = len([n for n, _ in BUDGET_SOLVEUR if n in donnees])
    noter("5. Solveur", f"Resolution ({resolus}/{total})",
          "OK" if resolus == total else f"PARTIEL ({resolus}/{total})")
    noter("5. Solveur", f"Plannings valides ({valides}/{resolus})",
          "OK" if valides == resolus and resolus else f"ECHEC ({valides}/{resolus})")

    if details:
        ecrire()
        ecrire("### Violations detectees")
        ecrire()
        for court, violations in details:
            ecrire(f"**{court}** — {len(violations)} violation(s) :")
            ecrire()
            for v in violations[:8]:
                ecrire(f"- {v}")
            if len(violations) > 8:
                ecrire(f"- ... et {len(violations) - 8} autre(s)")
            ecrire()


# ══════════════════════════════════════════════════════════════════════════════
# 6. VERIFICATEUR DE PLANNING (auto-test)
# ══════════════════════════════════════════════════════════════════════════════
def test_verificateur() -> None:
    titre("6. Auto-test du verificateur")

    ecrire("Le verificateur est lui-meme teste : un planning correct doit passer, "
           "neuf plannings volontairement fautifs doivent etre rejetes.")
    ecrire()

    import pandas as pd
    from verifier_planning import verifier_planning

    data = {
        "cte": 10, "params": {"nbOps": 4},
        "gammes": [(1, 1, 1), (2, 1, 2), (3, 2, 1), (4, 2, 2)],
        "modes": [(1, 1), (2, 2), (3, 1), (4, 2)],
        "pt": {(1, 1): 30, (2, 2): 20, (3, 1): 25, (4, 2): 15},
        "grp_mchs": [(1, 1), (1, 2)],
    }

    def plan(lignes):
        return pd.DataFrame([
            dict(OperationID=o, MachineID=m, StartTime=s, EndTime=e, Duration=d)
            for o, m, s, e, d in lignes
        ])

    # Planning de reference : valide pour TOUTES les contraintes, y compris les
    # setups du technicien 1 qui couvre les deux machines.
    #   setups technicien : [0,10] [40,50] [50,60] [80,90]  -> disjoints
    #   machine 1 : blocs [0,40] et [40,75]                  -> disjoints
    #   machine 2 : blocs [50,80] et [80,105]                -> disjoints
    bon = [(1, 1, 10, 40, 30), (3, 1, 50, 75, 25), (2, 2, 60, 80, 20), (4, 2, 90, 105, 15)]
    cas = [
        ("Planning correct", bon, False),
        ("Chevauchement machine", [(1, 1, 10, 40, 30), (3, 1, 35, 60, 25), (2, 2, 60, 80, 20), (4, 2, 90, 105, 15)], True),
        ("Setup cte non respecte", [(1, 1, 10, 40, 30), (3, 1, 45, 70, 25), (2, 2, 60, 80, 20), (4, 2, 90, 105, 15)], True),
        ("Precedence violee", [(1, 1, 10, 40, 30), (3, 1, 50, 75, 25), (2, 2, 20, 40, 20), (4, 2, 90, 105, 15)], True),
        ("Duree incorrecte", [(1, 1, 10, 40, 99), (3, 1, 50, 75, 25), (2, 2, 60, 80, 20), (4, 2, 90, 105, 15)], True),
        ("Machine non autorisee", [(1, 2, 10, 40, 30), (3, 1, 50, 75, 25), (2, 2, 60, 80, 20), (4, 2, 90, 105, 15)], True),
        ("Demarrage avant cte", [(1, 1, 2, 32, 30), (3, 1, 50, 75, 25), (2, 2, 60, 80, 20), (4, 2, 90, 105, 15)], True),
        ("Operation manquante", [(1, 1, 10, 40, 30), (3, 1, 50, 75, 25), (2, 2, 60, 80, 20)], True),
        ("Technicien sur deux setups a la fois", [(1, 1, 10, 40, 30), (3, 1, 50, 75, 25), (2, 2, 55, 75, 20), (4, 2, 90, 105, 15)], True),
        ("Changement de machine sans cte", [(1, 1, 10, 40, 30), (3, 1, 50, 75, 25), (2, 2, 40, 60, 20), (4, 2, 90, 105, 15)], True),
    ]

    ecrire("| Scenario | Violations detectees | Attendu | Resultat |")
    ecrire("|---|---|---|---|")
    reussis = 0
    for nom, lignes, doit_echouer in cas:
        n = len(verifier_planning(data, plan(lignes)))
        ok = (n >= 1) if doit_echouer else (n == 0)
        reussis += ok
        ecrire(f"| {nom} | {n} | {'>= 1' if doit_echouer else '0'} | "
               f"{'OK' if ok else 'ECHEC'} |")

    noter("6. Verificateur", f"Auto-test ({reussis}/{len(cas)})",
          "OK" if reussis == len(cas) else f"ECHEC ({reussis}/{len(cas)})")


# ══════════════════════════════════════════════════════════════════════════════
# 7. KPI
# ══════════════════════════════════════════════════════════════════════════════
def test_kpi() -> None:
    titre("7. Calcul des KPI")

    import pandas as pd
    from backend.kpi_calculator import compute_kpis, summary_by_machine, summary_by_job

    df = pd.DataFrame([
        dict(OperationID=1, MachineID=1, MachineLabel="Machine 1", JobID=1,
             JobLabel="Job 1", StartTime=10, EndTime=70, Duration=60),
        dict(OperationID=2, MachineID=2, MachineLabel="Machine 2", JobID=1,
             JobLabel="Job 1", StartTime=80, EndTime=120, Duration=40),
        dict(OperationID=3, MachineID=1, MachineLabel="Machine 1", JobID=2,
             JobLabel="Job 2", StartTime=75, EndTime=135, Duration=60),
    ])
    try:
        k = compute_kpis(df, {1: 2.5, 2: 3.0})
        profit_total = float(k["Profit"].sum())
        attendu = 60 * 2.5 + 40 * 2.5 + 60 * 3.0     # 430.0
        m = summary_by_machine(k)
        j = summary_by_job(k)

        ecrire(f"- Profit total calcule : **{profit_total}** (attendu {attendu})")
        ecrire(f"- Recapitulatif par machine : {len(m)} ligne(s)")
        ecrire(f"- Recapitulatif par piece : {len(j)} ligne(s)")
        ecrire(f"- Charge machine 1 : {int(m.loc[m.MachineLabel == 'Machine 1', 'Charge_min'].iloc[0])} min (attendu 120)")

        ok = abs(profit_total - attendu) < 0.01 and len(m) == 2 and len(j) == 2
        noter("7. KPI", "Profit et recapitulatifs", "OK" if ok else "ECHEC")
    except Exception as exc:
        ecrire(f"ECHEC — {type(exc).__name__}: {exc}")
        noter("7. KPI", "Profit et recapitulatifs", "ECHEC")


# ══════════════════════════════════════════════════════════════════════════════
# 8. SECURITE : MOTS DE PASSE ET JETONS
# ══════════════════════════════════════════════════════════════════════════════
def test_securite() -> None:
    titre("8. Securite : mots de passe et jetons de session")

    try:
        os.environ.setdefault("SESSION_SECRET", "secret-de-test-pour-run-all-tests")
        from backend.database import (hash_password, verify_password,
                                      create_session_token, verify_session_token,
                                      should_refresh_session_token,
                                      SESSION_DURATION_DAYS)
    except Exception as exc:
        ecrire(f"Import impossible : {type(exc).__name__}: {exc}")
        noter("8. Securite", "Import", "ECHEC")
        return

    ecrire("| Test | Resultat |")
    ecrire("|---|---|")
    reussis, total = 0, 0

    def verifier(nom: str, condition: bool) -> None:
        nonlocal reussis, total
        total += 1
        reussis += bool(condition)
        ecrire(f"| {nom} | {'OK' if condition else 'ECHEC'} |")

    try:
        h = hash_password("MotDePasse123")
        verifier("Le hash n'est pas le mot de passe en clair", "MotDePasse123" not in h)
        verifier("Format PBKDF2 avec sel", h.startswith("pbkdf2_sha256$200000$"))
        verifier("Deux hash du meme mot de passe different (sel)",
                 hash_password("MotDePasse123") != h)
        verifier("Bon mot de passe accepte", verify_password("MotDePasse123", h))
        verifier("Mauvais mot de passe refuse", not verify_password("MotDePasse124", h))
        verifier("Mot de passe vide refuse", not verify_password("", h))
    except Exception as exc:
        ecrire(f"| Hachage | ECHEC — {type(exc).__name__}: {exc} |")

    try:
        from datetime import timedelta, timezone
        maintenant = datetime.now(timezone.utc)
        jeton = create_session_token("alice")
        verifier("Jeton valide relu correctement", verify_session_token(jeton) == "alice")
        verifier("Jeton neuf non renouvele", not should_refresh_session_token(jeton))

        proche = create_session_token("alice", maintenant + timedelta(days=2))
        verifier("Jeton proche de l'expiration -> renouvellement",
                 should_refresh_session_token(proche))

        expire = create_session_token("alice", maintenant - timedelta(days=1))
        verifier("Jeton expire refuse", verify_session_token(expire) is None)

        import base64
        brut = base64.urlsafe_b64decode(jeton).decode().replace("alice", "admin")
        falsifie = base64.urlsafe_b64encode(brut.encode()).decode()
        verifier("Jeton falsifie (alice -> admin) refuse",
                 verify_session_token(falsifie) is None)
        verifier("Jeton vide refuse", verify_session_token("") is None)
        verifier("Jeton n'importe quoi refuse", verify_session_token("abc123") is None)
    except Exception as exc:
        ecrire(f"| Jetons | ECHEC — {type(exc).__name__}: {exc} |")

    noter("8. Securite", f"Mots de passe et jetons ({reussis}/{total})",
          "OK" if reussis == total else f"ECHEC ({reussis}/{total})")


# ══════════════════════════════════════════════════════════════════════════════
# 9. ROBUSTESSE
# ══════════════════════════════════════════════════════════════════════════════
def test_robustesse() -> None:
    titre("9. Robustesse : entrees invalides")

    ecrire("Chaque cas doit produire une erreur **explicite**, jamais un plantage muet.")
    ecrire()
    ecrire("| Cas | Comportement |")
    ecrire("|---|---|")

    from backend.solver.input_parser import parse_excel_to_dict, validate_excel_data
    reussis, total = 0, 0

    def verifier(nom: str, fonction) -> None:
        nonlocal reussis, total
        total += 1
        try:
            fonction()
            ecrire(f"| {nom} | ECHEC — aucune erreur levee |")
        except Exception as exc:
            message = str(exc)[:70].replace("|", "/").replace("\n", " ")
            reussis += 1
            ecrire(f"| {nom} | OK — {type(exc).__name__}: {message} |")

    faux = RACINE / "_faux_fichier_test.xlsx"
    try:
        faux.write_text("ceci n'est pas un classeur Excel", encoding="utf-8")
        verifier("Fichier texte renomme en .xlsx",
                 lambda: parse_excel_to_dict(str(faux)))
    finally:
        try:
            faux.unlink()
        except Exception:
            pass

    verifier("Fichier inexistant",
             lambda: parse_excel_to_dict(str(RACINE / "_nexiste_pas.xlsx")))

    # validate_excel_data doit renvoyer False, pas lever
    total += 1
    try:
        data = {"params": {"nbOps": 99, "nbMchs": 3}, "gammes": [(1, 1, 1)],
                "modes": [(1, 1)], "pt": {(1, 1): 10}, "grp_mchs": [(1, 1)]}
        ok, msg = validate_excel_data(data)
        if not ok:
            reussis += 1
            ecrire(f"| nbOps incoherent avec GAMMES | OK — \"{msg[:60]}\" |")
        else:
            ecrire("| nbOps incoherent avec GAMMES | ECHEC — declare valide |")
    except Exception as exc:
        ecrire(f"| nbOps incoherent avec GAMMES | ECHEC — exception {type(exc).__name__} |")

    total += 1
    try:
        data = {"params": {"nbOps": 1, "nbMchs": 3}, "gammes": [(1, 1, 1)],
                "modes": [(1, 2)], "pt": {(1, 2): 10}, "grp_mchs": []}
        ok, msg = validate_excel_data(data)
        if not ok and "technicien" in msg.lower():
            reussis += 1
            ecrire(f"| Machine sans technicien | OK — \"{msg[:60]}\" |")
        else:
            ecrire(f"| Machine sans technicien | ECHEC — \"{msg[:60]}\" |")
    except Exception as exc:
        ecrire(f"| Machine sans technicien | ECHEC — exception {type(exc).__name__} |")

    noter("9. Robustesse", f"Entrees invalides ({reussis}/{total})",
          "OK" if reussis == total else f"PARTIEL ({reussis}/{total})")


# ══════════════════════════════════════════════════════════════════════════════
# SYNTHESE
# ══════════════════════════════════════════════════════════════════════════════
def synthese(depart: float) -> None:
    ecrire()
    ecrire("---")
    titre("Synthese")

    ecrire("| Etape | Test | Resultat |")
    ecrire("|---|---|---|")
    for niveau, nom, statut in _resultats:
        ecrire(f"| {niveau} | {nom} | **{statut}** |")

    oks = sum(1 for _, _, s in _resultats if s == "OK")
    ecrire()
    ecrire(f"**{oks} / {len(_resultats)} tests au vert** — "
           f"campagne terminee en {time.time() - depart:.0f} secondes.")
    ecrire()
    ecrire(f"Rapport genere le {datetime.now().strftime('%d/%m/%Y a %H:%M:%S')}.")


def main() -> int:
    depart = time.time()
    _lignes.clear()
    ecrire("# Rapport de tests — application Gantt")
    ecrire()
    ecrire(f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M:%S')}")

    etapes = [
        ("environnement", test_environnement),
        ("modules", test_imports_projet),
        ("supabase", test_supabase),
        ("verificateur", test_verificateur),
        ("kpi", test_kpi),
        ("securite", test_securite),
        ("robustesse", test_robustesse),
    ]
    for nom, fonction in etapes:
        try:
            fonction()
        except Exception:
            ecrire()
            ecrire(f"Etape `{nom}` interrompue :")
            ecrire("```")
            ecrire(traceback.format_exc()[:1500])
            ecrire("```")
            noter(nom, "Execution de l'etape", "ECHEC")

    # Parsing et solveur en dernier : ce sont les plus longs.
    try:
        donnees = test_parsing()
    except Exception:
        ecrire("```")
        ecrire(traceback.format_exc()[:1500])
        ecrire("```")
        donnees = {}
        noter("4. Parsing", "Execution de l'etape", "ECHEC")

    try:
        test_solveur(donnees)
    except Exception:
        ecrire("```")
        ecrire(traceback.format_exc()[:1500])
        ecrire("```")
        noter("5. Solveur", "Execution de l'etape", "ECHEC")

    synthese(depart)
    print(f"\n>>> Rapport complet ecrit dans : {RAPPORT}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
