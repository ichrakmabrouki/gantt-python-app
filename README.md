# Workshop Scheduling Optimizer

Production scheduling for a mechanical workshop: assigns operations to machines,
sequences them under technician and setup constraints, and reports the cost and
profit of every part.

Built with **OR-Tools CP-SAT**, **Streamlit** and **Supabase**.

---

## The problem

A mechanical workshop runs parts through a sequence of operations. Each
operation can go on several machines, each machine needs a **series changeover**
(setup) before it runs, and a **technician** performs that changeover. One
technician covers several machines and cannot be in two places at once.

This is a **flexible job shop with sequence-dependent setups and a secondary
resource** — one of the harder classes of scheduling problem. The goal is to
minimise the makespan while telling the workshop manager what each part costs
and earns.

## What it does

- Imports the workshop data from an Excel workbook (a filled-in template is
  downloadable from the app)
- Solves the assignment and sequencing with CP-SAT
- Renders the optimised Gantt chart per machine
- Computes KPIs: machine load, operation count, profit and margin per part
- Saves a planning per day, and can reuse the previous day's machine
  availability so schedules chain across days
- Multi-user: accounts, per-user data isolation, exports to CSV / Excel / HTML

---

## The interesting part: reformulating the model

The original model encoded the problem MILP-style — implications written with a
big-M constant, and **one boolean variable per pair of operations** to decide
the order on a resource. CP-SAT accepts that, but cannot reason about it: it
only sees arithmetic where the model meant "if … then".

The cost is quadratic. On the largest instance, 271 438 of the 276 178 variables
— 98 % — were pairwise booleans, and building the model alone took nearly four
minutes before the search even started.

The rewrite is two ideas:

| | Before | After |
|---|---|---|
| Conditional constraints | `s2 >= e1 - M(1-x1) - M(1-x2)` | `.OnlyEnforceIf([x1, x2])` |
| Machine disjunction | 92 774 boolean `z` variables | optional intervals + one `AddNoOverlap` per machine |
| Technician serialisation | 178 664 boolean `K` variables | `AddNoOverlap` on setup intervals |

`OnlyEnforceIf` is exact reification — no arbitrary constant, and the solver
understands the condition. `AddNoOverlap` hands the sequencing to CP-SAT's
dedicated scheduling propagators, which reason over the whole resource instead
of comparing tasks two by two.

### Measured results

Same machine, same ten instances, **60 s budget per instance** for both versions.
Every schedule is checked by an independent verifier.

| Instance | Operations | v1 time | v1 makespan | v2 time | v2 makespan |
|---|---|---|---|---|---|
| 8 parts | 18 | 3.0 s | 245 min | **0.2 s** | 246 min |
| 12 parts | 37 | 67.4 s | 400 min | **1.8 s** | 400 min |
| 20 parts | 57 | 73.7 s | 1 612 min | **6.6 s** | **558 min** |
| 25 parts | 90 | 97.4 s | 20 889 min | **4.5 s** | **802 min** |
| 35 parts | 141 | 134.9 s | no solution | **18.6 s** | **1 241 min** |
| 45 parts | 186 | 100.4 s | no solution | **8.5 s** | **1 652 min** |
| 60 parts | 255 | 143.7 s | no solution | 60.3 s | **1 948 min** |
| 75 parts | 305 | 145.7 s | no solution | 60.4 s | **2 425 min** |
| 90 parts | 359 | 150.6 s | no solution | 60.5 s | **2 552 min** |
| 100 parts | 395 | 149.3 s | no solution | 60.8 s | **2 667 min** |

| | v1 | v2 |
|---|---|---|
| Instances solved | 4/10 | **10/10** |
| Total time | 1 066 s | **287 s** |
| Variables (100 parts) | 276 178 | **5 926** |

Three numbers worth pulling out:

- **Same answer, 37× faster** on the 12-part instance: both reach 400 minutes,
  v1 in 67.4 s, v2 in 1.8 s.
- **26× better schedule** on the 25-part instance: v1 returns a *valid* but
  useless 20 889-minute plan — the first feasible solution it managed to build
  before running out of budget. v2 returns 802 minutes.
