"""
Week 6, Step 5: Student segmentation (K-Means) and cohort / drop-off analysis.

Run from the project root:   python src/05_segmentation_and_cohorts.py
Reads : data/processed/student_model_table.csv, interactions_joined.csv
Writes: outputs/week6/segment_profiles.csv, student_segments.csv
        outputs/week6/cohort_completion_by_course_number.csv
        outputs/week6/dropoff_curve.csv, monthly_trend.csv, cohort_notes.txt
        outputs/week6/figures/segments.png, cohort_heatmap.png, dropoff_curve.png, monthly_trend.png
"""
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

warnings.filterwarnings("ignore")
notes = []


def note(text):
    print(text)
    notes.append(text)


students = pd.read_csv("data/processed/student_model_table.csv")
joined = pd.read_csv("data/processed/interactions_joined.csv",
                     parse_dates=["enrollment_date", "last_activity_date", "joined_date"])

# ===============================================================
# PART A: Segmentation with K-Means
# ===============================================================
cluster_cols = ["avg_completion_pct", "avg_quiz_score", "avg_hours_per_course", "n_interactions"]
Z = StandardScaler().fit_transform(students[cluster_cols])

for k in range(2, 7):
    km = KMeans(n_clusters=k, n_init=20, random_state=42).fit(Z)
    note(f"k={k}: silhouette = {silhouette_score(Z, km.labels_):.3f}")
note("Silhouette scores are low and similar for every k, so the groups overlap. We use k=4 because it gives four easy-to-explain tiers.")

km = KMeans(n_clusters=4, n_init=20, random_state=42).fit(Z)
students["cluster"] = km.labels_

# give each cluster a name using simple rules on its averages
means = students.groupby("cluster")[["avg_completion_pct", "avg_quiz_score"]].mean()
names = {}
names[means["avg_quiz_score"].idxmin()] = "At-Risk Struggling"             # lowest quiz scores
names[means["avg_quiz_score"].idxmax()] = "Disengaged High-Scorers"        # highest quiz scores
left = [c for c in means.index if c not in names]
names[means.loc[left, "avg_completion_pct"].idxmax()] = "High Achievers"   # highest completion of the rest
for c in left:
    if c not in names:
        names[c] = "Steady / Average"
students["segment"] = students["cluster"].map(names)

profile = students.groupby("segment").agg(
    students=("student_id", "count"),
    avg_completion_pct=("avg_completion_pct", "mean"),
    avg_quiz_score=("avg_quiz_score", "mean"),
    avg_hours_per_course=("avg_hours_per_course", "mean"),
    courses_per_student=("n_interactions", "mean"),
    at_risk_label_pct=("at_risk_label", lambda s: s.mean() * 100),
).round(1).reset_index()
profile["share_of_students_pct"] = (profile["students"] / len(students) * 100).round(1)
order = ["High Achievers", "Steady / Average", "Disengaged High-Scorers", "At-Risk Struggling"]
profile["segment"] = pd.Categorical(profile["segment"], order, ordered=True)
profile = profile.sort_values("segment")
profile.to_csv("outputs/week6/segment_profiles.csv", index=False)
students[["student_id", "segment"]].to_csv("outputs/week6/student_segments.csv", index=False)
print(profile.to_string(index=False))

colors = {"High Achievers": "#1E8449", "Steady / Average": "#2E86C1",
          "Disengaged High-Scorers": "#F39C12", "At-Risk Struggling": "#C0392B"}
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for seg in order:
    sub = students[students["segment"] == seg]
    axes[0].scatter(sub["avg_completion_pct"], sub["avg_quiz_score"], s=18, alpha=0.7,
                    color=colors[seg], label=seg)
axes[0].set_xlabel("Average completion %"); axes[0].set_ylabel("Average quiz score")
axes[0].set_title("Student segments"); axes[0].legend(fontsize=8)
axes[1].bar(range(4), profile["at_risk_label_pct"], color=[colors[s] for s in order])
axes[1].set_xticks(range(4)); axes[1].set_xticklabels(["High\nAchievers", "Steady /\nAverage", "Disengaged\nHigh-Scorers", "At-Risk\nStruggling"], fontsize=8)
axes[1].set_ylabel("% of students labelled at risk"); axes[1].set_title("At-risk rate by segment")
plt.tight_layout(); plt.savefig("outputs/week6/figures/segments.png", dpi=150); plt.close()

# ===============================================================
# PART B: Cohort analysis
# ===============================================================
# B1. Cohort = quarter the student joined. Columns = 1st, 2nd, 3rd... course they enrolled in.
j = joined.sort_values(["student_id", "enrollment_date"]).copy()
j["course_number"] = j.groupby("student_id").cumcount() + 1
j["join_quarter"] = j["joined_date"].dt.to_period("Q").astype(str)
heat = j[j["course_number"] <= 5].pivot_table(index="join_quarter", columns="course_number",
                                              values="completed", aggfunc="mean") * 100
