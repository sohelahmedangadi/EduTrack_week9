"""
Week 9, Step 7: Score every student for the dashboard.

Run from the project root:   python src/07_score_students.py
Reads : data/processed/student_model_table.csv, student_segments (outputs/week6)
Writes: data/processed/student_risk_scores.csv   (one row per student, used by the dashboard)
        outputs/week9/flag_validation.txt

How the risk probability is made:
  * Same logistic regression and 11 features as Week 6.
  * "Out-of-fold" scoring: each student is scored by a model that did NOT train on them
    (5-fold cross-validation). This keeps the watchlist honest, not over-optimistic.
How the flag works:
  * Flagged (at risk)  = risk probability >= FLAG_THRESHOLD
  * High tier          = probability >= HIGH_THRESHOLD, Medium tier = flagged but below that
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

FLAG_THRESHOLD = 0.40   # chosen so cross-validated accuracy stays above 80% with better recall than 0.50
HIGH_THRESHOLD = 0.60

data = pd.read_csv("data/processed/student_model_table.csv")
segments = pd.read_csv("outputs/week6/student_segments.csv")

feature_cols = ["n_interactions", "total_hours", "avg_hours_per_course", "avg_quiz_score",
                "avg_active_days", "share_Mobile", "share_Tablet",
                "max_hours", "min_hours", "max_quiz", "min_quiz"]
X = data[feature_cols]
y = data["at_risk_label"]

model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))

# 1. out-of-fold risk probability for every student
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
data["risk_probability"] = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]
data["flagged"] = (data["risk_probability"] >= FLAG_THRESHOLD).astype(int)

# 2. risk tier
data["risk_tier"] = "Low"
data.loc[data["risk_probability"] >= FLAG_THRESHOLD, "risk_tier"] = "Medium"
data.loc[data["risk_probability"] >= HIGH_THRESHOLD, "risk_tier"] = "High"

# 3. why was the student flagged? Fit one model on everyone, then see which features push risk UP
model.fit(X, y)
coef = model[-1].coef_[0]
z = model[0].transform(X)               # each student's standardised feature values
contribution = z * coef                 # positive number = pushes risk up

driver_text = {
    "avg_hours_per_course": "Low study hours",
    "total_hours": "Low study hours",
    "n_interactions": "High course load",
    "max_hours": "Uneven effort across courses",
    "avg_quiz_score": "Low quiz scores",
    "min_quiz": "Very low result in one course",
    "avg_active_days": "Short activity span",
    "min_hours": "Very little time on one course",
    "share_Mobile": "Mostly mobile use",
    "share_Tablet": "Mostly tablet use",
    "max_quiz": "Low best quiz score",
}
action_text = {
    "Low study hours": "Teacher check-in; agree weekly study goals",
    "High course load": "Review workload before new enrolments",
    "Uneven effort across courses": "Counsellor to review course priorities",
    "Low quiz scores": "Tutoring or revision support",
    "Very low result in one course": "Tutoring for the weakest course",
    "Short activity span": "Re-engagement nudge early in each course",
    "Very little time on one course": "Check whether a course was dropped",
    "Mostly mobile use": "Check device access and study setting",
    "Mostly tablet use": "Check device access and study setting",
    "Low best quiz score": "Tutoring or revision support",
}

top_drivers = []
actions = []
review_by = []
for i in range(len(data)):
    row = contribution[i]
    order = np.argsort(-row)                       # biggest push towards risk first
    names = []
    for k in order[:6]:
        label = driver_text[feature_cols[k]]
        if row[k] > 0.15 and label not in names:   # skip weak pushes and repeated labels
            names.append(label)
    names = names[:2]                              # keep the top two
    tier = data.loc[i, "risk_tier"]
    if tier == "Low":
        top_drivers.append("None (low risk)")      # do not list drivers for low-risk students
        actions.append("No action needed")
        review_by.append("-")
    elif len(names) == 0:
        top_drivers.append("No single dominant driver")
        actions.append("Monitor")
        review_by.append("Within 1 month")
    else:
        top_drivers.append(", ".join(names))
        actions.append(action_text[names[0]])
        review_by.append("Within 1 week" if tier == "High" else "Within 1 month")
data["top_risk_drivers"] = top_drivers
data["recommended_intervention"] = actions
data["review_by"] = review_by

# 4. add the Week 6 segment name and save
data = data.merge(segments, on="student_id", how="left")
keep = ["student_id", "city", "profile", "segment", "risk_probability", "risk_tier", "flagged",
        "top_risk_drivers", "recommended_intervention", "review_by", "n_interactions", "courses_completed",
        "total_hours", "avg_hours_per_course", "avg_quiz_score", "avg_completion_pct", "at_risk_label"]
data[keep].round(3).to_csv("data/processed/student_risk_scores.csv", index=False)

# 5. validation of the flag against the proxy label (out-of-fold, so a fair test)
flag = data["flagged"]
lines = [
    f"Flag rule: risk probability >= {FLAG_THRESHOLD} (High tier >= {HIGH_THRESHOLD})",
    f"Students flagged: {flag.sum()} of {len(data)} ({flag.mean()*100:.1f}%)",
    f"Tiers: " + ", ".join(f"{k} {v}" for k, v in data["risk_tier"].value_counts().items()),
    f"Cross-validated accuracy vs proxy label: {accuracy_score(y, flag)*100:.1f}%",
    f"Precision {precision_score(y, flag)*100:.1f}%, recall {recall_score(y, flag)*100:.1f}%, F1 {f1_score(y, flag)*100:.1f}%",
    "Proxy label = completed fewer than half of enrolled courses (no manual at-risk list available).",
]
print("\n".join(lines))
with open("outputs/week9/flag_validation.txt", "w") as f:
    f.write("\n".join(lines) + "\n")
