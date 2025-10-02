# DSOapp.py
import os
import sqlite3
import pandas as pd
import streamlit as st

# -- Definitions & Helpers ---
# Database connection helpers
@st.cache_resource(show_spinner=False)
def get_conn(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Database file not found: {path}")
    conn = sqlite3.connect(path, check_same_thread=False)
    return conn

def table_exists(conn, table_name: str) -> bool:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND lower(name)=lower(?)", (table_name,))
    return cur.fetchone() is not None

def col_exists(conn, table: str, col_name: str) -> bool:
    cur = conn.execute(f'PRAGMA table_info("{table}")')
    cols = [row[1] for row in cur.fetchall()]
    return any(c.lower() == col_name.lower() for c in cols)

def get_actual_col_name(conn, table: str, desired: str) -> str:
    cur = conn.execute(f'PRAGMA table_info("{table}")')
    cols = [row[1] for row in cur.fetchall()]
    dl = desired.lower().replace(" ", "")
    for c in cols:
        if c.lower() == desired.lower() or c.lower().replace(" ", "") == dl:
            return c
    return desired

def month_name(n: int) -> str:
    names = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    if 1 <= n <= 12:
        return names[n-1]
    return "Unknown"

def empty_like(df):
    # preserves columns & dtypes
    return df.iloc[0:0]

# Column width autosize helpers
def _width_bucket(n_chars: int) -> str:
    # tweak thresholds as you like for table column widths
    if n_chars <= 13:
        return "small"
    if n_chars <= 50:
        return "medium"
    return "large"

def _auto_column_config(df):
    """
    Build a Streamlit column_config dict with width buckets
    based on the longest string length in each column.
    """
    import streamlit as st
    cfg = {}
    if df is None or df.empty:
        # If empty, estimate by header lengths so we still get sane widths
        for c in df.columns if df is not None else []:
            n = len(str(c))
            cfg[c] = st.column_config.Column(c, width=_width_bucket(n))
        return cfg

    for c in df.columns:
        # consider both header and cell contents
        longest = max(
            len(str(c)),
            df[c].astype(str).map(len).max()
        )
        cfg[c] = st.column_config.Column(c, width=_width_bucket(longest))
    return cfg

# Time helper, fixes hours for SDT or STD
def hour_fixer(hour, time):
    if time == "Standard":
        hours = {1:'21:00 SDT', 2:'23:00 SDT', 3:'01:00 SDT', 4:'03:00 SDT'}
    elif time == "Daylight Saving":
        hours = {1:'22:00 DST', 2:'00:00 DST', 3:'02:00 DST', 4:'04:00 DST'}
    return hours[hour]


# --- Main App Logic ---

st.set_page_config(page_title="DSO Visibility Browser", layout="wide", page_icon="🌌")
st.title("🌌 DSO Visibility Browser")

# DB selection
default_db = os.path.join("data", "DSO.db")
db_path = st.sidebar.text_input(
    "SQLite DB path",
    value=default_db,
    help="Path to your SQLite database file (e.g., data/DSO.db)."
)

if not os.path.exists(db_path):
    st.info(f"ℹ️ The file **{db_path}** was not found. Update the path above to point to your SQLite database.")

# Try to connect
try:
    conn = get_conn(db_path)
except Exception:
    st.stop()

# Validate required tables/columns
required = {
    "DSO": ["Code", "Name", "Type", "Notes", "Constellation", "Catalogue"],
    "Visibility": ["Constellation", "Month", "Hour", "Optimal"],
    "Stars": ["Code", "Name", "Type", "Constellation", "Stars", "Notes"],
}
problems = []
for table, cols in required.items():
    if not table_exists(conn, table):
        problems.append(f"Missing table: {table}")
    else:
        for col in cols:
            if not col_exists(conn, table, col):
                problems.append(f'Missing column: "{col}" in table {table}')

if problems:
    st.error("Schema check failed:\n\n- " + "\n- ".join(problems))
    st.stop()

# Resolve actual column names
DSO_Code = get_actual_col_name(conn, "DSO", "Code")
DSO_Name = get_actual_col_name(conn, "DSO", "Name")
DSO_Type = get_actual_col_name(conn, "DSO", "Type")
DSO_Notes = get_actual_col_name(conn, "DSO", "Notes")
DSO_Const = get_actual_col_name(conn, "DSO", "Constellation")
DSO_Catalogue = get_actual_col_name(conn, "DSO", "Catalogue")

S_Code = get_actual_col_name(conn, "Stars", "Code")
S_Name = get_actual_col_name(conn, "Stars", "Name")
S_Type = get_actual_col_name(conn, "Stars", "Type")
S_No   = get_actual_col_name(conn, "Stars", "Stars")
S_Const= get_actual_col_name(conn, "Stars", "Constellation")
S_Notes = get_actual_col_name(conn, "Stars", "Notes")

V_Const = get_actual_col_name(conn, "Visibility", "Constellation")
V_Month = get_actual_col_name(conn, "Visibility", "Month")
V_Hour  = get_actual_col_name(conn, "Visibility", "Hour")
V_Optimal = get_actual_col_name(conn, "Visibility", "Optimal")

# Sidebar controls
available_months = pd.read_sql_query(f'''
    SELECT DISTINCT "{V_Month}" AS month
    FROM "Visibility"
    WHERE CAST("{V_Month}" AS INTEGER) BETWEEN 1 AND 12
    ORDER BY 1
''', conn)["month"].astype(int).tolist() or list(range(1, 13))

month = st.sidebar.number_input("Month (1-12)", min_value=1, max_value=12, value=1, step=1)
st.header(f"Showing results for **{month_name(month)}**.")

mode = st.sidebar.selectbox("Local Time", options=["Standard", "Daylight Saving"], index=0, help="Show the time ranges in Standard Time (SDT) or Daylight Saving Time (DST).")

q = st.sidebar.text_input("Search", value="", help="Search terms in name, type, constellation").strip()

st.sidebar.subheader("DSO Catalogues")
ck_messier  = st.sidebar.checkbox("Messier",  value=True)
ck_caldwell = st.sidebar.checkbox("Caldwell", value=True)
ck_other_dso    = st.sidebar.checkbox("Other",    value=True)

st.sidebar.subheader("Star Types")
ck_doubles  = st.sidebar.checkbox("Double Stars",  value=True)
ck_giants = st.sidebar.checkbox("Red Giants", value=True)
ck_other_star    = st.sidebar.checkbox("Others",    value=True)

# Build WHERE clause parts & params for the DSO catalogue filter
catalog_where = ""
catalog_params = []

selected_specific_dso = []
if ck_messier:
    selected_specific_dso.append("Messier")
if ck_caldwell:
    selected_specific_dso.append("Caldwell")

include_other_dso = ck_other_dso  # "Other" means anything not in ('Messier','Caldwell')

if selected_specific_dso or include_other_dso:
    pieces = []
    if selected_specific_dso:
        placeholders = ",".join(["?"] * len(selected_specific_dso))
        pieces.append(f'd."{DSO_Catalogue}" IN ({placeholders})')
        catalog_params.extend(selected_specific_dso)
    if include_other_dso:
        pieces.append(f'd."{DSO_Catalogue}" NOT IN (?, ?)')
        catalog_params.extend(["Messier", "Caldwell"])
    catalog_where = " OR ".join(pieces)
# If all three are checked (default), the where becomes IN (...) OR NOT IN (...), i.e., no effective restriction.

# Build WHERE clause parts & params for the DSO catalogue filter
startype_where = ""
startype_params = []

selected_specific_star = []
if ck_doubles:
    selected_specific_star.append("Double Star")
if ck_giants:
    selected_specific_star.append("Red Giant")

include_other_star = ck_other_star  # "Other" means anything not in ('Messier','Caldwell')

if selected_specific_star or include_other_star:
    pieces = []
    if selected_specific_star:
        placeholders = ",".join(["?"] * len(selected_specific_star))
        pieces.append(f's."{S_Type}" IN ({placeholders})')
        startype_params.extend(selected_specific_star)
    if include_other_star:
        pieces.append(f's."{S_Type}" NOT IN (?, ?)')
        startype_params.extend(["Double Star", "Red Giant"])
    startype_where = " OR ".join(pieces)
# If all three are checked (default), the where becomes IN (...) OR NOT IN (...), i.e., no effective restriction.

# Query 1: DSO x Visibility
sql_dso = f'''
SELECT
    d."{DSO_Code}" AS Code,
    d."{DSO_Type}" AS Type,
    d."{DSO_Name}" AS Name,
    d."{DSO_Notes}" AS Notes,
    d."{DSO_Const}" AS Constellation,
    v."{V_Hour}" AS Hour
FROM "DSO" d
JOIN "Visibility" v
  ON lower(trim(d."{DSO_Const}")) = lower(trim(v."{V_Const}"))
WHERE v."{V_Month}" = ?
  AND v."{V_Optimal}" = 1
'''
params_dso = [int(month)]
if q:
    sql_dso += f'''
    AND (
         lower(COALESCE(d."{DSO_Name}",'')) LIKE ?
      OR lower(COALESCE(d."{DSO_Type}",'')) LIKE ?
      OR lower(COALESCE(d."{DSO_Const}",'')) LIKE ?
    )
    '''
    like = f"%{q.lower()}%"
    params_dso += [like, like, like]
    
if catalog_where:
    sql_dso += f"\n    AND ({catalog_where})"
    params_dso += catalog_params

sql_dso += f' ORDER BY v."{V_Hour}" ASC, d."{DSO_Const}" ASC'

df = pd.read_sql_query(sql_dso, conn, params=params_dso)
if not (ck_messier or ck_caldwell or ck_other_dso):
    df = empty_like(df)

# Query 2: Stars x Visibility
sql_stars = f'''
SELECT
    s."{S_Code}" AS Code,
    s."{S_Type}" AS Type,
    s."{S_Name}" AS Name,   
    s."{S_No}"   AS Stars,
    s."{S_Notes}" AS Notes,
    s."{S_Const}" AS Constellation,
    v."{V_Hour}" AS Hour
FROM "Stars" s
JOIN "Visibility" v
  ON lower(trim(s."{S_Const}")) = lower(trim(v."{V_Const}"))
WHERE v."{V_Month}" = ?
  AND v."{V_Optimal}" = 1
'''
params_stars = [int(month)]
if q:
    sql_stars += f'''
    AND (
         lower(COALESCE(s."{S_Name}",'')) LIKE ?
      OR lower(COALESCE(s."{S_Type}",'')) LIKE ?
      OR lower(COALESCE(s."{S_Const}",'')) LIKE ?
    )
    '''
    like = f"%{q.lower()}%"
    params_stars += [like, like, like]
    
if startype_where:
    sql_stars += f"\n    AND ({startype_where})"
    params_stars += startype_params

    
sql_stars += f' ORDER BY v."{V_Hour}" ASC, s."{S_Const}" ASC'


df2 = pd.read_sql_query(sql_stars, conn, params=params_stars)
if not (ck_doubles or ck_giants or ck_other_star):
    df2 = empty_like(df2)


# Layout
tabs = st.tabs([hour_fixer(1, mode), hour_fixer(2, mode), hour_fixer(3, mode), hour_fixer(4, mode)])
for idx, hour in enumerate([1,2,3,4]):
    with tabs[idx]:
        st.caption("DSO Results")
        dso_view = df[df["Hour"] == hour].drop(columns="Hour", errors="ignore")
        st.dataframe(dso_view, hide_index=True, width='stretch', column_config=_auto_column_config(dso_view),)
        st.caption("Star Results")
        star_view = df2[df2["Hour"] == hour].drop(columns="Hour", errors="ignore")
        st.dataframe(star_view, hide_index=True, width='stretch', column_config=_auto_column_config(star_view),)


st.sidebar.metric("DSO Matches", len(df))
st.sidebar.metric("Star Matches", len(df2))
    
if len(df):
    csv = df.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button("⬇️ Download DSO CSV", data=csv, file_name=f"dso_visibility_month_{month}.csv", mime="text/csv")
if len(df2):
    csv2 = df2.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button("⬇️ Download Stars CSV", data=csv2, file_name=f'stars_visibility_month_{month}.csv', mime="text/csv")

st.markdown("---")
with st.expander("ℹ️ How it works"):
    st.write("""
    - Select a **month number (1–12)**. The app finds constellations in the **Visibility** table with that month and **Optimal = 1**.
    - It then returns matching rows from **DSO** and **Stars** whose **Constellation** matches those constellations.
    - For **DSO**: returns Code, Name, Type, Constellation, and Hour.
    - For **Stars**: returns Code, Name, Stars, 1Color, 2Color, Constellation, and Hour.
    """)