counts = j[j["course_number"] <= 5].pivot_table(index="join_quarter", columns="course_number",
                                                values="completed", aggfunc="count")
heat.round(1).to_csv("outputs/week6/cohort_completion_by_course_number.csv")

fig, ax = plt.subplots(figsize=(7.5, 4.5))
im = ax.imshow(heat.values, cmap="RdYlGn", vmin=35, vmax=80, aspect="auto")
for r in range(heat.shape[0]):
    for c in range(heat.shape[1]):
        ax.text(c, r, f"{heat.values[r, c]:.0f}%\n(n={int(counts.values[r, c])})", ha="center", va="center", fontsize=8)
ax.set_xticks(range(heat.shape[1])); ax.set_xticklabels([f"Course {c}" for c in heat.columns])
ax.set_yticks(range(heat.shape[0])); ax.set_yticklabels(heat.index)
ax.set_xlabel("Order in which the student enrolled"); ax.set_ylabel("Join quarter (cohort)")
ax.set_title("Completion rate by cohort and course number")
plt.colorbar(im, label="Completion rate %"); plt.tight_layout()
plt.savefig("outputs/week6/figures/cohort_heatmap.png", dpi=150); plt.close()
note(f"Cohort heatmap range: {np.nanmin(heat.values):.0f}% to {np.nanmax(heat.values):.0f}% (small cells have n under 30, read with care)")
note(f"Completion rate by course number (all cohorts): " +
     ", ".join(f"#{k}: {v:.0f}%" for k, v in (j.groupby('course_number')['completed'].mean() * 100).head(5).items()))

# B2. When do students stop? Share of courses still active after N days
days = np.arange(0, 61)
curve = pd.DataFrame({"day": days})
for label, flag in [("completed", 1), ("not_completed", 0)]:
    spans = j.loc[j["completed"] == flag, "active_days"]
    curve[label] = [(spans > d).mean() * 100 for d in days]
curve.round(1).to_csv("outputs/week6/dropoff_curve.csv", index=False)

plt.figure(figsize=(7, 4.5))
plt.plot(curve["day"], curve["completed"], label="Completed courses", color="#1E8449")
plt.plot(curve["day"], curve["not_completed"], label="Not completed courses", color="#C0392B")
plt.xlabel("Days since enrolling in the course"); plt.ylabel("% of courses still active")
plt.title("When do students go quiet?"); plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
plt.savefig("outputs/week6/figures/dropoff_curve.png", dpi=150); plt.close()

nc = j.loc[j["completed"] == 0, "active_days"]
cp = j.loc[j["completed"] == 1, "active_days"]
note(f"Not-completed courses: median last activity at day {nc.median():.0f}, latest at day {nc.max():.0f}; "
     f"{(nc <= 14).mean()*100:.0f}% stop within 14 days, {(nc <= 30).mean()*100:.0f}% within 30 days.")
note(f"Completed courses: median active span {cp.median():.0f} days; only {(cp <= 14).mean()*100:.0f}% finish within 14 days.")

# B3. Monthly trend by enrollment month
j["enrol_month"] = j["enrollment_date"].dt.to_period("M").astype(str)
monthly = j.groupby("enrol_month").agg(
    enrollments=("interaction_id", "count"),
    completion_rate_pct=("completed", lambda s: s.mean() * 100),
    avg_hours=("hours_spent", "mean"),
    avg_quiz=("quiz_score", "mean"),
).round(1).reset_index()
monthly.to_csv("outputs/week6/monthly_trend.csv", index=False)
monthly_ok = monthly[monthly["enrollments"] >= 30]      # ignore months with very few records

fig, ax1 = plt.subplots(figsize=(9, 4.2))
ax1.plot(monthly_ok["enrol_month"], monthly_ok["completion_rate_pct"], color="#2E86C1", marker="o", label="Completion rate %")
ax1.set_ylabel("Completion rate %"); ax1.set_xlabel("Enrollment month")
ax1.tick_params(axis="x", rotation=60)
ax2 = ax1.twinx()
ax2.plot(monthly_ok["enrol_month"], monthly_ok["avg_hours"], color="#F39C12", marker="s", label="Average hours")
ax2.set_ylabel("Average hours per course")
ax1.set_title("Monthly engagement trend (months with 30+ enrollments)")
fig.legend(loc="upper right", bbox_to_anchor=(0.9, 0.88)); plt.tight_layout()
plt.savefig("outputs/week6/figures/monthly_trend.png", dpi=150); plt.close()
note(f"Monthly completion rate ranged from {monthly_ok['completion_rate_pct'].min():.0f}% to {monthly_ok['completion_rate_pct'].max():.0f}%.")

with open("outputs/week6/cohort_notes.txt", "w") as f:
    f.write("\n".join(notes) + "\n")
