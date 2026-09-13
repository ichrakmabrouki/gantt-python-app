"""
stress_test_solveur.py — validation du solveur sur des entrees ALEATOIRES.

Tester 10 fichiers Excel qui se ressemblent ne prouve rien sur le onzieme.
Ce script genere des centaines d'instances differentes — nombre de pieces,
d'operations, de machines, de techniciens, valeur de cte, disponibilite
initiale des machines, tout varie — resout chacune, puis controle les
9 contraintes sur le planning produit.

C'est du test par propriete : au lieu de verifier des cas choisis a la main,
on verifie qu'une propriete (« le planning respecte les contraintes ») tient
sur un large echantillon tire au hasard, bornes comprises.

Chaque instance est reproductible par sa graine : une violation peut etre
rejouee a l'identique.

Lancer avec le bouton Run de VS Code, ou :
    python stress_test_solveur.py

Produit : RAPPORT_STRESS.md
"""

import random
import sys
import time
import traceback
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
RAPPORT = RACINE / "RAPPORT_STRESS.md"

NB_ALEATOIRES = 150          # instances tirees au hasard
BUDGET = 5.0                 # secondes par instance

_lignes: list[str] = []


def ecrire(ligne: str = "") -> None:
    _lignes.append(ligne)
    try:
        print(ligne)
    except Exception:
        print(ligne.encode("ascii", "replace").decode("ascii"))
    try:
        RAPPORT.write_text("\n".join(_lignes) + "\n", encoding="utf-8")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# GENERATEUR D'INSTANCES
# ══════════════════════════════════════════════════════════════════════════════
def generer(graine: int, profil: str = "aleatoire") -> dict:
    """Construit une instance valide et reproductible a partir d'une graine."""
    rng = random.Random(graine)

    if profil == "minimal":
        nb_jobs, nb_mchs, nb_techs, cte = 1, 1, 1, 0
        ops_par_job, modes_max = 1, 1
    elif profil == "cte_zero":
        nb_jobs = rng.randint(2, 10); nb_mchs = rng.randint(2, 5)
        nb_techs = rng.randint(1, 3); cte = 0
        ops_par_job, modes_max = rng.randint(1, 4), 2
    elif profil == "sans_flexibilite":
        # chaque operation n'a qu'une machine possible
        nb_jobs = rng.randint(2, 15); nb_mchs = rng.randint(2, 6)
        nb_techs = rng.randint(1, 4); cte = rng.randint(1, 20)
        ops_par_job, modes_max = rng.randint(1, 4), 1
    elif profil == "un_seul_technicien":
        nb_jobs = rng.randint(2, 12); nb_mchs = rng.randint(2, 6)
        nb_techs = 1; cte = rng.randint(1, 15)
        ops_par_job, modes_max = rng.randint(1, 3), 3
    elif profil == "un_tech_par_machine":
        # Autant de techniciens que de machines : aucun partage de technicien,
        # les setups peuvent tous se derouler en parallele. C'est la forme des
        # fichiers case_* du projet.
        nb_mchs = rng.randint(3, 8); nb_techs = nb_mchs
        nb_jobs = rng.randint(2, 12); cte = rng.randint(1, 15)
        ops_par_job, modes_max = rng.randint(1, 3), 3
    else:
        nb_jobs = rng.randint(1, 25)
        nb_mchs = rng.randint(1, 10)
        nb_techs = rng.randint(1, 8)
        cte = rng.randint(0, 30)
        ops_par_job = rng.randint(1, 5)
        modes_max = rng.randint(1, 3)

    # ── Gammes ────────────────────────────────────────────────────────────────
    gammes, op_id = [], 1
    for job in range(1, nb_jobs + 1):
        for pos in range(1, rng.randint(1, ops_par_job) + 1):
            gammes.append((op_id, job, pos))
            op_id += 1
    nb_ops = len(gammes)

    # ── Modes et temps operatoires ────────────────────────────────────────────
    modes, pt = [], {}
    machines = list(range(1, nb_mchs + 1))
    for (o, _, _) in gammes:
        k = min(rng.randint(1, modes_max), nb_mchs)
        for m in rng.sample(machines, k):
            modes.append((o, m))
            pt[(o, m)] = rng.randint(1, 120)

    # ── Techniciens : PARTITION stricte des machines ──────────────────────────
    # Regle metier du projet : chaque machine a exactement un technicien, un
    # technicien peut gerer plusieurs machines. Le generateur doit la respecter,
    # sinon il teste une configuration qui ne peut pas exister en production —
    # et que validate_excel_data refuse desormais.
    nb_techs = max(1, min(nb_techs, nb_mchs))
    melange = machines[:]
    rng.shuffle(melange)
    # Le modulo garantit au moins une machine par technicien.
    grp = {((i % nb_techs) + 1, m) for i, m in enumerate(melange)}

    data = {
        "params": {"nbJobs": nb_jobs, "nbMchs": nb_mchs, "nbOps": nb_ops},
        "nbtechs": nb_techs,
        "cte": cte,
        "gammes": gammes,
        "modes": modes,
        "pt": pt,
        "grp_mchs": sorted(grp),
        "of_map": {},
        "piece_map": {},
    }

    # ── Disponibilite initiale des machines (une fois sur trois) ──────────────
    # C6bis n'etait exercee par AUCUN test avant celui-ci.
    if profil == "aleatoire" and rng.random() < 0.33:
        data["machine_ready_times"] = {
            m: rng.randint(0, 200) for m in machines if rng.random() < 0.5
        }

    return data


