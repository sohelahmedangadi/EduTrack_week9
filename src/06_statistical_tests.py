"""
Week 6, Step 6: Hypothesis tests (is a difference real, or just random noise?).

Run from the project root:   python src/06_statistical_tests.py
Reads : data/processed/student_model_table.csv, interactions_joined.csv
Writes: outputs/week6/statistical_tests.csv
        outputs/week6/figures/city_boxplot.png, engagement_vs_quiz.png

Significance level: p < 0.05. Because we run many tests, we also show a Bonferroni-adjusted
p-value (p x number of tests). A result that is still below 0.05 after that is very safe.

NOTE: the data has no school_id and no grade, so we test CITY (stand-in for school),
COURSE (stand-in for subject) and PROFILE. Grade cannot be tested.
"""
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

warnings.filterwarnings("ignore")

students = pd.read_csv("data/processed/student_model_table.csv")
joined = pd.read_csv("data/processed/interactions_joined.csv")

results = []


def kruskal_and_anova(df, group_col, value_col, group_label, value_label):
    """Compare a number across several groups with Kruskal-Wallis and ANOVA."""
    data = df[[group_col, value_col]].dropna()
    groups = [g[value_col].values for _, g in data.groupby(group_col)]
    k, n = len(groups), len(data)
    h, p_kw = stats.kruskal(*groups)
    f, p_an = stats.f_oneway(*groups)
    eps2 = max((h - k + 1) / (n - k), 0)          # effect size for Kruskal-Wallis
    results.append({"area": group_label, "question": f"{value_label} differs across {k} groups",
                    "test": "Kruskal-Wallis", "statistic": round(h, 2), "p_value": p_kw,
                    "effect_size": round(eps2, 3), "effect_name": "epsilon-squared"})
    results.append({"area": group_label, "question": f"{value_label} differs across {k} groups",
                    "test": "One-way ANOVA", "statistic": round(f, 2), "p_value": p_an,
                    "effect_size": round(eps2, 3), "effect_name": "epsilon-squared"})


def chi_square(df, group_col, flag_col, group_label, flag_label):
    """Compare a yes/no outcome across groups."""
    table = pd.crosstab(df[group_col], df[flag_col])
    chi2, p, dof, _ = stats.chi2_contingency(table)
    v = np.sqrt(chi2 / (table.values.sum() * (min(table.shape) - 1)))     # Cramer's V
    results.append({"area": group_label, "question": f"{flag_label} rate differs across groups",
                    "test": "Chi-square", "statistic": round(chi2, 2), "p_value": p,
                    "effect_size": round(v, 3), "effect_name": "Cramer's V"})


# ---------------------------------------------------------------
# 1. Across cities (stand-in for the 15 schools)
# ---------------------------------------------------------------
kruskal_and_anova(students, "city", "avg_quiz_score", "City (school stand-in)", "Average quiz score")
kruskal_and_anova(students, "city", "avg_completion_pct", "City (school stand-in)", "Average completion %")
kruskal_and_anova(students, "city", "n_interactions", "City (school stand-in)", "Courses per student")
kruskal_and_anova(students, "city", "total_hours", "City (school stand-in)", "Total hours")
chi_square(students, "city", "at_risk_label", "City (school stand-in)", "At-risk")

# ---------------------------------------------------------------
# 2. Across courses (stand-in for subjects)
# ---------------------------------------------------------------
kruskal_and_anova(joined, "course_id", "quiz_score", "Course (subject stand-in)", "Quiz score")
kruskal_and_anova(joined, "course_id", "hours_spent", "Course (subject stand-in)", "Hours spent")
chi_square(joined, "course_id", "completed", "Course (subject stand-in)", "Completion")

# ---------------------------------------------------------------
# 3. Across student profiles
# ---------------------------------------------------------------
kruskal_and_anova(students, "profile", "avg_quiz_score", "Student profile", "Average quiz score")
chi_square(students, "profile", "at_risk_label", "Student profile", "At-risk")

# ---------------------------------------------------------------
# 4. Engagement vs assessment: correlations
# ---------------------------------------------------------------
pairs = [("total_hours", "avg_quiz_score"), ("avg_hours_per_course", "avg_quiz_score"),
         ("n_interactions", "avg_quiz_score"), ("avg_active_days", "avg_quiz_score")]
for x_col, y_col in pairs:
    pair = students[[x_col, y_col]].dropna()
    rho, p_s = stats.spearmanr(pair[x_col], pair[y_col])
    r, p_p = stats.pearsonr(pair[x_col], pair[y_col])
    results.append({"area": "Engagement vs score", "question": f"{x_col} vs {y_col}",
                    "test": "Spearman correlation", "statistic": round(rho, 3), "p_value": p_s,
                    "effect_size": round(rho, 3), "effect_name": "rho"})
    results.append({"area": "Engagement vs score", "question": f"{x_col} vs {y_col}",
                    "test": "Pearson correlation", "statistic": round(r, 3), "p_value": p_p,
                    "effect_size": round(r, 3), "effect_name": "r"})

