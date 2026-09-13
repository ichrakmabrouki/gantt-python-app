# Consommation mémoire d'une résolution

Généré le 13/09/2026 à 19:36:14

Mesure du pic de mémoire du processus (RSS) pendant la résolution, budget 30 s par instance. La référence est la limite de **1024 Mo** de Streamlit Community Cloud.

Mémoire au repos, modules chargés : **79 Mo**. C'est le coût fixe de Python, Streamlit, pandas, plotly et OR-Tools — il est payé une seule fois pour tout le conteneur, quel que soit le nombre de visiteurs.

| Fichier | Opérations | Pic mémoire | Surcoût vs repos | Temps |
|---|---|---|---|---|
| dataset_01_08pieces_cte10 | 18 | 93 Mo | +14 Mo | 0.2 s |
| dataset_02_12pieces_cte12 | 37 | 95 Mo | +16 Mo | 4.9 s |
| dataset_03_20pieces_cte15 | 57 | 96 Mo | +16 Mo | 3.5 s |
| dataset_04_25pieces_cte15 | 90 | 96 Mo | +17 Mo | 11.5 s |
| dataset_05_35pieces_cte18 | 141 | 98 Mo | +19 Mo | 10.0 s |
| dataset_06_45pieces_cte20 | 186 | 99 Mo | +20 Mo | 19.3 s |
| dataset_07_60pieces_cte22 | 255 | 101 Mo | +22 Mo | 30.7 s |
| dataset_08_75pieces_cte25 | 305 | 103 Mo | +24 Mo | 30.5 s |
| dataset_09_90pieces_cte28 | 359 | 104 Mo | +25 Mo | 30.4 s |
| dataset_10_100pieces_cte30 | 395 | 104 Mo | +25 Mo | 30.5 s |
| case_01_08pieces | 19 | 103 Mo | +24 Mo | 0.1 s |
| case_02_12pieces | 36 | 103 Mo | +24 Mo | 1.3 s |
| case_03_16pieces | 49 | 103 Mo | +23 Mo | 1.1 s |
| case_04_20pieces | 60 | 109 Mo | +29 Mo | 0.6 s |
| case_05_25pieces | 83 | 108 Mo | +29 Mo | 3.5 s |
| case_06_30pieces | 105 | 104 Mo | +25 Mo | 2.7 s |
| case_07_40pieces | 153 | 103 Mo | +24 Mo | 10.5 s |
| case_08_50pieces | 210 | 143 Mo | +64 Mo | 7.4 s |
| case_09_75pieces | 305 | 142 Mo | +63 Mo | 13.5 s |
| case_10_100pieces | 396 | 166 Mo | +86 Mo | 19.8 s |

## Ce que ça implique pour l'hébergement gratuit

| | Mo |
|---|---|
| Limite Streamlit Community Cloud | 1024 |
| Coût fixe (Python + bibliothèques), payé une fois | 79 |
| Marge disponible pour les résolutions | 945 |
| Pire résolution mesurée | 86 |

**Environ 10 résolution(s) du plus gros fichier peuvent tenir en mémoire simultanément.**

> Le verrou de `app.py` sérialise déjà les résolutions, ce qui laisse une marge confortable.

Un visiteur qui ne fait que consulter un planning déjà calculé ne coûte que quelques mégaoctets : le nombre de visiteurs n'est pas le problème, ce sont les résolutions simultanées.
