# backend/solver/baseline.py
#
# ORDONNANCEMENT DE REFERENCE — ce que l'atelier ferait sans optimiseur.
#
# Un makespan de 802 minutes ne veut rien dire tout seul : 802 par rapport a
# quoi ? Pour chiffrer l'apport du solveur il faut un point de comparaison, et
# ce point ne doit pas etre un homme de paille. On ne compare donc pas a un
# ordonnancement absurde, mais au MEILLEUR de quatre regles de priorite
# classiques — celles que l'on retrouve dans les ateliers et dans la plupart
# des MES :
#
#   FIFO   premier arrive, premier servi (ordre des pieces)
#   SPT    shortest processing time  — l'operation la plus courte d'abord
#   LPT    longest processing time   — la plus longue d'abord
#   MWKR   most work remaining       — la piece a qui il reste le plus a faire
#
# Chaque regle produit un planning complet par ordonnancement de liste :
# a chaque etape, on regarde les operations pretes, on en choisit une selon la
# regle, et on la place au plus tot sur la machine qui la terminerait le plus
# tot. C'est exactement la logique d'un chef d'atelier qui remplit son tableau
# machine par machine.
#
# Les plannings produits respectent LES MEMES CONTRAINTES que le modele CP-SAT
# (C1, C3, C6, C6bis, C7, C8, C9) — sans quoi la comparaison n'aurait aucun
# sens. C'est verifie par `verifier_planning.py`, qui ne connait ni ce fichier
# ni OR-Tools.

import pandas as pd

REGLES = ("FIFO", "SPT", "LPT", "MWKR")


def _chevauche(a1: int, b1: int, a2: int, b2: int) -> bool:
    """Deux intervalles se chevauchent-ils ? Se toucher ne compte pas."""
    return a1 < b2 and a2 < b1


def _plus_tot(
    depart_mini: int,
    duree: int,
    cte: int,
    occupation_machine: list[tuple[int, int]],
    occupations_tech: list[list[tuple[int, int]]],
) -> int:
    """Plus petite date de debut possible pour une operation.

    La machine est occupee de `debut - cte` (reservation du changement de
    serie) a `debut + duree`. Le technicien, lui, n'est pris que pendant le
    changement de serie : de `debut - cte` a `debut`.

    On avance la date tant qu'un conflit subsiste. Comme on ne recule jamais,
    la boucle se termine.
    """
    debut = max(depart_mini, cte)
    while True:
        conflit = False

        for (a, b) in occupation_machine:
            if _chevauche(debut - cte, debut + duree, a, b):
                debut = b + cte
                conflit = True

        for occupation in occupations_tech:
            for (a, b) in occupation:
                if _chevauche(debut - cte, debut, a, b):
                    debut = b + cte
                    conflit = True

        if not conflit:
            return debut


