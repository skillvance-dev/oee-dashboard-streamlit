# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="OEE Dashboard - PROMED", layout="wide")
st.title("📊 OEE Dashboard — PROMED")
st.markdown("Versi demo: mengambil data dari Google Sheet (public view).")

# --------- CONFIG ----------
# Ganti sheet_id dengan ID Google Sheet kamu jika ingin hardcode,
# atau masukkan via sidebar (lebih fleksibel).
DEFAULT_SHEET_ID = "1qMtaUtEgb2ei64NTzpr_dksoxjSm2TCWX1vqgDusGYs"

# ---------- Helpers ----------
def try_read_gsheet_csv(sheet_id):
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error("Gagal membaca Google Sheet. Pastikan 'Anyone with link can view' sudah diaktifkan.")
        st.exception(e)
        return None

def find_column(df, candidates):
    if df is None: return None
    cols = list(df.columns)
    lowered = [c.strip().lower() for c in cols]
    for cand in candidates:
        cand_l = cand.strip().lower()
        if cand_l in lowered:
            return cols[lowered.index(cand_l)]
    return None

def to_numeric_safe(series):
    return pd.to_numeric(series, errors='coerce')

# ---------- UI: Sidebar ----------
st.sidebar.header("Sumber Data")
sheet_id = st.sidebar.text_input("Google Sheet ID", value=DEFAULT_SHEET_ID, help="ID di URL Google Sheet (bagian setelah /d/ )")
load_btn = st.sidebar.button("Load data")

# Additional user inputs
st.sidebar.markdown("---")
st.sidebar.header("Parameter Perhitungan")
default_ideal = st.sidebar.number_input("Ideal rate (pcs per minute) — jika tidak ada kolom SPEED", min_value=0.0, value=0.0, step=0.1)
agg_level = st.sidebar.selectbox("Level agregasi", ["Per Mesin", "Per Shift", "Per Tanggal"])

# ---------- Load data ----------
if load_btn:
    df = try_read_gsheet_csv(sheet_id)
else:
    # try load default at start
    df = try_read_gsheet_csv(sheet_id)

if df is None:
    st.stop()

st.subheader("Data mentah (preview)")
st.dataframe(df.head(200))

# ---------- Detect relevant columns (robust) ----------
col_date = find_column(df, ["Tanggal", "Date", "tanggal", "date"])
col_shift = find_column(df, ["Shift", "shift"])
col_machine = find_column(df, ["Mesin", "Machine", "machine", "equipment"])
col_good = find_column(df, ["Good", "GOOD", "good", "OK", "Output", "output", "produksi"])
col_reject = find_column(df, ["Afkir", "Reject", "NG", "Bad", "afkir", "reject", "ng"])
col_planned = find_column(df, ["Jam Kerja Target", "Planned Time", "planned_time", "jam kerja target", "planned minutes"])
col_actual = find_column(df, ["Jam Kerja Aktual", "Jam Kerja Actual", "Actual Time", "Actual", "run_time", "runtime", "jam kerja aktual"])
col_downtime = find_column(df, ["Downtime", "Jam Berhenti", "Stop Time", "downtime", "jam berhenti"])
col_speed = find_column(df, ["Speed", "SPEED", "speed", "Ideal Rate", "Ideal_Rate", "Ideal Rate (pcs/min)"])

# Show detection result
st.sidebar.markdown("**Kolom terdeteksi:**")
st.sidebar.write({
    "Tanggal": col_date,
    "Shift": col_shift,
    "Mesin": col_machine,
    "Good": col_good,
    "Reject/Afkir": col_reject,
    "Planned Time": col_planned,
    "Actual Time": col_actual,
    "Downtime": col_downtime,
    "Speed/IdealRate": col_speed
})

# ---------- Normalize dataframe and compute fields ----------
df2 = df.copy()

# Parse date column if exists
if col_date:
    try:
        df2['__date'] = pd.to_datetime(df2[col_date], errors='coerce')
    except:
        df2['__date'] = pd.to_datetime(df2[col_date].astype(str), errors='coerce')
else:
    df2['__date'] = pd.to_datetime('today')

# numeric conversions
if col_good:
    df2['_good'] = to_numeric_safe(df2[col_good])
