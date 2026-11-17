"""
Week 6, Step 4: Train and validate an at-risk classifier.

Run from the project root:   python src/04_train_at_risk_model.py
Reads : data/processed/student_features.csv, interactions_joined.csv
Writes: data/processed/student_model_table.csv
        outputs/week6/model_metrics.csv
        outputs/week6/feature_importance.csv
        outputs/week6/model_notes.txt
        outputs/week6/figures/roc_curves.png, confusion_matrices.png, feature_importance.png

GROUND-TRUTH LABEL (proxy, because no manual at-risk list exists):
    at_risk_label = 1 if the student completed FEWER THAN HALF of the courses they enrolled in.
That label is built only from the "completed" column. So we do NOT use completed,
certificate_earned, completion_pct, rating or the missing-quiz flag as model inputs,
because they would give the answer away (data leakage).
"""
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, RepeatedStratifiedKFold, cross_validate
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.inspection import permutation_importance
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, roc_curve, confusion_matrix)

warnings.filterwarnings("ignore")
SEED = 42
notes = []


def note(text):
    print(text)
    notes.append(text)


# ---------------------------------------------------------------
# 1. Build the student table (features + label)
# ---------------------------------------------------------------
students = pd.read_csv("data/processed/student_features.csv")
joined = pd.read_csv("data/processed/interactions_joined.csv")

# share of courses done on mobile / tablet
device = joined.pivot_table(index="student_id", columns="device", values="interaction_id",
                            aggfunc="count", fill_value=0)
device = device.div(device.sum(axis=1), axis=0).add_prefix("share_").reset_index()

# a few extra summary columns (all based on hours and quiz scores only)
extra = joined.groupby("student_id").agg(
    max_hours=("hours_spent", "max"),
    min_hours=("hours_spent", "min"),
    max_quiz=("quiz_score", "max"),
    min_quiz=("quiz_score", "min"),
).reset_index()

data = students.merge(device, on="student_id").merge(extra, on="student_id")

# the label
data["at_risk_label"] = (data["completion_rate"] < 0.5).astype(int)

feature_cols = ["n_interactions", "total_hours", "avg_hours_per_course", "avg_quiz_score",
                "avg_active_days", "share_Mobile", "share_Tablet",
                "max_hours", "min_hours", "max_quiz", "min_quiz"]
data[feature_cols] = data[feature_cols].fillna(data[feature_cols].median())   # a few empty min/max values

data.to_csv("data/processed/student_model_table.csv", index=False)

X = data[feature_cols]
y = data["at_risk_label"]
note(f"students: {len(data)}; at-risk (label=1): {y.sum()} ({y.mean()*100:.1f}%)")
note(f"majority-class baseline accuracy (always predict 'not at risk'): {(1 - y.mean())*100:.1f}%")

# how does the Week 3 rule flag compare with this label?
rule_acc = accuracy_score(y, data["at_risk"])
rule_rec = recall_score(y, data["at_risk"])
note(f"Week 3 rule flag vs label: accuracy {rule_acc*100:.1f}%, recall {rule_rec*100:.1f}%")

# ---------------------------------------------------------------
# 2. 80/20 split (stratified so both sets have the same share of at-risk students)
# ---------------------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=SEED)
note(f"train: {len(X_train)} rows ({y_train.mean()*100:.1f}% at risk), test: {len(X_test)} rows ({y_test.mean()*100:.1f}% at risk)")

models = {
    "Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
    "Logistic Regression (balanced)": make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000)),
    "Decision Tree (depth 3)": DecisionTreeClassifier(max_depth=3, class_weight="balanced", random_state=SEED),
    "Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, random_state=SEED),
}

# 5-fold cross-validation repeated 10 times = 50 test folds (more stable than one split)
cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEED)

rows = []
fitted = {}
probs = {}
for name, model in models.items():
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1]
    fitted[name] = model
    probs[name] = prob

    cvres = cross_validate(model, X, y, cv=cv, n_jobs=-1,
                           scoring=["accuracy", "precision", "recall", "f1", "roc_auc"])
    rows.append({
        "model": name,
        "test_accuracy": accuracy_score(y_test, pred),
        "test_precision": precision_score(y_test, pred),
        "test_recall": recall_score(y_test, pred),
        "test_f1": f1_score(y_test, pred),
        "test_roc_auc": roc_auc_score(y_test, prob),
        "cv_accuracy_mean": cvres["test_accuracy"].mean(),
        "cv_accuracy_sd": cvres["test_accuracy"].std(),
        "cv_precision": cvres["test_precision"].mean(),
        "cv_recall": cvres["test_recall"].mean(),
        "cv_f1": cvres["test_f1"].mean(),
        "cv_roc_auc": cvres["test_roc_auc"].mean(),
    })

metrics = pd.DataFrame(rows).round(3)
metrics.to_csv("outputs/week6/model_metrics.csv", index=False)
print(metrics.to_string(index=False))

