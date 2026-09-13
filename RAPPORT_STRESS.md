# Test de robustesse du solveur

Genere le 13/09/2026 a 12:13:46

Verifier 10 fichiers Excel qui se ressemblent ne dit rien du onzieme. Ce test attaque le solveur avec des instances tirees au hasard sur toute la plage de parametres, puis controle les 9 contraintes sur chaque planning produit.

## 1. Les 20 fichiers Excel du projet

Les 10 de `generated_test_excels/` **et** les 10 de `generated_test_excels_fixed10tech_cte15/`, jamais testes jusqu'ici — ils ont une structure differente : 10 techniciens fixes, cte=15.

20 fichiers traites.

## 2. Cas limites

| Profil | Ce qu'il teste | Instances |
|---|---|---|
| `minimal` | 1 piece, 1 operation, 1 machine, 1 technicien, cte=0 | 5 |
| `cte_zero` | temps de setup nul | 20 |
| `sans_flexibilite` | une seule machine possible par operation | 20 |
| `un_seul_technicien` | un technicien pour toutes les machines | 20 |
| `un_tech_par_machine` | autant de techniciens que de machines | 20 |

## 3. Instances aleatoires

150 instances tirees au hasard : 1 a 25 pieces, 1 a 10 machines, 1 a 8 techniciens, cte de 0 a 30, jusqu'a 3 machines possibles par operation. Une instance sur trois porte une disponibilite initiale de machine (contrainte C6bis, exercee pour la premiere fois).

---

## Bilan

| Resultat | Nombre |
|---|---|
| Instances traitees | 255 |
| Plannings produits et **valides** | **255** |
| **Violations de contrainte** | **0** |
| Pas de solution dans le budget (non bloquant) | 0 |
| Erreurs techniques | 0 |

**Aucune violation de contrainte sur l'ensemble des instances.**

Campagne terminee en 128 secondes.

Une instance en echec se rejoue a l'identique : sa graine est dans son etiquette (`aleatoire#42` -> `generer(42)`).
