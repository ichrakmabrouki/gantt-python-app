# Rapport de tests — application Gantt

Genere le 12/09/2026 a 23:03:11

## 1. Environnement

- Python : `3.11.9` (64bit)
- Systeme : Windows 10
- Dossier : `C:\Users\PC\Documents\gantt_python`

| Paquet | Version | Statut |
|---|---|---|
| streamlit | 1.55.0 | OK |
| pandas | 2.2.2 | OK |
| plotly | 6.6.0 | OK |
| openpyxl | 3.1.5 | OK |
| supabase | 2.28.3 | OK |
| PIL | 12.1.1 | OK |
| extra_streamlit_components | n/a | OK |
| ortools | 9.10.4067 | OK |

## 2. Modules du projet

| Module | Statut |
|---|---|
| `backend.converter` | OK |
| `backend.data_processor` | OK |
| `backend.database` | OK |
| `backend.gantt_builder` | OK |
| `backend.kpi_calculator` | OK |
| `backend.solver.input_parser` | OK |
| `backend.solver.model` | OK |
| `verifier_planning` | OK |

## 3. Connexion Supabase

- URL : `https://tzhklwpduhenotlriabr.supabase.co`
- Cle : `sb_sec...m9GfT0` (41 caracteres)
- SESSION_SECRET defini : NON (voir remarque)
- DNS : `tzhklwpduhenotlriabr.supabase.co` -> `172.64.149.246`
- API REST : HTTP 200

| Table | Statut |
|---|---|
| `users` | OK (1 ligne lue) |
| `operations` | OK (1 ligne lue) |
| `jobs` | OK (1 ligne lue) |
| `kpis` | OK (1 ligne lue) |
| `prix` | OK (1 ligne lue) |
| `planning_jours` | OK (1 ligne lue) |
| `app_access_logs` | OK (1 ligne lue) |

## 6. Auto-test du verificateur

Le verificateur est lui-meme teste : un planning correct doit passer, sept plannings volontairement fautifs doivent etre rejetes.

| Scenario | Violations detectees | Attendu | Resultat |
|---|---|---|---|
| Planning correct | 0 | 0 | OK |
| Chevauchement machine | 1 | >= 1 | OK |
| Setup cte non respecte | 1 | >= 1 | OK |
| Precedence violee | 1 | >= 1 | OK |
| Duree incorrecte | 1 | >= 1 | OK |
| Machine non autorisee | 1 | >= 1 | OK |
| Demarrage avant cte | 1 | >= 1 | OK |
| Operation manquante | 1 | >= 1 | OK |

## 7. Calcul des KPI

- Profit total calcule : **430.0** (attendu 430.0)
- Recapitulatif par machine : 2 ligne(s)
- Recapitulatif par piece : 2 ligne(s)
- Charge machine 1 : 120 min (attendu 120)

## 8. Securite : mots de passe et jetons de session

| Test | Resultat |
|---|---|
| Le hash n'est pas le mot de passe en clair | OK |
| Format PBKDF2 avec sel | OK |
| Deux hash du meme mot de passe different (sel) | OK |
| Bon mot de passe accepte | OK |
| Mauvais mot de passe refuse | OK |
| Mot de passe vide refuse | OK |
| Jeton valide relu correctement | OK |
| Jeton neuf non renouvele | OK |
| Jeton proche de l'expiration -> renouvellement | OK |
| Jeton expire refuse | OK |
| Jeton falsifie (alice -> admin) refuse | OK |
| Jeton vide refuse | OK |
| Jeton n'importe quoi refuse | OK |

## 9. Robustesse : entrees invalides

Chaque cas doit produire une erreur **explicite**, jamais un plantage muet.

| Cas | Comportement |
|---|---|
| Fichier texte renomme en .xlsx | OK — ValueError: Excel file format cannot be determined, you must specify an engine man |
| Fichier inexistant | OK — FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\PC\\Documents\\gantt_ |
| nbOps incoherent avec GAMMES | OK — "nbOps=99 mais 1 opérations dans GAMMES." |
| Machine sans technicien | OK — "Machines sans technicien : [2]" |

## 4. Lecture et validation des fichiers Excel