def ordonnancer_par_regle(data: dict, regle: str = "FIFO") -> pd.DataFrame:
    """Construit un planning complet en appliquant une regle de priorite."""
    cte      = int(data["cte"])
    gammes   = data["gammes"]
    modes    = data["modes"]
    pt       = data["pt"]
    grp_mchs = data["grp_mchs"]
    dispo_machine = {
        int(m): int(t) for m, t in data.get("machine_ready_times", {}).items()
    }

    # ── Index ─────────────────────────────────────────────────────────────────
    machines_de_op: dict[int, list[int]] = {}
    for (o, m) in modes:
        machines_de_op.setdefault(int(o), []).append(int(m))

    techs_de_machine: dict[int, list[int]] = {}
    for (t, m) in grp_mchs:
        techs_de_machine.setdefault(int(m), []).append(int(t))

    job_de_op: dict[int, int] = {}
    ops_du_job: dict[int, list[tuple[int, int]]] = {}
    for (op_id, job_id, pos) in gammes:
        op_id, job_id, pos = int(op_id), int(job_id), int(pos)
        job_de_op[op_id] = job_id
        ops_du_job.setdefault(job_id, []).append((pos, op_id))
    for sequence in ops_du_job.values():
        sequence.sort()

    def duree_mini(op: int) -> int:
        durees = [int(pt.get((op, m), 0)) for m in machines_de_op.get(op, [])]
        return min(durees) if durees else 0

    # Travail restant sur la piece, utilise par la regle MWKR.
    travail_restant: dict[int, int] = {}
    for job, sequence in ops_du_job.items():
        cumul = 0
        for (_, op) in reversed(sequence):
            cumul += duree_mini(op)
            travail_restant[op] = cumul

    # ── Etat de l'atelier ─────────────────────────────────────────────────────
    occupation_machine: dict[int, list[tuple[int, int]]] = {}
    occupation_tech: dict[int, list[tuple[int, int]]] = {}
    indice_courant   = {job: 0 for job in ops_du_job}
    fin_precedente   = {job: 0 for job in ops_du_job}
    machine_precedente: dict[int, int | None] = {job: None for job in ops_du_job}

    lignes = []
    restantes = sum(len(s) for s in ops_du_job.values())

    while restantes > 0:
        # ── Operations pretes : la precedente de la meme piece est terminee ───
        candidates = []
        for job, sequence in ops_du_job.items():
            i = indice_courant[job]
            if i >= len(sequence):
                continue
            op = sequence[i][1]
            if not machines_de_op.get(op):
                # Operation sans machine possible : le fichier serait invalide.
                raise ValueError(f"L'operation {op} n'a aucune machine possible.")
            candidates.append((job, op))

        if not candidates:
            break

        # ── Meilleure machine pour chaque candidate ──────────────────────────
        evaluations = []
        for (job, op) in candidates:
            meilleure = None
            for m in sorted(machines_de_op[op]):
                duree = int(pt.get((op, m), 0))

                # C3 : apres la fin de l'operation precedente de la piece.
                depart = max(fin_precedente[job], dispo_machine.get(m, 0) + cte)

                # C9 : changer de machine en cours de gamme coute un cte de
                # plus, des lors que les deux machines partagent un technicien.
                precedente = machine_precedente[job]
                if precedente is not None and precedente != m:
                    communs = (set(techs_de_machine.get(precedente, []))
                               & set(techs_de_machine.get(m, [])))
                    if communs:
                        depart = max(depart, fin_precedente[job] + cte)

                debut = _plus_tot(
                    depart, duree, cte,
                    occupation_machine.get(m, []),
                    [occupation_tech.get(t, []) for t in techs_de_machine.get(m, [])],
                )
                fin = debut + duree
                if meilleure is None or fin < meilleure[1]:
                    meilleure = (debut, fin, m, duree)

            debut, fin, m, duree = meilleure
            evaluations.append({
                "job": job, "op": op, "machine": m,
                "debut": debut, "fin": fin, "duree": duree,
            })

        # ── Application de la regle de priorite ──────────────────────────────
        # A egalite, on departage toujours par le numero de piece puis
        # d'operation : le resultat est reproductible.
        if regle == "SPT":
            cle = lambda e: (e["duree"], e["fin"], e["job"], e["op"])
        elif regle == "LPT":
            cle = lambda e: (-e["duree"], e["fin"], e["job"], e["op"])
        elif regle == "MWKR":
            cle = lambda e: (-travail_restant.get(e["op"], 0), e["fin"], e["job"], e["op"])
        else:  # FIFO
            cle = lambda e: (e["job"], e["op"], e["fin"])

        choisie = min(evaluations, key=cle)

        # ── Placement ────────────────────────────────────────────────────────
        job, op = choisie["job"], choisie["op"]
        m, debut, fin = choisie["machine"], choisie["debut"], choisie["fin"]

        occupation_machine.setdefault(m, []).append((debut - cte, fin))
        for t in techs_de_machine.get(m, []):
            occupation_tech.setdefault(t, []).append((debut - cte, debut))

        indice_courant[job]     += 1
        fin_precedente[job]      = fin
        machine_precedente[job]  = m
        restantes               -= 1

        lignes.append({
            "OperationID":    op,
            "MachineID":      m,
            "MachineLabel":   f"Machine {m}",
            "JobID":          job,
            "JobLabel":       f"Job {job}",
            "StartTime":      debut,
            "EndTime":        fin,
            "Duration":       choisie["duree"],
            "ProcessingTime": choisie["duree"],
        })

    df = (pd.DataFrame(lignes)
          .sort_values(["JobID", "StartTime"])
          .reset_index(drop=True))
    df.attrs["makespan"] = int(df["EndTime"].max()) if not df.empty else 0
    df.attrs["regle"] = regle
    return df


def ordonnancement_reference(data: dict) -> pd.DataFrame:
    """Meilleur planning obtenu par les regles de priorite classiques.

    On retient le meilleur, pas le pire : l'ecart annonce face au solveur est
    donc une borne basse de son apport reel.
    """
    meilleur = None
    resultats = {}
    for regle in REGLES:
        planning = ordonnancer_par_regle(data, regle)
        if planning.empty:
            continue
        resultats[regle] = int(planning.attrs["makespan"])
        if meilleur is None or planning.attrs["makespan"] < meilleur.attrs["makespan"]:
            meilleur = planning
    if meilleur is None:
        return pd.DataFrame()
    meilleur.attrs["makespans_par_regle"] = resultats
    return meilleur
