# Comparaison des deux formulations du solveur

Genere le 13/09/2026 a 00:40:18

Protocole : meme machine, memes jeux de donnees, budget de **60 secondes** par instance pour les deux versions. Chaque planning produit est verifie par `verifier_planning.py`, independant du solveur.

## 1. Taille des modeles

| Jeu de donnees | Operations | Variables v1 | Variables v2 | Facteur |
|---|---|---|---|---|
| 01_08pieces_cte10 | 18 | 738 | 271 | **/3** |
| 02_12pieces_cte12 | 37 | 5 250 | 778 | **/7** |
| 03_20pieces_cte15 | 57 | 11 352 | 1 198 | **/9** |
| 04_25pieces_cte15 | 90 | 23 930 | 1 891 | **/13** |
| 05_35pieces_cte18 | 141 | 54 726 | 2 962 | **/18** |
| 06_45pieces_cte20 | 186 | 94 606 | 3 907 | **/24** |
| 07_60pieces_cte22 | 255 | 148 048 | 5 356 | **/28** |
| 08_75pieces_cte25 | 305 | 211 252 | 6 406 | **/33** |
| 09_90pieces_cte28 | 359 | 250 804 | 7 540 | **/33** |
| 10_100pieces_cte30 | 395 | 276 178 | 8 296 | **/33** |

La v1 cree une variable booleenne par PAIRE d'operations (ordre sur une machine, ordre des setups d'un technicien). La v2 remplace ces paires par des intervalles optionnels confies a `AddNoOverlap`.

## 2. Resultats

| Jeu de donnees | Op. | v1 — temps | v1 — resultat | v2 — temps | v2 — resultat |
|---|---|---|---|---|---|
| 01_08pieces_cte10 | 18 | 3.0 s | 245 min · valide | 1.3 s | 256 min · valide |
| 02_12pieces_cte12 | 37 | 67.4 s | 400 min · valide | 12.0 s | 401 min · valide |
| 03_20pieces_cte15 | 57 | 73.7 s | 1612 min · valide | 61.1 s | 560 min · valide |
| 04_25pieces_cte15 | 90 | 97.4 s | 20889 min · valide | 60.7 s | 784 min · valide |
| 05_35pieces_cte18 | 141 | 134.9 s | echec — ValueError: Pas de solution trouvée. Status: | 24.1 s | 1239 min · valide |
| 06_45pieces_cte20 | 186 | 100.4 s | echec — ValueError: Pas de solution trouvée. Status: | 29.9 s | 1668 min · valide |
| 07_60pieces_cte22 | 255 | 143.7 s | echec — ValueError: Pas de solution trouvée. Status: | 63.5 s | 1986 min · valide |
| 08_75pieces_cte25 | 305 | 145.7 s | echec — ValueError: Pas de solution trouvée. Status: | 64.4 s | 2576 min · valide |
| 09_90pieces_cte28 | 359 | 150.6 s | echec — ValueError: Pas de solution trouvée. Status: | 69.0 s | 2720 min · valide |
| 10_100pieces_cte30 | 395 | 149.3 s | echec — ValueError: Pas de solution trouvée. Status: | 66.4 s | 2619 min · valide |

## 3. Synthese

| Indicateur | v1 (grand M) | v2 (CP-SAT natif) |
|---|---|---|
| Instances resolues | 4/10 | **10/10** |
| Plannings valides | 4/4 | **10/10** |
| Temps total | 1066 s | **452 s** |

### Qualite des solutions, sur les instances resolues par les deux

| Jeu de donnees | Makespan v1 | Makespan v2 | Ecart |
|---|---|---|---|
| 01_08pieces_cte10 | 245 min | 256 min | v2 moins bon de 11 min |
| 02_12pieces_cte12 | 400 min | 401 min | v2 moins bon de 1 min |
| 03_20pieces_cte15 | 1612 min | 560 min | **v2 meilleur de 1052 min** |
| 04_25pieces_cte15 | 20889 min | 784 min | **v2 meilleur de 20105 min** |

Campagne terminee en 1545 secondes.