# ---------------------------------------------------------------
# 3. Forward-looking check: do EARLIER courses predict the LAST course?
# ---------------------------------------------------------------
j = joined.copy()
j["enrollment_date"] = pd.to_datetime(j["enrollment_date"])
j = j.sort_values(["student_id", "enrollment_date"])
j["seq"] = j.groupby("student_id").cumcount() + 1
j["n"] = j.groupby("student_id")["seq"].transform("max")
last = j[j["seq"] == j["n"]][["student_id", "completed"]].rename(columns={"completed": "last_done"})
earlier = j[j["seq"] < j["n"]].groupby("student_id").agg(
    prev_hours=("hours_spent", "mean"), prev_quiz=("quiz_score", "mean"),
    prev_completion=("completion_pct", "mean"), prev_done=("completed", "mean"),
    prev_days=("active_days", "mean")).reset_index()
fwd = last.merge(earlier, on="student_id")
fwd = fwd.fillna(fwd.median(numeric_only=True))
y_fwd = (fwd["last_done"] == 0).astype(int)
X_fwd = fwd[["prev_hours", "prev_quiz", "prev_completion", "prev_done", "prev_days"]]
fwd_model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
fwd_cv = cross_validate(fwd_model, X_fwd, y_fwd, cv=cv, n_jobs=-1, scoring=["accuracy", "roc_auc"])
note(f"FORWARD-LOOKING check (earlier courses -> last course not completed): "
     f"accuracy {fwd_cv['test_accuracy'].mean()*100:.1f}% (baseline {max(y_fwd.mean(), 1-y_fwd.mean())*100:.1f}%), "
     f"ROC AUC {fwd_cv['test_roc_auc'].mean():.3f} (0.5 = coin flip)")

# ---------------------------------------------------------------
# 4. Feature importance (logistic regression, the main model)
# ---------------------------------------------------------------
main = fitted["Logistic Regression"]
coef = main[-1].coef_[0]
perm = permutation_importance(main, X_test, y_test, scoring="roc_auc", n_repeats=30, random_state=SEED)
importance = pd.DataFrame({
    "feature": feature_cols,
    "std_coefficient": coef.round(3),
    "permutation_importance_auc_drop": perm.importances_mean.round(4),
    "direction": np.where(coef > 0, "raises risk", "lowers risk"),
}).sort_values("permutation_importance_auc_drop", ascending=False)
importance.to_csv("outputs/week6/feature_importance.csv", index=False)
print(importance.to_string(index=False))

# ---------------------------------------------------------------
# 5. Charts
# ---------------------------------------------------------------
# ROC curves
plt.figure(figsize=(6, 5))
for name in ["Logistic Regression", "Random Forest", "Decision Tree (depth 3)"]:
    fpr, tpr, _ = roc_curve(y_test, probs[name])
    plt.plot(fpr, tpr, label=f"{name} (AUC {roc_auc_score(y_test, probs[name]):.2f})")
plt.plot([0, 1], [0, 1], "k--", label="Coin flip")
plt.xlabel("False positive rate"); plt.ylabel("True positive rate")
plt.title("ROC curves on the 20% test set"); plt.legend(loc="lower right"); plt.tight_layout()
plt.savefig("outputs/week6/figures/roc_curves.png", dpi=150); plt.close()

# Confusion matrices for the two logistic regression versions
fig, axes = plt.subplots(1, 2, figsize=(9, 4))
for ax, name in zip(axes, ["Logistic Regression", "Logistic Regression (balanced)"]):
    cm = confusion_matrix(y_test, fitted[name].predict(X_test))
    ax.imshow(cm, cmap="Blues")
    for r in range(2):
        for c in range(2):
            ax.text(c, r, cm[r, c], ha="center", va="center", fontsize=16,
                    color="white" if cm[r, c] > cm.max() / 2 else "black")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Not at risk", "At risk"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Not at risk", "At risk"])
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual"); ax.set_title(name, fontsize=10)
plt.tight_layout(); plt.savefig("outputs/week6/figures/confusion_matrices.png", dpi=150); plt.close()

# Feature importance bar chart (top 8)
top = importance.head(8).iloc[::-1]
colors = ["#C0392B" if d == "raises risk" else "#2E86C1" for d in top["direction"]]
plt.figure(figsize=(7, 4.5))
plt.barh(top["feature"], top["permutation_importance_auc_drop"], color=colors)
plt.xlabel("Drop in ROC AUC when the feature is shuffled")
plt.title("What drives the at-risk prediction\n(red = raises risk, blue = lowers risk)")
plt.tight_layout(); plt.savefig("outputs/week6/figures/feature_importance.png", dpi=150); plt.close()

# ---------------------------------------------------------------
# 6. Save notes
# ---------------------------------------------------------------
with open("outputs/week6/model_notes.txt", "w") as f:
    f.write("\n".join(notes) + "\n")
