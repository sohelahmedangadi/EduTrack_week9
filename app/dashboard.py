"""
EduTrack Schools Network - Dashboard v1 (Streamlit)

Run from the project root:   streamlit run app/dashboard.py

Data used (created by the pipeline in src/):
  data/processed/student_risk_scores.csv   one row per student (risk probability, tier, drivers)
  data/processed/interactions_joined.csv   one row per student + course

IMPORTANT data limits (shown in the app too):
  * There is no school_id in the data, so CITY is used as a stand-in for school (10 cities, not 15 schools).
  * There is no grade column, so the Grade filter is switched off.
  * There is no subject column, so COURSE ID is used as a stand-in for subject.
"""
from pathlib import Path
import pandas as pd
import altair as alt
import streamlit as st
from fpdf import FPDF
from fpdf.fonts import FontFace

ROOT = Path(__file__).resolve().parent.parent      # project root, so the app runs from any folder

st.set_page_config(page_title="EduTrack Dashboard v1", page_icon=":bar_chart:", layout="wide")

TIER_COLORS = {"Low": "#2E8B57", "Medium": "#E69500", "High": "#C0392B"}
TIER_BADGE = {"Low": "🟢 Low", "Medium": "🟠 Medium", "High": "🔴 High"}
DARK, LIGHT = "#1F3864", "#A9BAD8"


# ---------------------------------------------------------------
# 1. Load data (cached so the app stays fast)
# ---------------------------------------------------------------
@st.cache_data
def load_data():
    students = pd.read_csv(ROOT / "data/processed/student_risk_scores.csv")
    records = pd.read_csv(ROOT / "data/processed/interactions_joined.csv", parse_dates=["enrollment_date"])
    records = records[["student_id", "course_id", "city", "completed", "quiz_score", "hours_spent", "enrollment_date"]]
    records["flagged"] = records["student_id"].map(students.set_index("student_id")["flagged"])
    return students, records


students, records = load_data()

# ---------------------------------------------------------------
# 2. Global filters (sidebar, so they stay the same on every tab)
# ---------------------------------------------------------------
st.sidebar.title("Filters")
school = st.sidebar.selectbox("School (city used as stand-in)", ["All schools"] + sorted(records["city"].unique()), key="school")
st.sidebar.selectbox("Grade", ["Not available in data"], disabled=True, key="grade",
                     help="The data has no grade column, so this filter cannot work yet.")
subject = st.sidebar.selectbox("Subject (course used as stand-in)", ["All subjects"] + sorted(records["course_id"].unique()), key="subject")
st.sidebar.caption("Filters apply to every tab. The flag and risk score are per student, across all of their courses.")
st.sidebar.divider()
st.sidebar.caption("Data: 500 students, 2,044 course records. Risk model: logistic regression, "
                   "81.8% cross-validated accuracy against a proxy label (see README).")

# apply the filters
rec = records.copy()
if school != "All schools":
    rec = rec[rec["city"] == school]
if subject != "All subjects":
    rec = rec[rec["course_id"] == subject]

st.title("EduTrack Academic Performance Dashboard")

if rec.empty:                                       # empty state
    st.warning("No data for this School + Subject combination. Choose another subject or school.")
    st.stop()

stu = students[students["student_id"].isin(rec["student_id"])]
n_students = len(stu)

# ---------------------------------------------------------------
# 3. KPI cards
# ---------------------------------------------------------------
def kpis(rec_df, stu_df):
    n = stu_df["student_id"].nunique()
    return {
        "students": n,
        "quiz": rec_df["quiz_score"].mean(),
        "completion": rec_df["completed"].mean() * 100,
        "hours": rec_df["hours_spent"].sum() / n,
        "courses": len(rec_df) / n,
        "risk": stu_df["flagged"].mean() * 100,
    }


k = kpis(rec, stu)
# Compare with the SAME subject across the whole network (so hours and completion are like-for-like)
net_rec = records if subject == "All subjects" else records[records["course_id"] == subject]
net = kpis(net_rec, students[students["student_id"].isin(net_rec["student_id"])])
filtered = school != "All schools"      # the comparison is only meaningful when one school is chosen