| Dataset | Pieces | Operations | Machines | cte | Somme durees | Horizon | Valide |
|---|---|---|---|---|---|---|---|
| dataset_01_08pieces_cte10 | 8 | 18 | 6 | 10 | 2104 | 2464 | oui |
| dataset_02_12pieces_cte12 | 12 | 37 | 7 | 12 | 7188 | 8076 | oui |
| dataset_03_20pieces_cte15 | 20 | 57 | 8 | 15 | 11046 | 12756 | oui |
| dataset_04_25pieces_cte15 | 25 | 90 | 9 | 15 | 18205 | 20905 | oui |
| dataset_05_35pieces_cte18 | 35 | 141 | 10 | 18 | 30242 | 35318 | oui |
| dataset_06_45pieces_cte20 | 45 | 186 | 10 | 20 | 40094 | 47534 | oui |
| dataset_07_60pieces_cte22 | 60 | 255 | 12 | 22 | 55238 | 66458 | oui |
| dataset_08_75pieces_cte25 | 75 | 305 | 12 | 25 | 64787 | 80037 | oui |
| dataset_09_90pieces_cte28 | 90 | 359 | 14 | 28 | 77739 | 97843 | oui |
| dataset_10_100pieces_cte30 | 100 | 395 | 15 | 30 | 83609 | 107309 | oui |

> Rappel : 8 dataset(s) ont un horizon superieur a 10000, l'ancienne valeur de `M_big` codee en dur. Horizon maximal observe : 107309.

## 5. Solveur et validite des plannings

| Dataset | Budget | Temps reel | Operations | Makespan | Planning valide |
|---|---|---|---|---|---|
| 01_08pieces_cte10 | 20 s | 5.3 s | 18 | 245 min | oui |
| 02_12pieces_cte12 | 20 s | 27.3 s | 37 | 868 min | oui |
| 03_20pieces_cte15 | 20 s | 32.4 s | — | — | ECHEC ValueError: Pas de solution trouvée. Status: UNKNOWN |
| 04_25pieces_cte15 | 30 s | 57.5 s | — | — | ECHEC ValueError: Pas de solution trouvée. Status: UNKNOWN |
| 05_35pieces_cte18 | 30 s | 77.4 s | — | — | ECHEC ValueError: Pas de solution trouvée. Status: UNKNOWN |
| 06_45pieces_cte20 | 30 s | 134.4 s | — | — | ECHEC ValueError: Pas de solution trouvée. Status: UNKNOWN |
| 07_60pieces_cte22 | 45 s | 146.1 s | — | — | ECHEC ValueError: Pas de solution trouvée. Status: UNKNOWN |
| 08_75pieces_cte25 | 45 s | 202.4 s | — | — | ECHEC ValueError: Pas de solution trouvée. Status: UNKNOWN |
| 09_90pieces_cte28 | 45 s | 251.8 s | — | — | ECHEC ValueError: Pas de solution trouvée. Status: UNKNOWN |
| 10_100pieces_cte30 | 60 s | 287.6 s | — | — | ECHEC ValueError: Pas de solution trouvée. Status: UNKNOWN |

---

## Synthese

| Etape | Test | Resultat |
|---|---|---|
| 1. Environnement | Dependances installees | **OK** |
| 2. Modules | Import de tous les modules | **OK** |
| 3. Supabase | Secrets presents | **OK** |
| 3. Supabase | Resolution DNS | **OK** |
| 3. Supabase | API REST joignable | **OK** |
| 3. Supabase | Tables accessibles | **OK** |
| 6. Verificateur | Auto-test (8/8) | **OK** |
| 7. KPI | Profit et recapitulatifs | **OK** |
| 8. Securite | Mots de passe et jetons (13/13) | **OK** |
| 9. Robustesse | Entrees invalides (4/4) | **OK** |
| 4. Parsing | Lecture des 10 datasets | **OK** |
| 5. Solveur | Resolution (2/10) | **PARTIEL (2/10)** |
| 5. Solveur | Plannings valides (2/2) | **OK** |

**12 / 13 tests au vert** — campagne terminee en 1444 secondes.

Rapport genere le 12/09/2026 a 23:27:15.