else:
    df2['_good'] = np.nan

if col_reject:
    df2['_reject'] = to_numeric_safe(df2[col_reject])
else:
    df2['_reject'] = np.nan

# total output (if exists)
if '_good' in df2.columns and '_reject' in df2.columns:
    df2['_total'] = df2['_good'].fillna(0) + df2['_reject'].fillna(0)
else:
    # try detect 'Total' or 'Output' column
    col_total = find_column(df, ["Total", "TOTAL", "total", "Output", "output"])
    if col_total:
        df2['_total'] = to_numeric_safe(df2[col_total])
    else:
        df2['_total'] = df2['_good'].fillna(0)

# Planned & Actual times (assume minutes)
if col_planned:
    df2['_planned'] = to_numeric_safe(df2[col_planned])
else:
    df2['_planned'] = np.nan

if col_actual:
    df2['_actual'] = to_numeric_safe(df2[col_actual])
else:
    # fallback: if downtime and planned exist, actual = planned - downtime
    if col_planned and col_downtime:
        df2['_actual'] = df2['_planned'] - to_numeric_safe(df2[col_downtime])
    else:
        df2['_actual'] = np.nan

# Downtime
if col_downtime:
    df2['_downtime'] = to_numeric_safe(df2[col_downtime])
else:
    df2['_downtime'] = np.nan

# Speed/Ideal rate: try to detect or use default from sidebar
if col_speed:
    df2['_ideal_rate'] = to_numeric_safe(df2[col_speed])
else:
    # If speed not in sheet, use global default if provided
    if default_ideal > 0:
        df2['_ideal_rate'] = default_ideal
    else:
        df2['_ideal_rate'] = np.nan

# Allow per-machine override
st.sidebar.markdown("---")
st.sidebar.markdown("**Override Ideal Rate per Mesin (opsional)**")
machines = df2[col_machine].unique().tolist() if col_machine else []
machine_rate = {}
for m in machines:
    machine_rate[m] = st.sidebar.number_input(f"Ideal rate (pcs/min) — {m}", min_value=0.0, value=float(default_ideal), step=0.1)
if col_machine:
    df2['_ideal_rate'] = df2[col_machine].map(machine_rate).fillna(df2['_ideal_rate'])

# Compute Availability / Performance / Quality / OEE with fallbacks
def compute_metrics(row):
    planned = row.get('_planned', np.nan)
    actual = row.get('_actual', np.nan)
    downtime = row.get('_downtime', np.nan)
    good = row.get('_good', np.nan)
    reject = row.get('_reject', np.nan)
    total = row.get('_total', np.nan)
    ideal_rate = row.get('_ideal_rate', np.nan)  # pcs per minute

    # Availability: prefer (planned - downtime) / planned, else actual/planned
    availability = np.nan
    if not np.isnan(planned):
        if not np.isnan(downtime):
            availability = max(0.0, (planned - downtime) / planned) if planned != 0 else np.nan
        elif not np.isnan(actual):
            availability = actual / planned if planned != 0 else np.nan
    elif not np.isnan(actual) and not np.isnan(total):
        # fallback crude
        availability = 1.0  # unknown; better to show NA/break
    else:
        availability = np.nan

    # Performance: need ideal_rate (pcs/min) and actual runtime (minutes)
    performance = np.nan
    if not np.isnan(ideal_rate) and not np.isnan(actual) and actual > 0:
        ideal_count = ideal_rate * actual
        if ideal_count > 0:
            performance = total / ideal_count
    else:
        # fallback: if there is column SPEED (pcs/min) in sheet, use it as actual rate vs ideal
        if not np.isnan(row.get('_ideal_rate', np.nan)) and not np.isnan(row.get('_total', np.nan)) and not np.isnan(actual) and actual>0:
            # if ideal rate present but we couldn't compute ideal_count above, try this
            performance = 1.0
        else:
            performance = np.nan

    # Quality: good / total
    quality = np.nan
    if not np.isnan(good) and not np.isnan(total) and total > 0:
        quality = good / total
    else:
        quality = np.nan

    # Overall OEE
    oee = np.nan
    if not np.isnan(availability) and not np.isnan(performance) and not np.isnan(quality):
        oee = availability * performance * quality
    else:
        oee = np.nan

    return pd.Series({
        'Availability': availability,
        'Performance': performance,
        'Quality': quality,
        'OEE': oee
    })

