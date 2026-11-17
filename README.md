# EduTrack Schools Network: Data Pipeline, Baselines and Deep-Dive Analysis (Weeks 3 and 6)

A small, repeatable pipeline that turns three raw CSV files into clean, analysis-ready tables and a first set of baseline ("before") metrics.

## Important data limitations

These came out of the Week 1 data inventory and still apply:

- **No `school_id`, grade, or subject columns exist in any file.** School and grade breakdowns cannot be built from this data. As a temporary stand-in, results are grouped by **`city`** (for school) and **`course_id`** (for subject). Please read these as placeholders, not real school results.
- **`da_edtech_enrollments.csv` cannot be joined to students.** Its IDs look like `ST-01894`, student IDs look like `STU-0001`, and 0 of 497 rows match. It is cleaned and analysed on its own.
- **The at-risk flag is an initial rule, not a validated model.** There is no manual at-risk list yet, so the 80% accuracy target cannot be measured. The flag rate is reported only.

## Project structure

```
data/raw/          original CSV files (never edited)
data/processed/    cleaned and joined tables created by the pipeline
src/               the three pipeline scripts
outputs/           Week 3 baseline tables; outputs/week6/ holds Week 6 tables and figures
logs/              cleaning and join logs from the last run
notebooks/         space for exploration notebooks
run_all.sh         runs all three steps in order
```

## How to run

Requires Python 3.9+.

```bash
pip install -r requirements.txt
python src/01_clean_data.py
python src/02_build_student_table.py
python src/03_baseline_metrics.py
```

Or run all six steps at once with `./run_all.sh`. Run every command from the project root folder.

## What each step does

| Step | Script | What it does |
|---|---|---|
| 1 | `src/01_clean_data.py` | Trims text, makes capitalisation consistent, converts dates to a standard format, converts Yes/No to 1/0, removes duplicates, blanks out impossible values, flags very high hours (kept, not removed). Keeps missing quiz scores as a signal. |
| 2 | `src/02_build_student_table.py` | Joins interactions to students on `student_id`, logs orphans, flags enrollments that do not match any student, builds one row per student with features, and applies the at-risk rule. |
| 3 | `src/03_baseline_metrics.py` | Calculates network-wide benchmarks and breakdowns by city, course, profile, and (separately) enrollment course. |
| 4 | `src/04_train_at_risk_model.py` | Week 6: trains and validates the at-risk classifier (80/20 split plus repeated cross-validation). |
| 5 | `src/05_segmentation_and_cohorts.py` | Week 6: K-Means student segments, cohort heatmap, drop-off curve, monthly trend. |
| 6 | `src/06_statistical_tests.py` | Week 6: ANOVA, Kruskal-Wallis, chi-square, correlations and high vs low engagement tests. |

### Join logic

`students (500)` joined to `interactions (2,044)` on `student_id`: 0 orphan interactions, 0 students without activity. Enrollments are checked against students and kept separate.

### Features created (`data/processed/student_features.csv`)

`n_interactions`, `total_hours`, `avg_hours_per_course`, `avg_completion_pct`, `avg_quiz_score`, `courses_completed`, `completion_rate`, `avg_active_days`, `avg_rating`, `quiz_missing_count`, `at_risk`.

### At-risk rule (first version)

A student is flagged if **average completion % is below 60 OR average quiz score is below 50**. The two thresholds are set at the top of `src/02_build_student_table.py` so they are easy to change.

## Baseline results

Full tables are in `outputs/baseline_summary.md`.

### Network-wide

| Metric | Value |
|---|---|
| Students | 500 |
| Course records (interactions) | 2,044 |
| Average quiz score | 62.9% |
| Course completion rate | 57.4% |
| Interactions per student | 4.09 |
| Average hours per student | 83.6 |
| Students flagged at risk | 22.0% (110 of 500) |

### By city (temporary stand-in for school)

