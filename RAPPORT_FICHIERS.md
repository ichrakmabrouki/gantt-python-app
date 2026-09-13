# Validation sur les fichiers Excel du projet

Genere le 13/09/2026 a 02:20:51

Budget de resolution : **60 secondes** par fichier. Chaque planning produit est relu par `verifier_planning.py`, independant du solveur.

## 1. Caracteristiques des fichiers

| Fichier | Pieces | Operations | Machines | Techniciens | cte | Modes | Modes/op |
|---|---|---|---|---|---|---|---|
| dataset_01_08pieces_cte10 | 8 | 18 | 6 | 3 | 10 | 36 | 2.00 |
| dataset_02_12pieces_cte12 | 12 | 37 | 7 | 4 | 12 | 111 | 3.00 |
| dataset_03_20pieces_cte15 | 20 | 57 | 8 | 4 | 15 | 171 | 3.00 |
| dataset_04_25pieces_cte15 | 25 | 90 | 9 | 5 | 15 | 270 | 3.00 |
| dataset_05_35pieces_cte18 | 35 | 141 | 10 | 5 | 18 | 423 | 3.00 |
| dataset_06_45pieces_cte20 | 45 | 186 | 10 | 5 | 20 | 558 | 3.00 |
| dataset_07_60pieces_cte22 | 60 | 255 | 12 | 6 | 22 | 765 | 3.00 |
| dataset_08_75pieces_cte25 | 75 | 305 | 12 | 6 | 25 | 915 | 3.00 |
| dataset_09_90pieces_cte28 | 90 | 359 | 14 | 7 | 28 | 1077 | 3.00 |
| dataset_10_100pieces_cte30 | 100 | 395 | 15 | 8 | 30 | 1185 | 3.00 |
| case_01_08pieces | 8 | 19 | 6 | 6 | 15 | 38 | 2.00 |
| case_02_12pieces | 12 | 36 | 7 | 7 | 15 | 108 | 3.00 |
| case_03_16pieces | 16 | 49 | 8 | 8 | 15 | 147 | 3.00 |
| case_04_20pieces | 20 | 60 | 8 | 8 | 15 | 180 | 3.00 |
| case_05_25pieces | 25 | 83 | 9 | 9 | 15 | 249 | 3.00 |
| case_06_30pieces | 30 | 105 | 10 | 10 | 15 | 315 | 3.00 |
| case_07_40pieces | 40 | 153 | 11 | 10 | 15 | 459 | 3.00 |
| case_08_50pieces | 50 | 210 | 12 | 10 | 15 | 630 | 3.00 |
| case_09_75pieces | 75 | 305 | 14 | 10 | 15 | 915 | 3.00 |
| case_10_100pieces | 100 | 396 | 15 | 10 | 15 | 1188 | 3.00 |

## 2. Resolution et controle des contraintes

Une case vide signifie « aucune violation ». Un nombre signifie le nombre de violations detectees pour cette contrainte.

| Fichier | Temps | Makespan | C1 | C2 | C3 | C6 | C7 | C8 | C9 | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| dataset_01_08pieces_cte10 | 0.2 s | 252 min |  |  |  |  |  |  |  | valide |
| dataset_02_12pieces_cte12 | 4.6 s | 397 min |  |  |  |  |  |  |  | valide |
| dataset_03_20pieces_cte15 | 22.7 s | 558 min |  |  |  |  |  |  |  | valide |
| dataset_04_25pieces_cte15 | 4.2 s | 802 min |  |  |  |  |  |  |  | valide |
| dataset_05_35pieces_cte18 | 20.3 s | 1241 min |  |  |  |  |  |  |  | valide |
| dataset_06_45pieces_cte20 | 26.3 s | 1672 min |  |  |  |  |  |  |  | valide |
| dataset_07_60pieces_cte22 | 60.4 s | 1980 min |  |  |  |  |  |  |  | valide |
| dataset_08_75pieces_cte25 | 60.5 s | 2432 min |  |  |  |  |  |  |  | valide |
| dataset_09_90pieces_cte28 | 60.8 s | 2555 min |  |  |  |  |  |  |  | valide |
| dataset_10_100pieces_cte30 | 60.6 s | 2737 min |  |  |  |  |  |  |  | valide |
| case_01_08pieces | 0.2 s | 218 min |  |  |  |  |  |  |  | valide |
| case_02_12pieces | 1.8 s | 360 min |  |  |  |  |  |  |  | valide |
| case_03_16pieces | 1.7 s | 425 min |  |  |  |  |  |  |  | valide |
| case_04_20pieces | 1.0 s | 508 min |  |  |  |  |  |  |  | valide |
| case_05_25pieces | 3.3 s | 642 min |  |  |  |  |  |  |  | valide |
| case_06_30pieces | 3.9 s | 738 min |  |  |  |  |  |  |  | valide |
| case_07_40pieces | 16.5 s | 984 min |  |  |  |  |  |  |  | valide |
| case_08_50pieces | 18.7 s | 1304 min |  |  |  |  |  |  |  | valide |
| case_09_75pieces | 22.6 s | 1601 min |  |  |  |  |  |  |  | valide |
| case_10_100pieces | 33.3 s | 1931 min |  |  |  |  |  |  |  | valide |

## 3. Bilan

| Resultat | Nombre |
|---|---|
| Fichiers traites | 20 |
| Plannings produits | 20 |
| Plannings **valides sur les 9 contraintes** | **20** |
| Plannings en violation | 0 |
| Aucune solution dans le budget | 0 |
| Erreurs techniques | 0 |

Campagne terminee en 434 secondes.

> C4 (debut apres fin de setup), C5 (setup >= cte) et C10 (fin >= duree + setup) ne figurent pas dans le tableau : elles sont structurelles dans la version 2. Le setup occupe exactement le creneau `[S - cte, S]` et la fin vaut `S + duree`, donc elles sont vraies par construction et non par verification.