metrics = df2.apply(compute_metrics, axis=1)
df2 = pd.concat([df2, metrics], axis=1)

# ---------- Dashboard views ----------
st.subheader("Ringkasan KPI")
kpi_cols = ['Availability', 'Performance', 'Quality', 'OEE']
kpi_vals = {}
col1, col2, col3, col4 = st.columns(4)
for idx, k in enumerate(kpi_cols):
    mean_val = df2[k].mean(skipna=True)
    txt = f"{mean_val:.2%}" if not np.isnan(mean_val) else "N/A"
    if idx == 0:
        col1.metric("Availability (avg)", txt)
    elif idx == 1:
        col2.metric("Performance (avg)", txt)
    elif idx == 2:
        col3.metric("Quality (avg)", txt)
    else:
        col4.metric("OEE (avg)", txt)

st.markdown("**Catatan:** Jika beberapa metrik tampil `N/A`, periksa apakah kolom `Planned`, `Actual`, `Good`, `Reject` atau `Ideal rate` tersedia.")

# Filters
st.sidebar.markdown("---")
st.sidebar.header("Filter Tampilan")
if col_machine:
    sel_machine = st.sidebar.selectbox("Pilih Mesin (All = semua)", options=["All"] + machines)
else:
    sel_machine = "All"

if col_date:
    min_date = df2['__date'].min()
    max_date = df2['__date'].max()
    date_range = st.sidebar.date_input("Pilih rentang tanggal", value=(min_date.date() if pd.notnull(min_date) else datetime.today().date(), max_date.date() if pd.notnull(max_date) else datetime.today().date()))
else:
    date_range = None

# apply filters
df_view = df2.copy()
if sel_machine != "All" and col_machine:
    df_view = df_view[df_view[col_machine] == sel_machine]

if date_range and col_date:
    start, end = date_range
    mask = (df_view['__date'] >= pd.to_datetime(start)) & (df_view['__date'] <= pd.to_datetime(end))
    df_view = df_view[mask]

st.subheader("Data terfilter & perhitungan")
display_cols = []
# show original cols + computed metrics
display_cols += list(df.columns)[:15]  # first N orig cols (prevent extremely wide)
display_cols += ['_total', 'Availability', 'Performance', 'Quality', 'OEE']
st.dataframe(df_view[display_cols].reset_index(drop=True).head(500))

# ---------- Trend chart ----------
st.subheader("Tren OEE")
if col_date:
    trend_df = df_view.groupby(df_view['__date'].dt.date).agg({
        'OEE': 'mean',
        'Availability': 'mean',
        'Performance': 'mean',
        'Quality': 'mean'
    }).reset_index().rename(columns={'__date':'date'})
    trend_df = trend_df.sort_values(by='__date') if '__date' in trend_df.columns else trend_df
    if not trend_df['OEE'].isna().all():
        fig = px.line(trend_df, x='__date' if '__date' in trend_df.columns else trend_df.columns[0], y=['OEE','Availability','Performance','Quality'],
                      labels={'value':'%', '__date':'Tanggal'}, markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Belum ada data OEE yang lengkap untuk ditampilkan di tren. Pastikan kolom Planned/Actual/Good/Reject/Ideal rate tersedia.")
else:
    st.info("Tidak ada kolom tanggal terdeteksi — tren tidak bisa ditampilkan.")

# ---------- Top losses (downtime) ----------
if col_downtime and 'Downtime Reason' in df.columns:
    st.subheader("Top Downtime Reasons")
    reason_col = 'Downtime Reason'
    dd = df_view.groupby(reason_col).agg({'_downtime':'sum'}).reset_index().sort_values('_downtime', ascending=False).head(10)
    fig2 = px.bar(dd, x=reason_col, y='_downtime', labels={'_downtime':'Total downtime (min)'})
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.caption("Template dashboard OEE ringan — cocok untuk pilot dan pelatihan. Untuk akurasi Performance, sediakan kolom Ideal Rate (pcs per minute) atau Speed.")