def delta(key, unit=""):
    return f"{k[key] - net[key]:+.1f}{unit} vs network" if filtered else None


c1, c2, c3, c4, c5 = st.columns(5)
with c1.container(border=True):
    st.metric("Students", f"{k['students']:,}", help="Students with at least one course record in the current filter.")
with c2.container(border=True):
    st.metric("Average quiz score", f"{k['quiz']:.1f}", delta=delta("quiz"))
with c3.container(border=True):
    st.metric("Completion rate", f"{k['completion']:.1f}%", delta=delta("completion", " pts"),
              help="Share of course records that were completed (used as the pass-rate stand-in). Deltas compare with the whole network for the same subject.")
with c4.container(border=True):
    st.metric("Avg hours / student", f"{k['hours']:.1f}", delta=delta("hours", " h"),
              help=f"Average platform hours per student. Courses per student: {k['courses']:.2f}.")
with c5.container(border=True):
    st.metric("At-risk students", f"{k['risk']:.1f}%", delta=delta("risk", " pts"), delta_color="inverse",
              help="Share of students flagged by the risk model (probability of 0.40 or more).")

if n_students < 20:
    st.info(f"Only {n_students} students match this filter, so averages can swing a lot. Read with care.")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "School comparison", "At-risk watchlist", "Term-end report"])