# ---------------------------------------------------------------
# 5. High vs low engagement cohorts: t-test and Mann-Whitney
# ---------------------------------------------------------------
def high_vs_low(high, low, label):
    t, p_t = stats.ttest_ind(high, low, equal_var=False)         # Welch t-test
    u, p_u = stats.mannwhitneyu(high, low, alternative="two-sided")
    pooled_sd = np.sqrt((high.std(ddof=1) ** 2 + low.std(ddof=1) ** 2) / 2)
    d = (high.mean() - low.mean()) / pooled_sd                   # Cohen's d
    results.append({"area": "High vs low engagement", "question": label, "test": "Welch t-test",
                    "statistic": round(t, 2), "p_value": p_t, "effect_size": round(d, 3), "effect_name": "Cohen's d"})
    results.append({"area": "High vs low engagement", "question": label, "test": "Mann-Whitney U",
                    "statistic": round(u, 1), "p_value": p_u, "effect_size": round(d, 3), "effect_name": "Cohen's d"})
    return high.mean(), low.mean()


median_hours = students["total_hours"].median()
high_h = students.loc[students["total_hours"] > median_hours, "avg_quiz_score"].dropna()
low_h = students.loc[students["total_hours"] <= median_hours, "avg_quiz_score"].dropna()
m_hi, m_lo = high_vs_low(high_h, low_h, f"Quiz score: total hours above vs at/below median ({median_hours:.0f} h)")
print(f"High-hours students: mean quiz {m_hi:.1f} (n={len(high_h)}); low-hours: {m_lo:.1f} (n={len(low_h)})")

high_n = students.loc[students["n_interactions"] >= 5, "avg_quiz_score"].dropna()
low_n = students.loc[students["n_interactions"] <= 3, "avg_quiz_score"].dropna()
m_hi2, m_lo2 = high_vs_low(high_n, low_n, "Quiz score: 5-6 courses vs 2-3 courses")
print(f"5-6 courses: mean quiz {m_hi2:.1f} (n={len(high_n)}); 2-3 courses: {m_lo2:.1f} (n={len(low_n)})")

# ---------------------------------------------------------------
# 6. Collect results
# ---------------------------------------------------------------
res = pd.DataFrame(results)
res["p_bonferroni"] = (res["p_value"] * len(res)).clip(upper=1)
res["significant_p_lt_0.05"] = np.where(res["p_value"] < 0.05, "Yes", "No")
res["still_significant_after_bonferroni"] = np.where(res["p_bonferroni"] < 0.05, "Yes", "No")
res["p_value"] = res["p_value"].map(lambda p: float(f"{p:.3g}"))
res["p_bonferroni"] = res["p_bonferroni"].map(lambda p: float(f"{p:.3g}"))
res.to_csv("outputs/week6/statistical_tests.csv", index=False)
print(res[["area", "question", "test", "statistic", "p_value", "effect_size", "significant_p_lt_0.05", "still_significant_after_bonferroni"]].to_string(index=False))

# ---------------------------------------------------------------
# 7. Charts
# ---------------------------------------------------------------
# quiz score by city
order = students.groupby("city")["avg_quiz_score"].median().sort_values().index
plt.figure(figsize=(8, 4.5))
plt.boxplot([students.loc[students["city"] == c, "avg_quiz_score"].dropna() for c in order],
            showfliers=False)
plt.xticks(range(1, len(order) + 1), order, rotation=45); plt.ylabel("Average quiz score")
plt.title("Student quiz scores by city (school stand-in)"); plt.tight_layout()
plt.savefig("outputs/week6/figures/city_boxplot.png", dpi=150); plt.close()

# engagement vs quiz
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3))
axes[0].scatter(students["total_hours"], students["avg_quiz_score"], s=14, alpha=0.5, color="#2E86C1")
pair = students[["total_hours", "avg_quiz_score"]].dropna()
slope, intercept = np.polyfit(pair["total_hours"], pair["avg_quiz_score"], 1)
xs = np.linspace(pair["total_hours"].min(), pair["total_hours"].max(), 50)
axes[0].plot(xs, slope * xs + intercept, color="#C0392B")
rho = stats.spearmanr(pair["total_hours"], pair["avg_quiz_score"])[0]
axes[0].set_xlabel("Total hours per student"); axes[0].set_ylabel("Average quiz score")
axes[0].set_title(f"Hours vs quiz score (Spearman rho = {rho:.2f})")
axes[1].boxplot([low_h, high_h], showfliers=False)
axes[1].set_xticks([1, 2]); axes[1].set_xticklabels(["Low hours\n(at/below median)", "High hours\n(above median)"])
axes[1].set_ylabel("Average quiz score"); axes[1].set_title("High vs low engagement cohorts")
plt.tight_layout(); plt.savefig("outputs/week6/figures/engagement_vs_quiz.png", dpi=150); plt.close()
