"""
Step 1: Clean the three raw CSV files.

Run from the project root:   python src/01_clean_data.py
Reads : data/raw/*.csv
Writes: data/processed/students_clean.csv
        data/processed/interactions_clean.csv
        data/processed/enrollments_clean.csv
        logs/01_cleaning_log.txt
"""
import pandas as pd

log = []   # we collect log lines here and save them at the end


def note(text):
    print(text)
    log.append(text)


# ---------------------------------------------------------------
# 1. Students
# ---------------------------------------------------------------
students = pd.read_csv("data/raw/edutrack_students.csv")
note(f"students: {len(students)} rows read")

# remove extra spaces and make text consistent
students["student_id"] = students["student_id"].str.strip().str.upper()
students["name"] = students["name"].str.strip().str.title()
students["email"] = students["email"].str.strip().str.lower()
students["city"] = students["city"].str.strip().str.title()
students["profile"] = students["profile"].str.strip()

# dates -> real dates (YYYY-MM-DD). Bad dates become empty (NaT)
students["joined_date"] = pd.to_datetime(students["joined_date"], errors="coerce")

# remove duplicate students (same student_id)
before = len(students)
students = students.drop_duplicates(subset="student_id", keep="first")
note(f"students: removed {before - len(students)} duplicate student_id rows")
note(f"students: {students['joined_date'].isna().sum()} missing/invalid joined_date")

# ---------------------------------------------------------------
# 2. Interactions
# ---------------------------------------------------------------
inter = pd.read_csv("data/raw/edutrack_interactions.csv")
note(f"interactions: {len(inter)} rows read")

inter["student_id"] = inter["student_id"].str.strip().str.upper()
inter["course_id"] = inter["course_id"].str.strip().str.upper()
inter["device"] = inter["device"].str.strip().str.title()

inter["enrollment_date"] = pd.to_datetime(inter["enrollment_date"], errors="coerce")
inter["last_activity_date"] = pd.to_datetime(inter["last_activity_date"], errors="coerce")

# Yes/No columns -> 1/0 so we can average them later
inter["completed"] = inter["completed"].str.strip().str.title().map({"Yes": 1, "No": 0})
inter["certificate_earned"] = inter["certificate_earned"].str.strip().str.title().map({"Yes": 1, "No": 0})

# remove duplicates
before = len(inter)
inter = inter.drop_duplicates(subset="interaction_id", keep="first")
inter = inter.drop_duplicates(subset=["student_id", "course_id"], keep="last")
note(f"interactions: removed {before - len(inter)} duplicate rows")

# invalid date range: last activity cannot be before enrollment
bad_dates = inter["last_activity_date"] < inter["enrollment_date"]
note(f"interactions: {bad_dates.sum()} rows with last_activity before enrollment (removed)")
inter = inter[~bad_dates]

# values outside the allowed range become empty
inter.loc[~inter["completion_pct"].between(0, 100), "completion_pct"] = None
inter.loc[~inter["quiz_score"].between(0, 100), "quiz_score"] = None
inter.loc[~inter["rating"].between(1, 5), "rating"] = None

# new helper columns
inter["active_days"] = (inter["last_activity_date"] - inter["enrollment_date"]).dt.days
inter["quiz_missing"] = inter["quiz_score"].isna().astype(int)   # missing quiz = signal, keep the row

# flag (do NOT remove) very high hours using the IQR rule
q1 = inter["hours_spent"].quantile(0.25)
q3 = inter["hours_spent"].quantile(0.75)
upper_fence = q3 + 1.5 * (q3 - q1)
inter["hours_outlier"] = (inter["hours_spent"] > upper_fence).astype(int)
note(f"interactions: {inter['hours_outlier'].sum()} rows flagged as hours outliers (> {upper_fence:.1f} h), kept")

note(f"interactions: missing quiz_score = {inter['quiz_score'].isna().sum()}, missing rating = {inter['rating'].isna().sum()}")

# ---------------------------------------------------------------
# 3. Enrollments
# ---------------------------------------------------------------
enr = pd.read_csv("data/raw/da_edtech_enrollments.csv")
note(f"enrollments: {len(enr)} rows read")

enr["enrol_id"] = enr["enrol_id"].str.strip().str.upper()
enr["student_id"] = enr["student_id"].str.strip().str.upper()
enr["course"] = enr["course"].str.strip()   # keep original capitalisation (e.g. "UI Design")
enr["mode"] = enr["mode"].str.strip().str.title()
enr["employment_outcome"] = enr["employment_outcome"].str.strip().str.title()
enr["enrol_date"] = pd.to_datetime(enr["enrol_date"], errors="coerce")

# same student + same course twice -> keep the most recent enrollment
before = len(enr)
enr = enr.sort_values("enrol_date").drop_duplicates(subset=["student_id", "course"], keep="last")
enr = enr.sort_values("enrol_id")
note(f"enrollments: removed {before - len(enr)} repeat student+course rows (kept latest)")

enr.loc[~enr["score_pct"].between(0, 100), "score_pct"] = None
note(f"enrollments: missing score_pct = {enr['score_pct'].isna().sum()}, missing employment_outcome = {enr['employment_outcome'].isna().sum()}")

# ---------------------------------------------------------------
# 4. Save
# ---------------------------------------------------------------
students.to_csv("data/processed/students_clean.csv", index=False)
inter.to_csv("data/processed/interactions_clean.csv", index=False)
enr.to_csv("data/processed/enrollments_clean.csv", index=False)
note(f"saved: students {len(students)}, interactions {len(inter)}, enrollments {len(enr)} rows")

with open("logs/01_cleaning_log.txt", "w") as f:
    f.write("\n".join(log) + "\n")