# ---------------------------------------------------------------
# TAB 1: Overview
# ---------------------------------------------------------------
with tab1:
    left, right = st.columns(2)

    with left:
        st.subheader("Performance by subject")
        metric_name = st.radio("Measure", ["Completion rate (%)", "Average quiz score", "Average hours per course"],
                               horizontal=True, key="subject_metric")
        col = {"Completion rate (%)": "completion", "Average quiz score": "quiz", "Average hours per course": "hours"}[metric_name]
        rec_school = records if school == "All schools" else records[records["city"] == school]
        by_course = rec_school.groupby("course_id").agg(
            records=("student_id", "count"), completion=("completed", lambda s: s.mean() * 100),
            quiz=("quiz_score", "mean"), hours=("hours_spent", "mean")).reset_index().round(1)
        by_course["highlight"] = (by_course["course_id"] == subject) | (subject == "All subjects")
        chart = alt.Chart(by_course).mark_bar().encode(
            y=alt.Y("course_id:N", sort="-x", title=None),
            x=alt.X(f"{col}:Q", title=metric_name),
            color=alt.Color("highlight:N", scale=alt.Scale(domain=[True, False], range=[DARK, LIGHT]), legend=None),
            tooltip=[alt.Tooltip("course_id", title="Course"), alt.Tooltip("records", title="Records"),
                     alt.Tooltip("completion", title="Completion %"), alt.Tooltip("quiz", title="Avg quiz"),
                     alt.Tooltip("hours", title="Avg hours")],
        ).properties(height=380)
        st.altair_chart(chart, width="stretch")
        st.caption("Subjects are shown for the selected school. The selected subject is highlighted.")

    with right:
        st.subheader("Risk tiers")
        tier_counts = stu["risk_tier"].value_counts().reindex(["High", "Medium", "Low"]).fillna(0).reset_index()
        tier_counts.columns = ["tier", "students"]
        chart = alt.Chart(tier_counts).mark_bar().encode(
            x=alt.X("tier:N", sort=["High", "Medium", "Low"], title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("students:Q", title="Students"),
            color=alt.Color("tier:N", scale=alt.Scale(domain=list(TIER_COLORS), range=list(TIER_COLORS.values())), legend=None),
            tooltip=["tier", "students"],
        ).properties(height=170)
        st.altair_chart(chart, width="stretch")

        st.subheader("Completion trend by enrollment month")
        monthly = rec.assign(month=rec["enrollment_date"].dt.to_period("M").dt.to_timestamp()).groupby("month").agg(
            records=("student_id", "count"), completion=("completed", lambda s: s.mean() * 100)).reset_index()
        monthly = monthly[monthly["records"] >= 15]       # hide months with too few records
        if len(monthly) < 3:
            st.info("Too few records per month to draw a trend for this filter.")
        else:
            line = alt.Chart(monthly).mark_line(point=True, color=DARK).encode(
                x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %y", labelAngle=-45)),
                y=alt.Y("completion:Q", title="Completion rate (%)", scale=alt.Scale(zero=False)),
                tooltip=[alt.Tooltip("month:T", format="%b %Y"), "records", alt.Tooltip("completion", format=".1f")],
            ).properties(height=200)
            st.altair_chart(line, width="stretch")
            st.caption("Months with fewer than 15 course records are hidden.")

# ---------------------------------------------------------------
# TAB 2: School comparison
# ---------------------------------------------------------------
with tab2:
    st.subheader("School comparison")
    st.caption("Cities are used as a stand-in for schools (the data has 10 cities, not 15 schools). "
               "Week 6 statistical tests found no reliable differences between cities, so treat the ranking as descriptive.")
    rec_sub = records if subject == "All subjects" else records[records["course_id"] == subject]
    school_stats = rec_sub.groupby("city").agg(
        students=("student_id", "nunique"), quiz=("quiz_score", "mean"),
        completion=("completed", lambda s: s.mean() * 100), hours_total=("hours_spent", "sum"),
    ).reset_index()
    school_stats["hours"] = school_stats["hours_total"] / school_stats["students"]
    risk_by_city = rec_sub.drop_duplicates("student_id").groupby("city")["flagged"].mean() * 100
    school_stats["risk"] = school_stats["city"].map(risk_by_city)
    school_stats = school_stats.drop(columns="hours_total").round(1)

    measure = st.radio("Compare schools on", ["Average quiz score", "Completion rate (%)", "Engagement (hours / student)", "At-risk students (%)"],
                       horizontal=True, key="school_metric")
    mcol = {"Average quiz score": "quiz", "Completion rate (%)": "completion",
            "Engagement (hours / student)": "hours", "At-risk students (%)": "risk"}[measure]
    school_stats["highlight"] = (school_stats["city"] == school) | (school == "All schools")
    network_value = school_stats[mcol].mean()
    bars = alt.Chart(school_stats).mark_bar().encode(
        y=alt.Y("city:N", sort="-x", title=None),
        x=alt.X(f"{mcol}:Q", title=measure),
        color=alt.Color("highlight:N", scale=alt.Scale(domain=[True, False], range=[DARK, LIGHT]), legend=None),
        tooltip=[alt.Tooltip("city", title="School (city)"), alt.Tooltip("students", title="Students"),
                 alt.Tooltip("quiz", title="Avg quiz"), alt.Tooltip("completion", title="Completion %"),
                 alt.Tooltip("hours", title="Hours / student"), alt.Tooltip("risk", title="At-risk %")],
    )
    avg_line = alt.Chart(pd.DataFrame({"v": [network_value]})).mark_rule(color="#C0392B", strokeDash=[5, 4]).encode(x="v:Q")
    st.altair_chart((bars + avg_line).properties(height=340), width="stretch")
    st.caption("Dashed line = average across the schools shown. The selected school is highlighted.")

    st.markdown("**Scorecard**")
    card = school_stats.drop(columns="highlight").sort_values(mcol, ascending=(mcol == "risk")).reset_index(drop=True)
    card.insert(0, "Rank", card.index + 1)
    st.dataframe(card, hide_index=True, width="stretch", column_config={
        "city": "School (city)", "students": "Students",
        "quiz": st.column_config.ProgressColumn("Avg quiz", min_value=0, max_value=100, format="%.1f"),
        "completion": st.column_config.ProgressColumn("Completion %", min_value=0, max_value=100, format="%.1f"),
        "hours": st.column_config.NumberColumn("Hours / student", format="%.1f"),
        "risk": st.column_config.ProgressColumn("At-risk %", min_value=0, max_value=100, format="%.1f"),
    })
    st.caption("Rank follows the measure chosen above (for at-risk %, rank 1 = lowest share).")

# ---------------------------------------------------------------
# TAB 3: At-risk watchlist
# ---------------------------------------------------------------
with tab3:
    st.subheader("At-risk student watchlist")
    f1, f2 = st.columns([2, 1])
    tiers = f1.multiselect("Risk tier", ["High", "Medium"], default=["High", "Medium"], key="tiers")
    search = f2.text_input("Search student ID", placeholder="e.g. STU-0003", key="search")

    watch = stu[(stu["flagged"] == 1) & (stu["risk_tier"].isin(tiers))]
    if search:
        watch = watch[watch["student_id"].str.contains(search.strip(), case=False)]
    watch = watch.sort_values("risk_probability", ascending=False)

    if watch.empty:
        st.info("No flagged students match these settings.")
    else:
        st.caption(f"Showing {len(watch)} flagged students of {int(stu['flagged'].sum())} flagged in the current filter. "
                   "Sorted by risk, highest first. Student IDs only; no names are shown.")
        table = pd.DataFrame({
            "Student": watch["student_id"],
            "School (city)": watch["city"],
            "Risk": (watch["risk_probability"] * 100).round(0),
            "Tier": watch["risk_tier"].map(TIER_BADGE),
            "Review by": watch["review_by"],
            "Why flagged (top drivers)": watch["top_risk_drivers"],
            "Recommended intervention": watch["recommended_intervention"],
            "Courses done": watch["courses_completed"].astype(int).astype(str) + " / " + watch["n_interactions"].astype(int).astype(str),
            "Avg quiz": watch["avg_quiz_score"].round(1),
        })
        st.dataframe(table, hide_index=True, width="stretch", height=440, column_config={
            "Risk": st.column_config.ProgressColumn("Risk %", min_value=0, max_value=100, format="%d%%"),
            "Student": st.column_config.TextColumn(width=85),
            "School (city)": st.column_config.TextColumn(width=100),
            "Tier": st.column_config.TextColumn(width=95),
            "Why flagged (top drivers)": st.column_config.TextColumn(width=290),
            "Recommended intervention": st.column_config.TextColumn(width=290),
            "Review by": st.column_config.TextColumn(width=110),
            "Courses done": st.column_config.TextColumn(width=105),
            "Avg quiz": st.column_config.NumberColumn(width=80),
        })
        st.download_button("Download watchlist (CSV)", table.to_csv(index=False).encode("utf-8"),
                           file_name="edutrack_watchlist.csv", mime="text/csv")
    st.caption("Drivers show which behaviours push a student's risk up (low hours, low quiz scores, and so on). "
               "Interventions are suggestions only; tracking whether an intervention happened needs a database (planned).")

# ---------------------------------------------------------------
# TAB 4: Term-end PDF report
# ---------------------------------------------------------------
def clean(text):
    """The built-in PDF fonts only handle basic Latin characters."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


class ReportPDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 6, f"EduTrack Dashboard v1  |  Page {self.page_no()}", align="C")


def make_pdf(school_name, subject_name, kpi, net_kpi, school_table, course_table, watch_df, compare=True):
    pdf = ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(14, 14, 14)
    pdf.add_page()
    head = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=(31, 56, 100))

    pdf.set_font("Helvetica", "B", 18); pdf.set_text_color(31, 56, 100)
    pdf.cell(0, 9, "EduTrack Schools Network", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12); pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 7, "Term-End Summary Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, clean(f"School: {school_name}   |   Grade: not available in data   |   Subject: {subject_name}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    def heading(text):
        pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(31, 56, 100)
        pdf.cell(0, 8, clean(text), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(30, 30, 30); pdf.set_font("Helvetica", "", 8)

    def draw_table(widths, header, rows, aligns=None):
        pdf.set_font("Helvetica", "", 8); pdf.set_text_color(30, 30, 30)
        with pdf.table(col_widths=widths, text_align=aligns or ("LEFT",) * len(widths), line_height=4.6,
                       headings_style=head, cell_fill_color=(242, 245, 250), cell_fill_mode="ROWS") as t:
            r = t.row()
            for h in header:
                r.cell(clean(h))
            for row in rows:
                r = t.row()
                for cell_value in row:
                    r.cell(clean(cell_value))
        pdf.ln(3)

    heading("Key indicators")
    draw_table((70, 40, 66), ("Measure", "Value", "Difference vs network (same subject)"), [
        ("Students", f"{kpi['students']:,}", "-"),
        ("Average quiz score", f"{kpi['quiz']:.1f}", f"{kpi['quiz'] - net_kpi['quiz']:+.1f}" if compare else "-"),
        ("Completion rate", f"{kpi['completion']:.1f}%", f"{kpi['completion'] - net_kpi['completion']:+.1f} pts" if compare else "-"),
        ("Engagement (hours per student)", f"{kpi['hours']:.1f}", f"{kpi['hours'] - net_kpi['hours']:+.1f} h" if compare else "-"),
        ("At-risk students", f"{kpi['risk']:.1f}%", f"{kpi['risk'] - net_kpi['risk']:+.1f} pts" if compare else "-"),
    ])

    if school_table is not None:
        heading("School comparison (city used as stand-in for school)")
        draw_table((46, 24, 26, 28, 28, 24), ("School (city)", "Students", "Avg quiz", "Completion %", "Hours / student", "At-risk %"),
                   [(r.city, r.students, f"{r.quiz:.1f}", f"{r.completion:.1f}", f"{r.hours:.1f}", f"{r.risk:.1f}")
                    for r in school_table.itertuples()], aligns=("LEFT",) + ("RIGHT",) * 5)

    heading("Subject performance (course used as stand-in for subject)")
    draw_table((40, 30, 36, 36, 34), ("Course", "Records", "Completion %", "Avg quiz", "Avg hours"),
               [(r.course_id, r.records, f"{r.completion:.1f}", f"{r.quiz:.1f}", f"{r.hours:.1f}")
                for r in course_table.itertuples()], aligns=("LEFT",) + ("RIGHT",) * 4)

    if pdf.will_page_break(60):          # start the watchlist on a fresh page if it would be squeezed
        pdf.add_page()
    heading("At-risk watchlist (top 15 by risk)")
    if watch_df.empty:
        pdf.cell(0, 6, "No flagged students for this selection.", new_x="LMARGIN", new_y="NEXT")
    else:
        top = watch_df.head(15)
        draw_table((20, 14, 15, 50, 55, 28), ("Student", "Risk %", "Tier", "Why flagged", "Recommended intervention", "Review by"),
                   [(r.student_id, f"{r.risk_probability * 100:.0f}", r.risk_tier, r.top_risk_drivers, r.recommended_intervention, r.review_by)
                    for r in top.itertuples()], aligns=("LEFT", "RIGHT", "LEFT", "LEFT", "LEFT", "LEFT"))
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, clean(f"{len(watch_df)} students flagged in total for this selection; first 15 shown."),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    heading("Notes")
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4.4, clean(
        "At-risk flag: logistic regression risk probability of 0.40 or more. Cross-validated accuracy is 81.8% against a proxy "
        "label (a student who completed fewer than half of their enrolled courses), because no manual at-risk list is available yet. "
        "School and subject are stand-ins (city and course ID); the data has no school ID, grade or subject columns. "
        "Interventions are suggestions for staff to review, not decisions."), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


with tab4:
    st.subheader("Term-end report (prototype)")
    st.write(f"The report covers the current selection: **{school}**, grade not available, **{subject}**. "
             "It includes key indicators, subject performance and the top 15 at-risk students"
             + (", plus a comparison of all schools." if school == "All schools" else "."))

    rec_for_report = rec
    course_report = rec_for_report.groupby("course_id").agg(
        records=("student_id", "count"), completion=("completed", lambda s: s.mean() * 100),
        quiz=("quiz_score", "mean"), hours=("hours_spent", "mean")).reset_index().round(1)
    school_report = school_stats.drop(columns="highlight") if school == "All schools" else None
    watch_report = stu[stu["flagged"] == 1].sort_values("risk_probability", ascending=False)

    pdf_bytes = make_pdf(school, subject, k, net, school_report, course_report, watch_report, compare=filtered)
    file_label = school.replace(" ", "_").lower()
    st.download_button("Generate and download term-end PDF report", pdf_bytes,
                       file_name=f"edutrack_term_report_{file_label}.pdf", mime="application/pdf", type="primary")
    st.caption("Prototype: layout and content will be refined after the peer review.")