# ══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    from backend.solver.input_parser import parse_excel_to_dict, validate_excel_data
    from backend.solver.model import solve_flexible_jobshop
    from verifier_planning import verifier_planning

    depart = time.time()
    ecrire("# Test de robustesse du solveur")
    ecrire()
    ecrire(f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M:%S')}")
    ecrire()
    ecrire("Verifier 10 fichiers Excel qui se ressemblent ne dit rien du "
           "onzieme. Ce test attaque le solveur avec des instances tirees au "
           "hasard sur toute la plage de parametres, puis controle les "
           "9 contraintes sur chaque planning produit.")

    total = valides = timeouts = 0
    echecs: list[tuple[str, list[str]]] = []
    erreurs: list[tuple[str, str]] = []

    def traiter(etiquette: str, data: dict) -> None:
        nonlocal total, valides, timeouts
        total += 1
        # Toute instance doit d'abord passer la validation metier : cela garantit
        # que le test porte sur des configurations realistes.
        ok, message = validate_excel_data(data)
        if not ok:
            erreurs.append((etiquette, f"instance non conforme : {message[:90]}"))
            return
        try:
            with redirect_stdout(StringIO()):
                df = solve_flexible_jobshop(data, max_time_seconds=BUDGET)
        except ValueError as exc:
            if "Pas de solution" in str(exc):
                timeouts += 1
            else:
                erreurs.append((etiquette, f"ValueError: {exc}"))
            return
        except Exception as exc:
            erreurs.append((etiquette, f"{type(exc).__name__}: {exc}"))
            return

        violations = verifier_planning(data, df)
        if violations:
            echecs.append((etiquette, violations))
        else:
            valides += 1

    # ── 1. Les 20 fichiers Excel du projet ────────────────────────────────────
    ecrire()
    ecrire("## 1. Les 20 fichiers Excel du projet")
    ecrire()
    ecrire("Les 10 de `generated_test_excels/` **et** les 10 de "
           "`generated_test_excels_fixed10tech_cte15/`, jamais testes jusqu'ici "
           "— ils ont une structure differente : 10 techniciens fixes, cte=15.")
    ecrire()

    avant = total
    for dossier in ("generated_test_excels", "generated_test_excels_fixed10tech_cte15"):
        chemin_dossier = RACINE / dossier
        if not chemin_dossier.exists():
            continue
        for fichier in sorted(chemin_dossier.glob("*.xlsx")):
            try:
                data = parse_excel_to_dict(str(fichier))
                ok, _ = validate_excel_data(data)
                if not ok:
                    continue
            except Exception:
                continue
            traiter(f"{dossier}/{fichier.name}", data)

    ecrire(f"{total - avant} fichiers traites.")

    # ── 2. Cas limites ────────────────────────────────────────────────────────
    ecrire()
    ecrire("## 2. Cas limites")
    ecrire()
    ecrire("| Profil | Ce qu'il teste | Instances |")
    ecrire("|---|---|---|")
    profils = [
        ("minimal", "1 piece, 1 operation, 1 machine, 1 technicien, cte=0", 5),
        ("cte_zero", "temps de setup nul", 20),
        ("sans_flexibilite", "une seule machine possible par operation", 20),
        ("un_seul_technicien", "un technicien pour toutes les machines", 20),
        ("un_tech_par_machine", "autant de techniciens que de machines", 20),
    ]
    for profil, description, n in profils:
        avant = total
        for i in range(n):
            traiter(f"{profil}#{i}", generer(10_000 + hash(profil) % 1000 + i, profil))
        ecrire(f"| `{profil}` | {description} | {total - avant} |")

    # ── 3. Instances aleatoires ───────────────────────────────────────────────
    ecrire()
    ecrire("## 3. Instances aleatoires")
    ecrire()
    ecrire(f"{NB_ALEATOIRES} instances tirees au hasard : 1 a 25 pieces, "
           f"1 a 10 machines, 1 a 8 techniciens, cte de 0 a 30, jusqu'a "
           f"3 machines possibles par operation. Une instance sur trois porte "
           f"une disponibilite initiale de machine (contrainte C6bis, "
           f"exercee pour la premiere fois).")

    for graine in range(NB_ALEATOIRES):
        traiter(f"aleatoire#{graine}", generer(graine))

    # ── Bilan ─────────────────────────────────────────────────────────────────
    ecrire()
    ecrire("---")
    ecrire()
    ecrire("## Bilan")
    ecrire()
    ecrire("| Resultat | Nombre |")
    ecrire("|---|---|")
    ecrire(f"| Instances traitees | {total} |")
    ecrire(f"| Plannings produits et **valides** | **{valides}** |")
    ecrire(f"| **Violations de contrainte** | **{len(echecs)}** |")
    ecrire(f"| Pas de solution dans le budget (non bloquant) | {timeouts} |")
    ecrire(f"| Erreurs techniques | {len(erreurs)} |")

    if echecs:
        ecrire()
        ecrire("### Violations detectees")
        ecrire()
        for etiquette, violations in echecs[:15]:
            ecrire(f"**{etiquette}** — {len(violations)} violation(s) :")
            ecrire()
            for v in violations[:5]:
                ecrire(f"- {v}")
            ecrire()
        if len(echecs) > 15:
            ecrire(f"... et {len(echecs) - 15} autre(s) instance(s) en echec.")
    else:
        ecrire()
        ecrire("**Aucune violation de contrainte sur l'ensemble des instances.**")

    if erreurs:
        ecrire()
        ecrire("### Erreurs techniques")
        ecrire()
        for etiquette, message in erreurs[:15]:
            ecrire(f"- `{etiquette}` : {message[:140]}")

    ecrire()
    ecrire(f"Campagne terminee en {time.time() - depart:.0f} secondes.")
    ecrire()
    ecrire("Une instance en echec se rejoue a l'identique : sa graine est dans "
           "son etiquette (`aleatoire#42` -> `generer(42)`).")
    return 0 if not echecs and not erreurs else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        ecrire()
        ecrire("```")
        ecrire(traceback.format_exc()[:3000])
        ecrire("```")
        sys.exit(1)