| City | Students | Avg quiz score | Completion rate % | At-risk % |
|---|---|---|---|---|
| Ahmedabad | 42 | 66.7 | 63.3 | 14.3 |
| Hyderabad | 46 | 64.8 | 57.8 | 19.6 |
| Kolkata | 66 | 64.5 | 59.4 | 21.2 |
| Jaipur | 39 | 63.9 | 59.1 | 15.4 |
| Chennai | 62 | 63.3 | 58.4 | 19.4 |
| Mumbai | 59 | 63.2 | 58.6 | 22.0 |
| Pune | 45 | 62.1 | 63.3 | 17.8 |
| Kochi | 49 | 60.4 | 54.7 | 28.6 |
| Bengaluru | 41 | 59.8 | 53.9 | 29.3 |
| Delhi | 51 | 59.4 | 50.2 | 31.4 |

### By course (stand-in for subject): top 3 and bottom 3 by completion rate

| Course ID | Records | Avg quiz score | Completion rate % |
|---|---|---|---|
| CRS-003 | 154 | 66.6 | 78.6 |
| CRS-010 | 136 | 65.5 | 74.3 |
| CRS-014 | 133 | 65.8 | 72.9 |
| CRS-009 | 130 | 58.6 | 37.7 |
| CRS-004 | 117 | 58.4 | 37.6 |
| CRS-012 | 136 | 54.6 | 34.6 |

## Next steps

- Obtain `school_id`, grade, subject and term data so the real school comparison can replace the city stand-in.
- Get a manual at-risk list from teachers to test the 80% accuracy target.
- Get a student ID mapping so enrollments can be joined.

## Week 6 deep-dive results

All outputs are in `outputs/week6/` (tables as CSV, charts in `figures/`). The written report is `reports/EduTrack_Week6_Deep_Dive_Report.docx`.

**How "at-risk" is defined.** No manual at-risk list exists, so the label is a proxy: a student is at risk if they completed **fewer than half** of the courses they enrolled in (141 of 500 students, 28.2%). Columns that give the label away (completed, certificate_earned, completion_pct, rating, missing-quiz flag) are not used as model inputs. Replace the label with the teachers' own list when available.

### Model (stratified 80/20 split, seed 42; repeated 5-fold CV)

| Model | Accuracy | Precision | Recall | F1 | ROC AUC | CV accuracy |
|---|---|---|---|---|---|---|
| Logistic Regression | 81.0% | 69.6% | 57.1% | 62.7% | 0.84 | 81.7% ± 2.7 |
| Logistic Regression (balanced) | 75.0% | 53.7% | 78.6% | 63.8% | 0.84 | 77.6% ± 3.1 |
| Decision Tree (depth 3) | 74.0% | 52.4% | 78.6% | 62.9% | 0.80 | 73.9% ± 5.0 |
| Random Forest | 76.0% | 59.1% | 46.4% | 52.0% | 0.82 | 80.7% ± 3.1 |

Always predicting "not at risk" scores 71.8%. The standard logistic regression meets the 80% target on this proxy label; the balanced version finds more at-risk students but does not. Earlier-course behaviour does **not** predict the last course (AUC 0.54), so this is a current-status model, not an early-warning model.

Top drivers: average hours per course (strongest), courses per student, longest single-course hours, total hours, average quiz score.

### Segments (K-Means, k = 4)

| Segment | Students | Labelled at risk |
|---|---|---|
| High Achievers | 147 | 2.7% |
| Steady / Average | 179 | 20.7% |
| Disengaged High-Scorers | 75 | 36.0% |
| At-Risk Struggling | 99 | 73.7% |

### Drop-off and statistics

- Courses that are not completed go quiet at a median of day 22; about two thirds stop within 30 days.
- Courses differ strongly in completion, hours and quiz score (all p < 0.001). Cities (school stand-in) show no reliable differences. Hours per course vs quiz score: Spearman rho = 0.15 (p < 0.001).
- Grade cannot be tested: there is no grade column.