- **From nothing to something** on the six largest instances, where v1 returned
  no solution at all.

The old version did not merely fail on large instances. Where it "succeeded" it
produced unusable schedules — and nothing flagged it, because nothing checked
the quality of the output.

---

## How correctness is guaranteed

A solver can return a provably optimal solution to the wrong model. So
correctness is not argued, it is **checked on the output** by code that knows
nothing about OR-Tools.

`verifier_planning.py` reads the input data and the produced schedule,
recomputes everything and reports any deviation:

| | Checked |
|---|---|
| C1 | Each operation scheduled once, on an allowed machine |
| C2 | Duration matches the declared processing time |
| C3 | Operation precedence within a part |
| C6 | No start before the initial setup time |
| C7 | No machine overlap, and the setup delay between two operations |
| C8 | A technician never performs two changeovers at once, across machines |
| C9 | Setup delay when a part moves between machines of the same technician |

Evidence:

- The verifier is itself tested on **10 crafted scenarios** — one correct
  schedule and nine deliberately broken. 10/10 classified correctly.
- **20 Excel files** from two structurally different families: 20/20 valid.
- **235 generated instances** — random parameters plus edge cases (`cte = 0`,
  single machine, single technician, no machine flexibility): 235/235 valid.
  Each instance is reproducible from its seed.
- **Every real solve in the app** is verified before the Gantt is displayed. If
  a constraint is violated, the app shows the violation instead of a wrong chart.

The last point is the one that matters: correctness no longer rests on "it
worked when I tested it", but on "every result is checked before it is shown".

---

## Quick start

```bash
git clone https://github.com/ichrakmabrouki/gantt-python-app.git
cd gantt-python-app
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:

```toml
SUPABASE_URL   = "https://<your-project>.supabase.co"
SUPABASE_KEY   = "<your secret key>"
SESSION_SECRET = "<random value, see below>"
```

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"   # SESSION_SECRET
python check_supabase.py                                        # verify the connection
streamlit run app.py
```

Database schema: run `supabase_schema.sql` in the Supabase SQL editor, then
`enable_rls.sql`.

## Tests

```bash
python run_all_tests.py          # full suite: environment, database, solver, security
python test_fichiers_excel.py    # the 20 Excel files, constraint by constraint
python stress_test_solveur.py    # 255 instances, edge cases and random
python benchmark_v2.py           # solver benchmark with optimality gap
python verifier_planning.py <file.xlsx>
```

## Architecture

```
app.py                         Streamlit UI, authentication, Gantt, KPIs
backend/
  solver/
    input_parser.py            Excel → solver structures, business validation
    model.py                   CP-SAT model (v2, native formulation)
    model_v1.py                original MILP-style model, kept for comparison
  database.py                  Supabase, PBKDF2 passwords, signed session tokens
  gantt_builder.py             Plotly Gantt chart
  kpi_calculator.py            load, profit and margin
  template_excel.py            downloadable input template
verifier_planning.py           independent constraint checker
```

Security note: passwords use PBKDF2-SHA256 with 200 000 iterations and a
per-user salt; sessions use HMAC-signed tokens with sliding renewal.

## Input format

Four sheets, exact names required. The template is downloadable from the import
screen and contains a worked example.

| Sheet | Contents |
|---|---|
| `⚙ PARAMETRES` | nbJobs, nbMchs, nbOps, nbtechs, cte (setup duration) |
| `📋 GAMMES` | one row per operation: op_id, job_id, pos, work order, part name |
| `🔧 MODES & PT` | one row per (operation, eligible machine) with its duration |
| `👷 TECHNICIENS` | tech_id → machine_id |

Business rule enforced at import: a technician may cover several machines, but
**each machine has exactly one technician**. Overlapping coverage would force a
changeover from every assigned technician on every operation, silently inflating
the schedule — so the file is rejected with an explicit message instead.

## Known limitations

- **Travel time** between machines is not modelled: a technician moves
  instantly, only the setup duration applies.
- **Technician shifts and breaks** are not modelled; availability is continuous.
- Test data is **synthetic** — no real workshop extract has been run through it.
- Large instances return a good schedule, not a proven optimum. The app reports
  the gap to the lower bound so the quality is explicit.
