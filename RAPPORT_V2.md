# Version 2 du solveur — mesures

Genere le 13/09/2026 a 01:53:34

Budget : **60 secondes** par instance. Chaque planning est verifie par `verifier_planning.py`.

| Jeu de donnees | Operations | Variables | Temps | Makespan | Planning valide |
|---|---|---|---|---|---|
| 01_08pieces_cte10 | 18 | 199 | 0.2 s | 246 min | oui |
| 02_12pieces_cte12 | 37 | 556 | 1.8 s | 400 min | oui |
| 03_20pieces_cte15 | 57 | 856 | 6.6 s | 558 min | oui |
| 04_25pieces_cte15 | 90 | 1 351 | 4.5 s | 802 min | oui |
| 05_35pieces_cte18 | 141 | 2 116 | 18.6 s | 1241 min | oui |
| 06_45pieces_cte20 | 186 | 2 791 | 8.5 s | 1652 min | oui |
| 07_60pieces_cte22 | 255 | 3 826 | 60.3 s | 1948 min | oui |
| 08_75pieces_cte25 | 305 | 4 576 | 60.4 s | 2425 min | oui |
| 09_90pieces_cte28 | 359 | 5 386 | 60.5 s | 2552 min | oui |
| 10_100pieces_cte30 | 395 | 5 926 | 60.8 s | 2667 min | oui |

**10/10 instances resolues, 10/10 plannings valides.** Campagne terminee en 287 secondes.
