import html
import os
import re
import sqlite3

import altair as alt
import pandas as pd
import streamlit as st
from groq import Groq

FONT = "Poppins"  # change only this line to try another font, e.g. "Inter", "DM Sans", "Lora"

# Palette (from Coolors)
TEAL = "#073B3A"      # Dark Teal
EMERALD = "#0B6E4F"   # Dark Emerald
JUNGLE = "#08A045"    # Medium Jungle
MOSS = "#6BBF59"      # Moss Green
FAWN = "#DDB771"      # Soft Fawn

st.set_page_config(page_title="Ask Your Data", layout="wide", initial_sidebar_state="collapsed")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=__FONT_URL__:wght@400;500;600;700&display=swap');

.stApp, .stApp p, .stApp label, .stApp li, .stApp input, .stApp textarea,
.stApp button, .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
    font-family: '__FONT__', sans-serif;
}
.stApp {background: #F2F7F3;}
.stApp h2, .stApp h3, .stApp h4 {color: #073B3A; letter-spacing: -0.2px;}
.block-container {padding-top: 1.25rem; max-width: 1200px;}

/* Hide Streamlit chrome */
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}

/* ---------- Hero band (title left, uploader right) ---------- */
.st-key-hero {
    background:
        radial-gradient(circle at 94% 6%, rgba(221,183,113,0.40), transparent 36%),
        linear-gradient(135deg, #073B3A 0%, #0B6E4F 100%);
    border-radius: 22px;
    padding: 30px 34px;
    margin-bottom: 18px;
}
.hero-title {font-size: 2.4rem; font-weight: 700; letter-spacing: -0.6px; line-height: 1.15; color: #FFFFFF;}
.hero-sub {margin-top: 8px; font-size: 1.05rem; color: #D5EBDB;}
.hero-note {margin-top: 16px; padding-left: 12px; border-left: 3px solid #DDB771;
            font-size: 0.85rem; color: #BFDCC9;}

.st-key-hero [data-testid="stFileUploaderDropzone"] {
    background: rgba(255,255,255,0.08);
    border: 2px dashed #DDB771;
    border-radius: 14px;
}
.st-key-hero [data-testid="stFileUploader"] * {color: #EAF4EC;}
.st-key-hero [data-testid="stFileUploaderDropzone"] button {
    background: #DDB771; color: #073B3A; border: none; border-radius: 10px; font-weight: 600;
}

/* ---------- Stat strip ---------- */
.kpi {
    background: #FFFFFF; border: 1px solid #DCE8DF; border-left: 6px solid var(--accent);
    border-radius: 14px; padding: 14px 18px;
}
.kpi-label {font-size: 0.8rem; font-weight: 600; color: #4B6B66;}
.kpi-value {font-size: 1.7rem; font-weight: 700; line-height: 1.25; color: #073B3A;}

/* ---------- Workspace panels ---------- */
.st-key-ask, .st-key-side {
    background: #FFFFFF;
    border: 1px solid #DCE8DF !important;
    border-radius: 18px !important;
    padding: 22px 24px;
    box-shadow: 0 6px 24px rgba(7,59,58,0.07);
}

/* Buttons */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
    border-radius: 10px; font-weight: 600;
}
button[kind="primary"], [data-testid="stBaseButton-primary"] {
    background: #0B6E4F; border: 1px solid #0B6E4F; color: #FFFFFF;
}
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {
    background: #073B3A; border-color: #073B3A; color: #FFFFFF;
}

/* Suggestion pills */
.st-key-chips button {
    border-radius: 999px; background: #FBF3E1; border: 1px solid #DDB771;
    color: #073B3A; font-size: 0.85rem; font-weight: 500; padding: 0.25rem 0.9rem;
}
.st-key-chips button:hover {background: #DDB771; border-color: #DDB771; color: #073B3A;}

.stTextInput input {border-radius: 10px;}

/* Dataset panel */
.side-h {font-size: 0.95rem; font-weight: 700; color: #073B3A; margin: 2px 0 8px;}
.col-list {max-height: 230px; overflow-y: auto; border: 1px solid #E3EEE6; border-radius: 12px;}
.col-row {display: flex; justify-content: space-between; align-items: center; gap: 12px;
          padding: 8px 12px; border-bottom: 1px solid #EEF4EF; font-size: 0.88rem;}
.col-row:last-child {border-bottom: none;}
.col-name {font-weight: 600; color: #073B3A; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;}
.col-type {flex-shrink: 0; font-size: 0.72rem; font-weight: 600; padding: 1px 9px; border-radius: 999px;
           background: #E6F4EA; color: #0B6E4F;}
.col-type.number {background: #F7ECD3; color: #6B4E12;}
.st-key-summary {background: #F4F9F5; border-radius: 12px; padding: 12px 16px; margin-top: 10px;}
.st-key-summary p, .st-key-summary li {font-size: 0.9rem;}

.empty {background: #FFFFFF; border: 2px dashed #DDB771; border-radius: 18px;
        padding: 28px 30px; color: #073B3A;}
.empty b {font-size: 1.1rem;}
</style>
"""
st.markdown(
    CSS.replace("__FONT_URL__", FONT.replace(" ", "+")).replace("__FONT__", FONT),
    unsafe_allow_html=True,
)


def wide(fn, *args, **kwargs):
    """Stretch a widget to full width on both old and new Streamlit versions."""
    try:
        return fn(*args, width="stretch", **kwargs)
    except TypeError:
        return fn(*args, use_container_width=True, **kwargs)


# ---------- Hero: title on the left, uploader on the right ----------
with st.container(key="hero"):
    h_left, h_right = st.columns([1.25, 1], vertical_alignment="center")
    with h_left:
        st.markdown(
            '<div class="hero-title">Ask Your Data</div>'
            '<div class="hero-sub">Upload a CSV, then ask questions in plain English.</div>'
            '<div class="hero-note">The app writes SQL for your question, checks that it is '
            "read-only, and runs it.</div>",
            unsafe_allow_html=True,
        )
    with h_right:
        uploaded = st.file_uploader("Upload a CSV", type="csv", label_visibility="collapsed")

# ---------- Pick the data source: upload first, then the sample file ----------
SAMPLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sales.csv")
has_sample = os.path.exists(SAMPLE_PATH)


def start_sample():
    st.session_state["use_sample"] = True


if uploaded is not None:
    source, file_key = uploaded, (uploaded.name, uploaded.size)
    st.session_state["use_sample"] = False
elif st.session_state.get("use_sample") and has_sample:
    source, file_key = SAMPLE_PATH, ("sample", os.path.getsize(SAMPLE_PATH))
    st.caption("Showing the sample sales data. Upload your own CSV above to switch.")
else:
    st.markdown(
        '<div class="empty"><b>Drop a CSV into the box above to start.</b><br>'
        "You'll get a quick overview of your data and can ask questions about it right away."
        + ("<br>No file handy? Try the sample sales data instead." if has_sample else "")
        + "</div>",
        unsafe_allow_html=True,
    )
    if has_sample:
        st.write("")
        st.button("Try the sample sales data", type="primary", on_click=start_sample)
    st.stop()

# Reset answers when the data changes
if st.session_state.get("file_key") != file_key:
    st.session_state["file_key"] = file_key
    for k in ("last", "summary", "q", "pending"):
        st.session_state.pop(k, None)

# ---------- Load and clean data ----------
df = pd.read_csv(source)
df.columns = [c.strip().replace(" ", "_") for c in df.columns]

for col in df.columns:
    if "date" in col.lower():
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
        bad = df[col].isna().sum()
        if bad:
            st.warning(f"{bad} values in '{col}' couldn't be read as dates.")

# ---------- SQLite (read-only) ----------
conn = sqlite3.connect(":memory:")
df.to_sql("data", conn, index=False, if_exists="replace")
schema = pd.read_sql("PRAGMA table_info(data)", conn)[["name", "type"]].to_string(index=False)
conn.execute("PRAGMA query_only = ON")

# ---------- API key and model ----------
try:
    api_key = st.secrets["GROQ_API_KEY"]
except Exception:
    api_key = os.environ.get("GROQ_API_KEY")

if not api_key:
    st.error("No API key found. Add GROQ_API_KEY to .streamlit/secrets.toml or set it as an environment variable.")
    st.stop()

client = Groq(api_key=api_key)
MODEL = "openai/gpt-oss-120b"


def ask_llm(prompt: str, max_tokens: int = 2000) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


FORBIDDEN = re.compile(
    r"\b(drop|delete|update|insert|alter|create|replace|attach|pragma|truncate)\b", re.I
)


def validate_sql(sql: str) -> str:
    sql = sql.strip().rstrip(";").strip()
    if ";" in sql:
        raise ValueError("Chained statements are not allowed.")
    if not re.match(r"^(select|with)\b", sql, re.I):
        raise ValueError("Only SELECT queries are allowed.")
    if FORBIDDEN.search(sql):
        raise ValueError("Query contains a blocked keyword.")
    return sql


# ---------- Charts ----------
def draw_chart(result):
    cat, val = result.columns[0], result.columns[1]
    data = pd.DataFrame({"label": result[cat].astype(str), "value": result[val]})
    tips = [
        alt.Tooltip("label:N", title=cat),
        alt.Tooltip("value:Q", title=val, format=",.2f"),
    ]

    if any(w in cat.lower() for w in ("month", "date", "year")):
        base = alt.Chart(data).encode(
            x=alt.X("label:O", sort=None, title=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("value:Q", title=None),
            tooltip=tips,
        )
        area = base.mark_area(color=MOSS, opacity=0.22, line=False)
        line = base.mark_line(
            color=EMERALD, strokeWidth=3,
            point=alt.OverlayMarkDef(color=FAWN, size=90),
        )
        chart = (area + line).properties(height=320)
    else:
        top_label = data.loc[data["value"].idxmax(), "label"]
        chart = (
            alt.Chart(data)
            .mark_bar(cornerRadiusEnd=5)
            .encode(
                y=alt.Y("label:N", sort=None, title=None, axis=alt.Axis(labelLimit=260)),
                x=alt.X("value:Q", title=None),
                color=alt.condition(
                    alt.datum.label == top_label, alt.value(JUNGLE), alt.value(MOSS)
                ),
                tooltip=tips,
            )
            .properties(height=max(200, 34 * len(data)))
        )

    chart = (
        chart.configure(font=FONT)
        .configure_view(strokeWidth=0)
        .configure_axis(gridColor="#E3EEE6", labelColor=TEAL, domain=False, tickColor="#E3EEE6")
    )
    wide(st.altair_chart, chart)


# ---------- Stat strip ----------
def kpi(label, value, accent):
    st.markdown(
        f'<div class="kpi" style="--accent:{accent}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


date_cols = [c for c in df.columns if "date" in c.lower()]
if date_cols and df[date_cols[0]].notna().any():
    d = df[date_cols[0]].dropna()
    third = ("Date range", f"{d.min()[:4]} – {d.max()[:4]}")
else:
    third = ("Numeric columns", len(df.select_dtypes("number").columns))

k1, k2, k3, k4 = st.columns(4)
with k1:
    kpi("Rows", f"{len(df):,}", JUNGLE)
with k2:
    kpi("Columns", len(df.columns), FAWN)
with k3:
    kpi(third[0], third[1], EMERALD)
with k4:
    kpi("Missing cells", f"{int(df.isna().sum().sum()):,}", MOSS)

st.write("")

# ---------- Question helpers ----------
num_cols = list(df.select_dtypes("number").columns)
cat_cols = [
    c for c in df.columns
    if c not in num_cols and "date" not in c.lower() and 2 <= df[c].nunique() <= 50
]

def is_id_like(c):
    name = c.lower()
    pattern = r"(^|_)(id|code|zip|postal|index|no|number)($|_)"
    return bool(re.search(pattern, name)) or df[c].nunique() == len(df)


PREFERRED = ("sales", "revenue", "amount", "profit", "total", "price", "cost", "quantity")
measure_cols = [c for c in num_cols if not is_id_like(c)]
measure_cols.sort(key=lambda c: 0 if any(p in c.lower() for p in PREFERRED) else 1)

suggestions = []
if cat_cols and measure_cols:
    suggestions.append(f"Top 5 {cat_cols[0]} by total {measure_cols[0]}")
if date_cols and measure_cols:
    suggestions.append(f"Monthly total {measure_cols[0]}")
suggestions.append("How many rows are there?")
suggestions = suggestions[:3]


def queue_run():
    st.session_state["pending"] = True


def use_suggestion(text):
    st.session_state["q"] = text
    st.session_state["pending"] = True


# ---------- Workspace: ask on the left, dataset on the right ----------
col_main, col_side = st.columns([1.9, 1], gap="large")

with col_main:
    with st.container(border=True, key="ask"):
        st.markdown("### Ask a question")

        c_in, c_btn = st.columns([5, 1], vertical_alignment="bottom")
        with c_in:
            st.text_input(
                "Your question",
                key="q",
                placeholder="e.g. Top 5 products by total sales",
                label_visibility="collapsed",
                on_change=queue_run,
            )
        with c_btn:
            wide(st.button, "Ask", type="primary", on_click=queue_run)

        with st.container(key="chips"):
            chip_cols = st.columns(len(suggestions))
            for i, (cc, s) in enumerate(zip(chip_cols, suggestions)):
                with cc:
                    wide(st.button, s, key=f"chip{i}", on_click=use_suggestion, args=(s,))

        question = st.session_state.get("q", "").strip()
        if st.session_state.pop("pending", False) and question:
            entry = {"question": question, "sql": ""}
            with st.spinner("Thinking..."):
                try:
                    prompt = f"""You write SQLite queries. The table is named `data`.

Schema:
{schema}

Sample rows:
{df.head(5).to_string(index=False)}

Notes:
- Date columns are stored as text in YYYY-MM-DD format. Use strftime('%Y-%m', column) for months.
- If a column name has spaces or symbols, wrap it in double quotes. Copy column names exactly as in the schema.
- Never sum or average ID, code or postal-code columns. For totals, use measure columns such as sales, profit or quantity.
- Return ONLY one SELECT query. No explanation, no markdown fences.

Question: {question}"""
                    sql = ask_llm(prompt).replace("```sql", "").replace("```", "").strip()
                    entry["sql"] = sql
                    entry["result"] = pd.read_sql(validate_sql(sql), conn)
                except Exception as e:
                    entry["error"] = str(e)
            st.session_state["last"] = entry

        last = st.session_state.get("last")
        if last:
            st.markdown(f"#### {html.escape(last['question'])}")

            if "error" in last:
                st.error(f"Couldn't run that: {last['error']}")
            else:
                result = last["result"]
                if len(result.columns) == 2 and pd.api.types.is_numeric_dtype(result.iloc[:, 1]):
                    draw_chart(result)
                wide(st.dataframe, result)
                wide(
                    st.download_button,
                    "Download result as CSV",
                    result.to_csv(index=False).encode("utf-8"),
                    file_name="result.csv",
                    mime="text/csv",
                )

            with st.expander("Generated SQL"):
                st.code(last["sql"], language="sql")

with col_side:
    with st.container(border=True, key="side"):
        st.markdown("### Your dataset")

        st.markdown('<div class="side-h">Columns</div>', unsafe_allow_html=True)

        def col_type(c):
            if c in num_cols:
                return "number"
            if "date" in c.lower():
                return "date"
            return "text"

        rows = "".join(
            f'<div class="col-row"><span class="col-name">{html.escape(c)}</span>'
            f'<span class="col-type {col_type(c)}">{col_type(c)}</span></div>'
            for c in df.columns
        )
        st.markdown(f'<div class="col-list">{rows}</div>', unsafe_allow_html=True)

        st.write("")
        st.markdown('<div class="side-h">Summary</div>', unsafe_allow_html=True)
        if wide(st.button, "Generate summary", type="primary"):
            with st.spinner("Summarizing..."):
                stats = df.describe(include="all").to_string()
                st.session_state["summary"] = ask_llm(
                    f"Summarize this dataset in 5 short bullet points for a business reader.\n"
                    f"Columns:\n{schema}\n\nStats:\n{stats}",
                    max_tokens=1500,
                )
        if "summary" in st.session_state:
            with st.container(key="summary"):
                st.markdown(st.session_state["summary"].replace("$", "\\$"))

st.write("")
with st.expander("Preview data (first 100 rows)"):
    wide(st.dataframe, df.head(100))
