import os
import io
import pandas as pd
import streamlit as st
import plotly.express as px
try:
    from groq import Groq
except ImportError:
    Groq = None
from dotenv import load_dotenv

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=groq_api_key) if Groq is not None and groq_api_key else None

st.set_page_config(
    page_title="Smart Data Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Header
st.markdown("""
<div style="background:#185FA5;padding:1.8rem 2rem;border-radius:16px;margin-bottom:1.5rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap">
    <div style="display:flex;align-items:center;justify-content:center;width:72px;height:72px;border-radius:20px;background:linear-gradient(135deg,#3FA9F5,#0F3F85);box-shadow:0 16px 40px rgba(0,0,0,0.18)">
        <svg width="40" height="40" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="8" y="28" width="10" height="28" rx="3" fill="white"/>
            <rect x="26" y="16" width="10" height="40" rx="3" fill="white"/>
            <rect x="44" y="8" width="10" height="48" rx="3" fill="white"/>
            <path d="M16 28C18.2091 28 20 26.2091 20 24C20 21.7909 18.2091 20 16 20C13.7909 20 12 21.7909 12 24C12 26.2091 13.7909 28 16 28Z" fill="#8BD3FF"/>
            <path d="M34 16C36.2091 16 38 14.2091 38 12C38 9.79086 36.2091 8 34 8C31.7909 8 30 9.79086 30 12C30 14.2091 31.7909 16 34 16Z" fill="#8BD3FF"/>
            <path d="M52 8C54.2091 8 56 6.20914 56 4C56 1.79086 54.2091 0 52 0C49.7909 0 48 1.79086 48 4C48 6.20914 49.7909 8 52 8Z" fill="#8BD3FF"/>
        </svg>
    </div>
    <div style="min-width:280px;flex:1 1 360px">
        <h1 style="color:white;font-size:32px;font-weight:700;letter-spacing:0.3px;margin:0">Smart Data Analyzer</h1>
        <p style="color:rgba(255,255,255,0.9);font-size:15px;line-height:1.6;margin:10px 0 0 0;max-width:720px">Upload, profile, clean, and visualize CSV data faster with intelligent charts and actionable AI insights.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def get_meaningful_numeric(df):
    skip_keywords = ["id", "code", "index", "no", "num", "serial", "key"]
    num_cols = df.select_dtypes(include="number").columns.tolist()
    meaningful = []
    for col in num_cols:
        col_lower = col.lower()
        is_id = any(col_lower == kw or col_lower.endswith("_" + kw) or col_lower.startswith(kw + "_") for kw in skip_keywords)
        if not is_id and df[col].nunique() / len(df) < 0.9:
            meaningful.append(col)
    return meaningful if meaningful else num_cols

def badge(text, good=True):
    if good:
        return f'<span style="background:#E6F1FB;color:#0C447C;padding:2px 10px;border-radius:99px;font-size:12px;font-weight:500">{text} ✓</span>'
    return f'<span style="background:#FCEBEB;color:#A32D2D;padding:2px 10px;border-radius:99px;font-size:12px;font-weight:500">{text} ✕</span>'

def get_numeric_like_columns(df):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    numeric_like_cols = []
    for col in df.select_dtypes(include=["object", "string", "category"]).columns:
        series = df[col].dropna().astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.replace("%", "", regex=False)
        if series.empty:
            continue
        coerced = pd.to_numeric(series, errors="coerce")
        if coerced.notna().mean() >= 0.8:
            numeric_like_cols.append(col)
    return numeric_cols + [c for c in numeric_like_cols if c not in numeric_cols]


def infer_aggregation_for_column(col_name, series):
    col_lower = col_name.lower()
    keywords_count = ["count", "id", "index", "code", "serial", "no", "number"]
    sum_terms = ["amount", "total", "sales", "revenue", "profit", "income", "cost", "price", "expense", "budget", "qty", "quantity", "units", "value", "salary"]
    avg_terms = ["age", "score", "rating", "duration", "tenure", "years", "year", "month", "day", "hour", "minute", "distance", "weight", "height", "temp", "temperature", "speed"]

    if any(term in col_lower for term in keywords_count):
        return "Count"
    if any(term in col_lower for term in sum_terms):
        return "Sum"
    if any(term in col_lower for term in avg_terms):
        return "Average"

    values = series.dropna()
    if values.empty:
        return "Count"

    unique_ratio = values.nunique() / len(values)
    if unique_ratio > 0.8:
        return "Average"
    if values.nunique() <= 5:
        return "Sum"
    return "Sum"

def dtype_badge(dtype):
    if "int" in dtype or "float" in dtype:
        return f'<span style="background:#E6F1FB;color:#185FA5;padding:2px 8px;border-radius:4px;font-size:12px">{dtype}</span>'
    elif "datetime" in dtype:
        return f'<span style="background:#EAF3DE;color:#3B6D11;padding:2px 8px;border-radius:4px;font-size:12px">{dtype}</span>'
    return f'<span style="background:#F1EFE8;color:#5F5E5A;padding:2px 8px;border-radius:4px;font-size:12px">{dtype}</span>'

# ---------- Quality Report ----------
def show_quality_report(df):
    st.subheader(":material/fact_check: Data Quality Report")
    cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()

    dup_count = int(df.duplicated().sum())
    empty_rows = int(df.isnull().all(axis=1).sum())
    empty_cols = df.columns[df.isnull().all()].tolist()
    casing_cols = [c for c in cat_cols if len(set(v.strip().lower() for v in df[c].dropna().unique())) < len(df[c].dropna().unique())]
    whitespace_cols = [c for c in cat_cols if df[c].dropna().apply(lambda x: x != x.strip()).any()]
    numeric_as_text_cols = []
    for col in cat_cols:
        try:
            pd.to_numeric(df[col].dropna().head(20).str.replace(",","").str.replace("$","").str.replace("%",""))
            numeric_as_text_cols.append(col)
        except: pass

    rows = [
        ("Shape", f"{df.shape[0]:,} rows, {df.shape[1]} columns", True),
        ("Duplicates", f"{dup_count} rows", dup_count == 0),
        ("Empty rows", f"{empty_rows} rows", empty_rows == 0),
        ("Empty columns", ', '.join(empty_cols) if empty_cols else "0", not empty_cols),
        ("Casing issues", ', '.join(casing_cols) if casing_cols else "None", not casing_cols),
        ("Whitespace", ', '.join(whitespace_cols) if whitespace_cols else "None", not whitespace_cols),
        ("Numeric as text", ', '.join(numeric_as_text_cols) if numeric_as_text_cols else "None", not numeric_as_text_cols),
    ]

    table_style = "width:100%;border-collapse:collapse;font-size:13px;margin-bottom:1rem"
    th_style = "background:#E6F1FB;color:#0C447C;padding:9px 14px;text-align:left;font-weight:500;border-bottom:2px solid #B5D4F4"
    td_style = "padding:9px 14px;border-bottom:0.5px solid #E6F1FB;color:#1C1C1C;vertical-align:middle"
    td_check = "padding:9px 14px;border-bottom:0.5px solid #E6F1FB;color:#5F5E5A;font-weight:500;width:180px"

    html = f'<table style="{table_style}"><tr><th style="{th_style}">Check</th><th style="{th_style}">Result</th></tr>'
    for check, result, is_ok in rows:
        html += f'<tr><td style="{td_check}">{check}</td><td style="{td_style}">{badge(result, is_ok)}</td></tr>'
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

    col_html = f'<table style="{table_style}"><tr><th style="{th_style}">Column name</th><th style="{th_style}">Data type</th><th style="{th_style};text-align:right">Null count</th></tr>'
    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        null_cell = f'<span style="color:#A32D2D;font-weight:500">{null_count}</span>' if null_count > 0 else f'<span style="color:#0C447C">{null_count}</span>'
        col_html += f'<tr><td style="{td_style}">{col}</td><td style="{td_style}">{dtype_badge(str(df[col].dtype))}</td><td style="{td_style};text-align:right">{null_cell}</td></tr>'
    col_html += "</table>"

    with st.expander(":material/view_column: Column details"):
        st.markdown(col_html, unsafe_allow_html=True)

    total_issues = sum([dup_count > 0, empty_rows > 0, bool(empty_cols), bool(casing_cols), bool(whitespace_cols), bool(numeric_as_text_cols), df.isnull().sum().sum() > 0])
    score = max(0, round((1 - total_issues / 7) * 100))
    score_label = f"Good — {score}% Clean" if score >= 80 else (f"Fair — {score}% Clean" if score >= 50 else f"Poor — {score}% Clean")
    st.metric("Data health score", score_label)
    if total_issues == 0:
        st.success("Your data looks clean. No major issues found.")
    else:
        st.warning(f"Found **{total_issues} issue(s)** in your dataset.")

# ---------- Auto Clean ----------
def auto_clean(df):
    report = []
    cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()

    empty_cols = df.columns[df.isnull().all()].tolist()
    if empty_cols:
        df = df.drop(columns=empty_cols)
        report.append(f"Removed **{len(empty_cols)} empty columns**: {empty_cols}")

    before = len(df); df = df.dropna(how="all")
    if len(df) < before: report.append(f"Removed **{before - len(df)} empty rows**")

    before = len(df); df = df.drop_duplicates()
    if len(df) < before: report.append(f"Removed **{before - len(df)} duplicate rows**")

    for col in cat_cols:
        if col in df.columns and df[col].dropna().apply(lambda x: x != x.strip()).any():
            df[col] = df[col].str.strip()
            report.append(f"Stripped whitespace in **{col}**")

    for col in cat_cols:
        if col in df.columns:
            values = df[col].dropna().unique()
            if len(set(v.strip().lower() for v in values)) < len(values):
                df[col] = df[col].str.strip().str.title()
                report.append(f"Fixed casing in **{col}**")

    for col in cat_cols:
        if col in df.columns:
            try:
                pd.to_numeric(df[col].dropna().head(20).str.replace(",","").str.replace("$","").str.replace("%",""))
                df[col] = pd.to_numeric(df[col].str.replace(",","").str.replace("$","").str.replace("%",""), errors="coerce")
                report.append(f"Converted **{col}** to numeric")
            except: pass

    for col in df.select_dtypes(include="number").columns:
        missing = df[col].isnull().sum()
        if missing > 0:
            val = df[col].median()
            df[col] = df[col].fillna(val)
            report.append(f"Filled **{missing} nulls** in **{col}** with median ({round(val,2)})")

    for col in df.select_dtypes(include="object").columns:
        missing = df[col].isnull().sum()
        if missing > 0:
            mode_vals = df[col].mode()
            if not mode_vals.empty:
                val = mode_vals[0]
                df[col] = df[col].fillna(val)
                report.append(f"Filled **{missing} nulls** in **{col}** with mode ('{val}')")
            else:
                df[col] = df[col].fillna("")
                report.append(f"Filled **{missing} nulls** in **{col}** with empty string")

    return df, report

# ---------- Charts ----------
def show_charts(df):
    num_cols = get_meaningful_numeric(df)
    all_num_cols = get_numeric_like_columns(df)
    cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    all_cols = df.columns.tolist()

    st.subheader(":material/bar_chart: Charts")
    if "chart_history" not in st.session_state:
        st.session_state["chart_history"] = []

    chart_type = st.selectbox("Select chart type", [
        "Bar Chart", "Histogram", "Scatter Plot",
        "Pie Chart", "Line Chart", "Box Plot", "Correlation Heatmap"
    ])
    st.markdown("---")
    params = {}

    display_num_cols = all_num_cols if all_num_cols else num_cols

    if chart_type == "Bar Chart":
        if not cat_cols or not display_num_cols:
            st.warning("Needs 1 category and 1 numeric column.")
        else:
            c1, c2, c3 = st.columns(3)
            params["cat"] = c1.selectbox("Category column (X axis)", cat_cols)
            params["val"] = c2.selectbox("Value column (Y axis)", display_num_cols)
            default_agg = infer_aggregation_for_column(params["val"], df[params["val"]]) if params.get("val") else "Sum"
            params["agg"] = c3.selectbox("Aggregation", ["Sum", "Average", "Count"], index=["Sum", "Average", "Count"].index(default_agg))
    elif chart_type == "Histogram":
        if not display_num_cols:
            st.warning("Needs at least 1 numeric column.")
        else:
            params["col"] = st.selectbox("Numeric column", display_num_cols)
            params["bins"] = st.slider("Number of bins", 5, 100, 30)
    elif chart_type == "Scatter Plot":
        if len(display_num_cols) < 2:
            st.warning("Needs at least 2 numeric columns.")
        else:
            c1, c2, c3 = st.columns(3)
            params["x_col"] = c1.selectbox("X axis", display_num_cols)
            params["y_col"] = c2.selectbox("Y axis", display_num_cols, index=1)
            params["color_col"] = c3.selectbox("Color by (optional)", ["None"] + cat_cols)
    elif chart_type == "Pie Chart":
        if not cat_cols or not display_num_cols:
            st.warning("Needs 1 category and 1 numeric column.")
        else:
            c1, c2, c3 = st.columns(3)
            params["cat"] = c1.selectbox("Category column", cat_cols)
            params["val"] = c2.selectbox("Value column", display_num_cols)
            default_agg = infer_aggregation_for_column(params["val"], df[params["val"]]) if params.get("val") else "Sum"
            params["agg"] = c3.selectbox("Aggregation", ["Sum", "Average", "Count"], index=["Sum", "Average", "Count"].index(default_agg))
    elif chart_type == "Line Chart":
        if not display_num_cols:
            st.warning("Needs at least 1 numeric column.")
        else:
            c1, c2 = st.columns(2)
            params["x_col"] = c1.selectbox("X axis", all_cols)
            params["y_col"] = c2.selectbox("Y axis", display_num_cols)
    elif chart_type == "Box Plot":
        if not display_num_cols:
            st.warning("Needs at least 1 numeric column.")
        else:
            c1, c2 = st.columns(2)
            params["val"] = c1.selectbox("Numeric column", display_num_cols)
            params["color_col"] = c2.selectbox("Group by (optional)", ["None"] + cat_cols)
    elif chart_type == "Correlation Heatmap":
        if len(display_num_cols) < 2:
            st.warning("Needs at least 2 numeric columns.")
        else:
            params["heatmap"] = True

    if params and st.button("Generate Chart", type="primary"):
        try:
            if chart_type == "Bar Chart":
                if params["agg"] == "Count":
                    grouped = df.groupby(params["cat"]).size().reset_index(name="Count").sort_values("Count", ascending=False).head(15)
                    fig = px.bar(grouped, x=params["cat"], y="Count", title=f"Count by {params['cat']}", color="Count", color_continuous_scale="Blues", text_auto=True)
                else:
                    agg_func = "mean" if params["agg"] == "Average" else "sum"
                    grouped = df.groupby(params["cat"])[params["val"]].agg(agg_func).reset_index().sort_values(params["val"], ascending=False).head(15)
                    fig = px.bar(grouped, x=params["cat"], y=params["val"], title=f"{params['agg']} of {params['val']} by {params['cat']}", color=params["val"], color_continuous_scale="Blues", text_auto=True)
                fig.update_traces(textposition="outside")
            elif chart_type == "Histogram":
                fig = px.histogram(df, x=params["col"], nbins=params["bins"], title=f"Distribution of {params['col']}", color_discrete_sequence=["#378ADD"])
                fig.update_layout(bargap=0.1)
            elif chart_type == "Scatter Plot":
                fig = px.scatter(df, x=params["x_col"], y=params["y_col"], color=None if params["color_col"] == "None" else params["color_col"], title=f"{params['x_col']} vs {params['y_col']}", opacity=0.7, color_discrete_sequence=px.colors.qualitative.Set2)
            elif chart_type == "Pie Chart":
                if params["agg"] == "Count":
                    pie_data = df.groupby(params["cat"]).size().reset_index(name="Count")
                    fig = px.pie(pie_data, names=params["cat"], values="Count", title=f"Count by {params['cat']}", color_discrete_sequence=px.colors.qualitative.Pastel, hole=0.3)
                else:
                    agg_func = "mean" if params["agg"] == "Average" else "sum"
                    pie_data = df.groupby(params["cat"])[params["val"]].agg(agg_func).reset_index()
                    fig = px.pie(pie_data, names=params["cat"], values=params["val"], title=f"{params['agg']} of {params['val']} by {params['cat']}", color_discrete_sequence=px.colors.qualitative.Pastel, hole=0.3)
            elif chart_type == "Line Chart":
                df_line = df[[params["x_col"], params["y_col"]]].copy().sort_values(params["x_col"])
                fig = px.line(df_line, x=params["x_col"], y=params["y_col"], title=f"{params['y_col']} over {params['x_col']}", color_discrete_sequence=["#378ADD"], markers=True)
            elif chart_type == "Box Plot":
                fig = px.box(df, y=params["val"], color=None if params["color_col"] == "None" else params["color_col"], title=f"Outliers in {params['val']}", color_discrete_sequence=px.colors.qualitative.Pastel)
            elif chart_type == "Correlation Heatmap":
                corr_df = df[all_num_cols].copy()
                for col in corr_df.select_dtypes(include="object").columns:
                    corr_df[col] = pd.to_numeric(corr_df[col].astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.replace("%", "", regex=False), errors="coerce")
                fig = px.imshow(corr_df.corr().round(2), text_auto=True, color_continuous_scale="Blues", title="Correlation Heatmap")

            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#1C1C1C", size=12),
                title_font=dict(color="#1C1C1C", size=15),
                xaxis=dict(
                    title_font=dict(color="#1C1C1C"),
                    tickfont=dict(color="#1C1C1C"),
                    gridcolor="#E0E0E0",
                    linecolor="#CCCCCC"
                ),
                yaxis=dict(
                    title_font=dict(color="#1C1C1C"),
                    tickfont=dict(color="#1C1C1C"),
                    gridcolor="#E0E0E0",
                    linecolor="#CCCCCC"
                ),
                legend=dict(font=dict(color="#1C1C1C")),
                coloraxis_colorbar=dict(tickfont=dict(color="#1C1C1C"), title_font=dict(color="#1C1C1C"))
            )
            label = f"{chart_type} — {' | '.join(str(v) for v in params.values())}"
            st.session_state["chart_history"].append({"label": label, "fig": fig})
        except Exception as e:
            st.error(f"Could not generate chart: {e}")

    if st.session_state["chart_history"]:
        st.markdown("---")
        st.subheader(f":material/gallery_thumbnail: Generated Charts ({len(st.session_state['chart_history'])})")
        if st.button("Clear All Charts"):
            st.session_state["chart_history"] = []
            st.rerun()
        for i, chart in enumerate(reversed(st.session_state["chart_history"])):
            idx = len(st.session_state["chart_history"]) - 1 - i
            with st.expander(f"Chart {idx + 1} — {chart['label']}", expanded=True):
                st.plotly_chart(chart["fig"], use_container_width=True, key=f"plot_{idx}")
                if st.button("Delete", key=f"del_{idx}"):
                    st.session_state["chart_history"].pop(idx)
                    st.rerun()

# ---------- AI Section ----------
def show_ai_section(df):
    st.subheader(":material/psychology: AI Insights")
    if client is None:
        st.warning("AI features are disabled because the Groq client or GROQ_API_KEY is not configured.")
        return

    if st.button("Generate Insights", type="primary"):
        with st.spinner("Analyzing your data..."):
            summary = df.describe(include="all").round(2).to_string()[:2000]
            prompt = f"""
You are a smart data analyst. Analyze this dataset and provide:
1. Brief overview of what this dataset is about
2. 3 key trends or patterns
3. 2 anomalies or problemsm/ aq
4. 3 actionable business suggestions
Dataset: {df.shape[0]} rows, {df.shape[1]} columns
Columns: {list(df.columns)}
Stats: {summary}
Sample: {df.head(5).to_string()}
Use bullet points. Be specific with numbers.
"""
            response = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=800)
            st.markdown(response.choices[0].message.content)

    st.subheader(":material/chat: Ask AI")
    question = st.text_input("Ask anything about your data", placeholder="e.g. Which region has highest sales?")
    if st.button("Ask AI"):
        if not question:
            st.warning("Please enter a question before sending it to AI.")
        else:
            with st.spinner("Thinking..."):
                prompt = f"You are a data analyst. Answer concisely using specific numbers.\nColumns: {list(df.columns)}\nStats: {df.describe(include='all').round(2).to_string()[:1500]}\nSample: {df.head(10).to_string()}\nQuestion: {question}"
                response = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=600)
                st.write("**Answer:**", response.choices[0].message.content)

#  MAIN APP
uploaded_file = st.file_uploader("Upload your CSV file", type="csv")

if uploaded_file:
    # Clear charts when new file is uploaded
    if "last_file" not in st.session_state or st.session_state["last_file"] != uploaded_file.name:
        st.session_state["chart_history"] = []
        st.session_state["ai_suggestions"] = [] if "ai_suggestions" in st.session_state else []
        st.session_state["df_final"] = None
        st.session_state["cleaned"] = False
        st.session_state["last_file"] = uploaded_file.name

    df_raw = pd.read_csv(uploaded_file)

    with st.expander(":material/table: Preview raw data"):
        st.dataframe(df_raw.head(20))

    num_cols = get_meaningful_numeric(df_raw)
    st.subheader(":material/speed: Quick Stats")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Rows", f"{df_raw.shape[0]:,}")
    c2.metric("Total Columns", df_raw.shape[1])
    c3.metric("Numeric Columns", len(num_cols))
    c4.metric("Missing Values", int(df_raw.isnull().sum().sum()))

    st.markdown("---")
    show_quality_report(df_raw)

    c1, c2 = st.columns([1, 5])
    fix_btn = c1.button("Fix It", type="primary")
    skip_btn = c2.button("Skip")

    if fix_btn:
        df_clean, report = auto_clean(df_raw.copy())
        st.session_state["df_final"] = df_clean
        st.session_state["cleaned"] = True
        st.session_state["clean_report"] = report

    if skip_btn:
        st.session_state["df_final"] = df_raw.copy()
        st.session_state["cleaned"] = False

    if "df_final" in st.session_state and st.session_state["df_final"] is not None:
        df_final = st.session_state["df_final"]
        if st.session_state["cleaned"]:
            st.success("Data cleaned successfully!")
            with st.expander(":material/check_circle: See what was fixed"):
                for item in st.session_state["clean_report"]:
                    st.markdown(f"- {item}")
            csv_buffer = io.StringIO()
            df_final.to_csv(csv_buffer, index=False)
            st.download_button("Download Cleaned CSV", csv_buffer.getvalue(), "cleaned_data.csv", "text/csv")
        else:
            st.info("Continuing with raw data as is.")

        st.markdown("---")
        show_charts(df_final)
        st.markdown("---")
        show_ai_section(df_final)

else:
    st.markdown("""
    <div style="background:white;border-radius:12px;padding:3rem;text-align:center;border:1px dashed #B5D4F4;margin-top:1rem">
        <div style="font-size:36px;margin-bottom:1rem;color:#378ADD">⬆</div>
        <div style="font-size:16px;font-weight:500;color:#185FA5;margin-bottom:0.5rem">Upload a CSV file to get started</div>
        <div style="color:#888;font-size:13px">Works with any data — sales, expenses, marks, surveys and more</div>
    </div>
    """, unsafe_allow_html=True)