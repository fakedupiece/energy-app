import streamlit as st
import numpy as np
import numpy_financial as npf
import pandas as pd
import plotly.express as px
import plotly.io as pio
from pathlib import Path
import base64
from datetime import date
import io
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ============================================================
# CONFIG
# ============================================================
st.set_page_config(page_title="Renewable Investment Dashboard", page_icon="📊", layout="wide")

BRAND_ORANGE = "#FF6A00"
LOGO_PATH = "ideal_logo.jpg"
TRANSMISSION_COST_PER_KM = 100_000.0  # $ per km

# ============================================================
# HELPERS
# ============================================================
def img_to_data_uri(path: str) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    b = p.read_bytes()
    b64 = base64.b64encode(b).decode("utf-8")
    ext = p.suffix.lower().lstrip(".")
    mime = "png" if ext == "png" else "jpeg" if ext in ("jpg", "jpeg") else ext
    return f"data:image/{mime};base64,{b64}"

def bytes_to_data_uri_png(b: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(b).decode("utf-8")

def money(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    ax = abs(x)
    sign = "-" if x < 0 else ""
    if ax >= 1e9: return f"{sign}${ax/1e9:,.2f}B"
    if ax >= 1e6: return f"{sign}${ax/1e6:,.2f}M"
    if ax >= 1e3: return f"{sign}${ax/1e3:,.1f}K"
    return f"{sign}${ax:,.0f}"

def pct(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x*100:.2f}%"

def years(x: int | None) -> str:
    return "—" if not x else f"{x} yrs"

def annual_energy_kwh(capacity_mw: float, capacity_factor_pct: float) -> float:
    return capacity_mw * 1e3 * 8760 * (capacity_factor_pct / 100.0)

def safe_float(x, default=np.nan):
    try:
        return float(x)
    except Exception:
        return default

# ============================================================
# LIGHT THEME / CSS (readable)
# ============================================================
logo_uri = img_to_data_uri(LOGO_PATH)
logo_html = (
    f'<img src="{logo_uri}" style="height:38px; width:auto; display:block;" />'
    if logo_uri
    else f'<div style="height:38px; width:38px; border-radius:10px; background:{BRAND_ORANGE};"></div>'
)

st.markdown(
    f"""
<style>
[data-testid="stAppViewContainer"] {{ background: #F6F8FC; }}
[data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
.block-container {{ padding-top: 1.1rem; padding-bottom: 2.0rem; }}

section[data-testid="stSidebar"] {{
  background: #FFFFFF;
  border-right: 1px solid rgba(15, 23, 42, 0.08);
}}

.brandbar {{
  background: #FFFFFF;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 18px;
  padding: 14px 18px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
}}
.brandrow {{ display:flex; justify-content:space-between; align-items:center; gap: 16px; }}
.brandleft {{ display:flex; align-items:center; gap: 14px; }}
.brandtitle {{ font-size: 22px; font-weight: 900; letter-spacing: -0.02em; color: #0F172A; }}
.brandsub {{ color: rgba(15, 23, 42, 0.70); font-size: 13px; margin-top: 2px; }}
.badge {{
  padding: 8px 12px; border-radius: 999px;
  background: rgba(255,106,0,0.10);
  border: 1px solid rgba(255,106,0,0.25);
  color: #7A2E00; font-size: 12px; white-space: nowrap;
}}
.accent-line {{
  height: 4px; width: 100%;
  background: linear-gradient(90deg, {BRAND_ORANGE}, rgba(255,106,0,0));
  border-radius: 999px; margin-top: 10px;
}}

.card {{
  background: #FFFFFF;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.07);
}}
.kpi-title {{ color: rgba(15, 23, 42, 0.70); font-size: 12px; margin-bottom: 6px; }}
.kpi-value {{ color: #0F172A; font-size: 34px; font-weight: 900; letter-spacing: -0.02em; line-height: 1.05; }}
.kpi-sub {{ color: rgba(15, 23, 42, 0.65); font-size: 12px; margin-top: 6px; }}
.hr {{ height: 1px; background: rgba(15, 23, 42, 0.10); margin: .8rem 0 1rem 0; border-radius: 999px; }}
.note {{ color: rgba(15, 23, 42, 0.65); font-size: 12px; }}

.pill {{
  display:inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.10);
  background: #F8FAFF;
  font-size: 12px;
}}
.pill-good {{ border-color: rgba(22,163,74,.35); background: rgba(22,163,74,.08); color:#14532D; }}
.pill-warn {{ border-color: rgba(217,119,6,.35); background: rgba(217,119,6,.10); color:#7C2D12; }}
.pill-bad  {{ border-color: rgba(220,38,38,.35); background: rgba(220,38,38,.08); color:#7F1D1D; }}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# HEADER
# ============================================================
st.markdown(
    f"""
<div class="brandbar">
  <div class="brandrow">
    <div class="brandleft">
      {logo_html}
      <div>
        <div class="brandtitle">Renewable Investment Dashboard</div>
        <div class="brandsub">Pre‑feasibility scorecard • Stage costs • Transmission km pricing • Carbon income • PDF memo export</div>
      </div>
    </div>
    <div class="badge">Light Theme • Orange Accent</div>
  </div>
  <div class="accent-line"></div>
</div>
""",
    unsafe_allow_html=True,
)
st.write("")

# ============================================================
# DEV TASK BREAKDOWN DEFAULTS
# ============================================================
def default_dev_tasks():
    pre = [
        ("Site identification & screening", 35_000),
        ("Landowner outreach / exclusivity", 45_000),
        ("Desktop resource study", 60_000),
        ("Initial grid proximity check", 25_000),
        ("P50 yield draft", 40_000),
        ("Stakeholder mapping", 20_000),
        ("Concept layout & constraints", 35_000),
    ]
    lic = [
        ("Bankable feasibility scope definition", 120_000),
        ("Environmental & social studies (E&S)", 220_000),
        ("Permitting applications & filings", 90_000),
        ("Grid interconnection studies", 180_000),
        ("Geotech / topo surveys", 110_000),
        ("Noise/shadow flicker (wind only)", 65_000),
        ("Community consultations / hearings", 75_000),
        ("Legal structuring + SPV setup", 60_000),
    ]
    return pre, lic

pre_default, lic_default = default_dev_tasks()
pre_tasks_df = pd.DataFrame(pre_default, columns=["Task", "Cost ($)"])
lic_tasks_df = pd.DataFrame(lic_default, columns=["Task", "Cost ($)"])

# ============================================================
# SIDEBAR INPUTS
# ============================================================
with st.sidebar:
    st.markdown("## Investor Questions")
    rtb_only = st.toggle("Strictly RTB-only buyer", value=False)
    experience = st.selectbox("Renewables experience", ["None", "Some (1–2 deals)", "Experienced (3–10 deals)", "Expert (10+ deals)"])
    risk_pref = st.select_slider("Risk tolerance", ["Low", "Medium", "High"], value="Medium")
    st.markdown("---")

    st.markdown("## Project & Entry")
    project_type = st.selectbox("Project Type", ["WEP (Wind)", "SEP (Solar)"])
    entry_stage = st.selectbox("Investor Entry Stage", ["Idea", "Pre-licensing", "Licensing", "RTB"])

    st.markdown("## Capacity & Operations")
    capacity_mw = st.number_input("Capacity (MW)", value=10.0, min_value=0.1, step=0.5)
    default_cf = 35.0 if project_type.startswith("WEP") else 20.0
    capacity_factor = st.slider("Capacity Factor (%)", 0.0, 100.0, float(default_cf), 0.5)

    price = st.number_input("Electricity Price ($/kWh)", value=0.080, min_value=0.0, step=0.005, format="%.3f")
    opex = st.number_input("OPEX ($/year)", value=200_000.0, min_value=0.0, step=10_000.0, format="%.0f")
    degradation = st.slider("Degradation (%/yr)", 0.0, 5.0, 0.5, 0.1)
    lifetime = st.slider("Lifetime (years)", 1, 35, 20, 1)
    discount = st.slider("Discount Rate (%)", 0.0, 20.0, 8.0, 0.25)

    st.markdown("## Carbon Income")
    carbon_price = st.number_input("Carbon credit value ($/tCO₂)", value=25.0, min_value=0.0, step=1.0)
    grid_intensity = st.number_input("Displaced grid intensity (tCO₂/MWh)", value=0.40, min_value=0.0, step=0.01, format="%.2f")

    st.markdown("## Build CAPEX")
    if project_type.startswith("WEP"):
        equip_cost = st.number_input("Turbine supply cost ($)", value=6_500_000.0, min_value=0.0, step=250_000.0, format="%.0f")
    else:
        equip_cost = st.number_input("Panel supply cost ($)", value=4_000_000.0, min_value=0.0, step=250_000.0, format="%.0f")

    construction_cost = st.number_input("Construction / EPC cost ($)", value=2_500_000.0, min_value=0.0, step=250_000.0, format="%.0f")

    st.markdown("## Transmission Line")
    km = st.slider("Transmission line distance (km)", 0, 80, 10, 1)
    transmission_cost = km * TRANSMISSION_COST_PER_KM
    st.caption(f"Auto-cost: {km} km × $100,000/km = **{money(transmission_cost)}**")

# ============================================================
# DEVELOPMENT STAGE COSTS (task totals)
# ============================================================
pre_total = float(pre_tasks_df["Cost ($)"].sum())
lic_total = float(lic_tasks_df["Cost ($)"].sum())

def dev_spent_remaining(entry_stage: str):
    if entry_stage in ("Idea", "Pre-licensing"):
        return 0.0, pre_total + lic_total
    if entry_stage == "Licensing":
        return pre_total, lic_total
    if entry_stage == "RTB":
        return pre_total + lic_total, 0.0
    return 0.0, pre_total + lic_total

dev_spent, dev_remaining = dev_spent_remaining(entry_stage)
build_capex = equip_cost + construction_cost + transmission_cost
initial_outlay = dev_remaining + build_capex

# ============================================================
# ECONOMICS
# ============================================================
def full_economics():
    disc = discount / 100.0
    deg = degradation / 100.0

    annual_kwh = annual_energy_kwh(capacity_mw, capacity_factor)
    prod_kwh = annual_kwh

    rows = []
    cashflows = []
    cumulative = -initial_outlay

    for year in range(1, lifetime + 1):
        revenue_energy = prod_kwh * price
        mwh = prod_kwh / 1000.0
        carbon_t = mwh * grid_intensity
        revenue_carbon = carbon_t * carbon_price

        total_revenue = revenue_energy + revenue_carbon
        net = total_revenue - opex

        cashflows.append(net)
        cumulative += net

        rows.append({
            "Year": year,
            "Energy (kWh)": prod_kwh,
            "Energy Revenue ($)": revenue_energy,
            "Carbon Revenue ($)": revenue_carbon,
            "Total Revenue ($)": total_revenue,
            "OPEX ($)": opex,
            "Net Cashflow ($)": net,
            "Cumulative ($)": cumulative,
        })

        prod_kwh *= (1 - deg)

    npv = -initial_outlay + sum(cf / ((1 + disc) ** i) for i, cf in enumerate(cashflows, start=1))
    irr = npf.irr([-initial_outlay] + cashflows)

    payback = None
    cum2 = -initial_outlay
    for i, cf in enumerate(cashflows, start=1):
        cum2 += cf
        if cum2 >= 0:
            payback = i
            break

    profit = sum(cashflows) - initial_outlay

    df = pd.DataFrame(rows)
    return dict(npv=npv, irr=irr, payback=payback, profit=profit, df=df, annual_kwh=annual_kwh, cashflows=cashflows)

econ = full_economics()
npv, irr, payback, profit = econ["npv"], econ["irr"], econ["payback"], econ["profit"]
df_cf = econ["df"]
annual_kwh = econ["annual_kwh"]

# ============================================================
# PRE-FEASIBILITY SCORECARD (numbers + insight)
# ============================================================
def pre_feasibility_score():
    # Derived metrics investors like
    year1_total_rev = safe_float(df_cf.loc[0, "Total Revenue ($)"])
    year1_carbon_rev = safe_float(df_cf.loc[0, "Carbon Revenue ($)"])
    year1_net = safe_float(df_cf.loc[0, "Net Cashflow ($)"])

    capex_per_kw = build_capex / (capacity_mw * 1e3)  # $/kW
    dev_per_mw = (pre_total + lic_total) / max(capacity_mw, 0.001)
    grid_share = transmission_cost / max(build_capex, 1.0)
    carbon_share = year1_carbon_rev / max(year1_total_rev, 1.0)

    roi_multiple = (profit + initial_outlay) / max(initial_outlay, 1.0)  # (total returned) / initial
    # If profit is negative, this still behaves and signals.
    margin = year1_net / max(year1_total_rev, 1.0)

    # Scoring weights (tune as you like)
    score = 0
    notes = []

    # IRR
    if irr is not None and not np.isnan(irr):
        if irr >= 0.15:
            score += 30; notes.append("IRR strong (≥15%).")
        elif irr >= 0.10:
            score += 20; notes.append("IRR acceptable (10–15%).")
        elif irr >= 0.08:
            score += 12; notes.append("IRR near hurdle (8–10%).")
        else:
            score += 0; notes.append("IRR below typical hurdle (<8%).")
    else:
        notes.append("IRR not computable (cashflows may be negative).")

    # NPV
    if npv > 0:
        score += 18; notes.append("NPV positive (value-creating).")
    else:
        score += 0; notes.append("NPV negative (value-destroying at current assumptions).")

    # Payback
    if payback is not None:
        if payback <= 8:
            score += 12; notes.append("Payback fast (≤8 years).")
        elif payback <= 12:
            score += 7; notes.append("Payback moderate (9–12 years).")
        else:
            score += 2; notes.append("Payback long (>12 years).")
    else:
        notes.append("No payback within model horizon.")

    # CAPEX intensity
    if capex_per_kw <= 1800:
        score += 10; notes.append("CAPEX intensity competitive.")
    elif capex_per_kw <= 2400:
        score += 6; notes.append("CAPEX intensity moderate.")
    else:
        score += 2; notes.append("CAPEX intensity high; verify EPC/equipment pricing.")

    # Transmission burden
    if grid_share <= 0.15:
        score += 8; notes.append("Grid/interconnection cost share reasonable.")
    elif grid_share <= 0.30:
        score += 4; notes.append("Grid cost share meaningful; check route + permits.")
    else:
        score += 1; notes.append("Grid cost share high; distance/interconnection may be a risk.")

    # Carbon dependence
    if carbon_share <= 0.20:
        score += 6; notes.append("Economics not overly dependent on carbon income.")
    else:
        score += 2; notes.append("Economics depends materially on carbon income; verify eligibility/price.")

    # Operating margin
    if margin >= 0.60:
        score += 6; notes.append("Year 1 net margin strong.")
    elif margin >= 0.40:
        score += 4; notes.append("Year 1 net margin acceptable.")
    else:
        score += 1; notes.append("Year 1 net margin thin; review OPEX/price assumptions.")

    # ROI multiple hint
    if roi_multiple >= 2.0:
        score += 10; notes.append("Attractive total return multiple.")
    elif roi_multiple >= 1.4:
        score += 6; notes.append("Decent total return multiple.")
    else:
        score += 2; notes.append("Low total return multiple under current assumptions.")

    # Clamp 0..100
    score = int(max(0, min(100, score)))

    # Recommendation bands
    if score >= 80:
        rec = "STRONG"
        rec_pill = "pill pill-good"
    elif score >= 60:
        rec = "GOOD"
        rec_pill = "pill pill-warn"
    else:
        rec = "WEAK / REVIEW"
        rec_pill = "pill pill-bad"

    summary = {
        "Score": score,
        "Recommendation": rec,
        "NPV ($)": npv,
        "IRR": irr,
        "Payback (yrs)": payback,
        "CAPEX ($/kW)": capex_per_kw,
        "Dev cost ($/MW)": dev_per_mw,
        "Grid cost share": grid_share,
        "Carbon revenue share (Y1)": carbon_share,
        "Year 1 net margin": margin,
        "ROI multiple": roi_multiple,
        "Notes": notes,
        "pill_class": rec_pill,
    }
    return summary

scorecard = pre_feasibility_score()

# ============================================================
# KPI CARDS
# ============================================================
risk = "High Risk"
if irr is not None and not np.isnan(irr):
    if irr >= 0.15: risk = "Low Risk"
    elif irr >= 0.08: risk = "Medium Risk"
risk_color = "#16A34A" if risk == "Low Risk" else "#D97706" if risk == "Medium Risk" else "#DC2626"

k1, k2, k3, k4, k5, k6 = st.columns([1.18, 1.02, 1.02, 1.05, 1.02, 1.10], gap="medium")

with k1:
    st.markdown(f"""
<div class="card">
  <div class="kpi-title">Pre‑Feasibility Score</div>
  <div class="kpi-value">{scorecard["Score"]}/100</div>
  <div class="kpi-sub"><span class="{scorecard["pill_class"]}">{scorecard["Recommendation"]}</span></div>
</div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""
<div class="card">
  <div class="kpi-title">NPV (incl. carbon)</div>
  <div class="kpi-value" style="color:#1D4ED8;">{money(npv)}</div>
  <div class="kpi-sub">Initial outlay: <b>{money(initial_outlay)}</b></div>
</div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
<div class="card">
  <div class="kpi-title">IRR</div>
  <div class="kpi-value" style="color:#15803D;">{pct(irr)}</div>
  <div class="kpi-sub">Hurdle guidance: 8–15%+</div>
</div>""", unsafe_allow_html=True)

with k4:
    st.markdown(f"""
<div class="card">
  <div class="kpi-title">Payback</div>
  <div class="kpi-value" style="color:#B45309;">{years(payback)}</div>
  <div class="kpi-sub">From {entry_stage} entry</div>
</div>""", unsafe_allow_html=True)

with k5:
    st.markdown(f"""
<div class="card">
  <div class="kpi-title">Build CAPEX</div>
  <div class="kpi-value">{money(build_capex)}</div>
  <div class="kpi-sub">Equipment + EPC + grid</div>
</div>""", unsafe_allow_html=True)

with k6:
    st.markdown(f"""
<div class="card">
  <div class="kpi-title">Risk</div>
  <div class="kpi-value" style="color:{risk_color};">{risk}</div>
  <div class="kpi-sub">Investor: {"RTB-only" if rtb_only else "Flexible"} • {experience}</div>
</div>""", unsafe_allow_html=True)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# ============================================================
# TABLES (Feasibility + Costs)
# ============================================================
def feasibility_numbers_table():
    year1 = df_cf.iloc[0]
    capex_per_kw = build_capex / (capacity_mw * 1e3)
    dev_total = pre_total + lic_total
    dev_per_mw = dev_total / max(capacity_mw, 0.001)
    grid_share = transmission_cost / max(build_capex, 1.0)
    carbon_share = float(year1["Carbon Revenue ($)"]) / max(float(year1["Total Revenue ($)"]), 1.0)
    roi_multiple = scorecard["ROI multiple"]

    rows = [
        ("Initial outlay (from entry)", initial_outlay, "Total investor outlay at selected entry stage"),
        ("NPV", npv, "Discounted value created (positive is good)"),
        ("IRR", irr, "Return profile (compare vs hurdle)"),
        ("Payback (yrs)", payback if payback else np.nan, "Years to recover initial outlay"),
        ("Year 1 total revenue", float(year1["Total Revenue ($)"]), "Energy + carbon"),
        ("Year 1 net cashflow", float(year1["Net Cashflow ($)"]), "After OPEX"),
        ("ROI multiple (total return / invested)", roi_multiple, "Simple multiple over lifetime"),
        ("CAPEX intensity ($/kW)", capex_per_kw, "Build CAPEX per kW"),
        ("Dev intensity ($/MW)", dev_per_mw, "Dev spend per MW to RTB"),
        ("Grid cost share", grid_share, "Transmission/interconnection share of build CAPEX"),
        ("Carbon revenue share (Y1)", carbon_share, "Dependence on carbon income"),
    ]
    df = pd.DataFrame(rows, columns=["Metric", "Value", "Insight"])
    return df

def costs_table():
    rows = [
        ("DEV", "Pre-licensing total", pre_total),
        ("DEV", "Licensing total", lic_total),
        ("DEV", "Already spent (by stage)", dev_spent),
        ("DEV", "Remaining to RTB", dev_remaining),
        ("CAPEX", "Equipment (turbines/panels)", equip_cost),
        ("CAPEX", "Construction / EPC", construction_cost),
        ("CAPEX", f"Transmission ({km} km × $100k/km)", transmission_cost),
        ("CAPEX", "Build CAPEX total", build_capex),
        ("TOTAL", "Initial outlay (from entry)", initial_outlay),
    ]
    return pd.DataFrame(rows, columns=["Bucket", "Item", "Cost ($)"])

left, right = st.columns([1.15, 1.25], gap="large")

with left:
    st.markdown("### Pre‑Feasibility (Numbers)")
    fn = feasibility_numbers_table()
    fn_show = fn.copy()

    def format_value(metric, v):
        if metric in ("IRR",):
            return pct(v)
        if "share" in metric.lower():
            return f"{v*100:.1f}%" if isinstance(v, (float, np.floating)) and not np.isnan(v) else "—"
        if "Payback" in metric:
            return years(int(v)) if v == v and not np.isnan(v) else "—"
        if "($/kW)" in metric or "($/MW)" in metric:
            return f"${v:,.0f}" if isinstance(v, (float, np.floating)) else "—"
        if "ROI multiple" in metric:
            return f"{v:.2f}x" if isinstance(v, (float, np.floating)) else "—"
        if "Year 1" in metric or metric in ("NPV", "Initial outlay (from entry)"):
            return money(v)
        return str(v)

    fn_show["Value"] = [format_value(m, v) for m, v in zip(fn_show["Metric"], fn_show["Value"])]
    st.dataframe(fn_show, use_container_width=True, hide_index=True)

    st.markdown("**Investor insight**")
    st.markdown("- " + "\n- ".join(scorecard["Notes"]))

with right:
    st.markdown("### Costs Table (DEV + CAPEX)")
    ct = costs_table()
    ct_show = ct.copy()
    ct_show["Cost ($)"] = ct_show["Cost ($)"].map(lambda v: f"{v:,.0f}")
    st.dataframe(ct_show, use_container_width=True, hide_index=True)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# ============================================================
# CHARTS
# ============================================================
tab1, tab2, tab3 = st.tabs(["Charts", "Development Tasks", "Cashflows"])

with tab1:
    a, b = st.columns([1.4, 1.0], gap="large")

    fig_cum = px.area(
        df_cf, x="Year", y="Cumulative ($)",
        title="Cumulative Cashflow ($) — from entry stage",
        template="plotly_white",
    )
    fig_cum.update_traces(line=dict(color=BRAND_ORANGE, width=3), fillcolor="rgba(255,106,0,0.20)")
    fig_cum.update_layout(
        margin=dict(l=10, r=10, t=55, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(15, 23, 42, 0.08)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(15, 23, 42, 0.08)", tickprefix="$"),
        title_font=dict(size=16, color="#0F172A"),
    )

    fig_rev = px.bar(
        df_cf, x="Year", y=["Energy Revenue ($)", "Carbon Revenue ($)"],
        title="Revenue Composition — Energy vs Carbon",
        template="plotly_white", barmode="stack",
    )
    fig_rev.update_layout(
        margin=dict(l=10, r=10, t=55, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(15, 23, 42, 0.08)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(15, 23, 42, 0.08)", tickprefix="$"),
        legend_title_text="",
        title_font=dict(size=16, color="#0F172A"),
    )

    with a:
        st.plotly_chart(fig_cum, use_container_width=True)
    with b:
        st.plotly_chart(fig_rev, use_container_width=True)

with tab2:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("### Pre‑licensing tasks")
        pre_show = pre_tasks_df.copy()
        pre_show["Cost ($)"] = pre_show["Cost ($)"].map(lambda v: f"{v:,.0f}")
        st.dataframe(pre_show, use_container_width=True, hide_index=True)
        st.caption(f"Pre‑licensing total: {money(pre_total)}")

    with c2:
        st.markdown("### Licensing tasks")
        lic_show = lic_tasks_df.copy()
        lic_show["Cost ($)"] = lic_show["Cost ($)"].map(lambda v: f"{v:,.0f}")
        st.dataframe(lic_show, use_container_width=True, hide_index=True)
        st.caption(f"Licensing total: {money(lic_total)}")

with tab3:
    st.markdown("### Cashflows (export-ready)")
    df_show = df_cf.copy()
    for col in ["Energy Revenue ($)", "Carbon Revenue ($)", "Total Revenue ($)", "OPEX ($)", "Net Cashflow ($)", "Cumulative ($)"]:
        df_show[col] = df_show[col].map(lambda v: f"{v:,.0f}")
    df_show["Energy (kWh)"] = df_show["Energy (kWh)"].map(lambda v: f"{v:,.0f}")
    st.dataframe(df_show, use_container_width=True, hide_index=True)
    st.download_button("Download cashflows CSV", data=df_cf.to_csv(index=False).encode("utf-8"),
                       file_name="cashflows.csv", mime="text/csv")

# ============================================================
# PDF REPORT GENERATION
# ============================================================
# def plotly_fig_to_png_bytes(fig) -> bytes:
#     # Requires kaleido installed
#     return fig.to_image(format="png", scale=2)

def make_report_html(fig_cum_png_uri: str, fig_rev_png_uri: str) -> str:
    today = date.today().isoformat()

    # Basic HTML/CSS for PDF print
    logo_tag = f'<img src="{logo_uri}" style="height:40px; width:auto;" />' if logo_uri else ""
    rec_class = scorecard["pill_class"]

    # Tables to HTML
    ct = costs_table().copy()
    ct["Cost ($)"] = ct["Cost ($)"].map(lambda v: f"{v:,.0f}")
    ct_html = ct.to_html(index=False, escape=False)

    fn = feasibility_numbers_table().copy()
    # Format feasibility values for report
    def report_val(metric, v):
        if metric == "IRR":
            return pct(v)
        if "share" in metric.lower():
            return f"{v*100:.1f}%"
        if "Payback" in metric:
            return years(int(v)) if v == v else "—"
        if "ROI multiple" in metric:
            return f"{v:.2f}x"
        if "($/kW)" in metric or "($/MW)" in metric:
            return f"${v:,.0f}"
        if metric in ("NPV", "Initial outlay (from entry)", "Year 1 total revenue", "Year 1 net cashflow"):
            return money(v)
        return str(v)
    fn["Value"] = [report_val(m, v) for m, v in zip(fn["Metric"], fn["Value"])]
    fn_html = fn.to_html(index=False, escape=False)
    
    pre_rep = pre_tasks_df.copy()
    pre_rep["Cost ($)"] = pre_rep["Cost ($)"].map(lambda v: f"{v:,.0f}")
    lic_rep = lic_tasks_df.copy()
    lic_rep["Cost ($)"] = lic_rep["Cost ($)"].map(lambda v: f"{v:,.0f}")

    pre_html = pre_rep.to_html(index=False, escape=False)
    lic_html = lic_rep.to_html(index=False, escape=False)

    insight_list = "".join([f"<li>{n}</li>" for n in scorecard["Notes"]])
    import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

def fig_to_png_bytes_matplotlib(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()

def make_mpl_charts(df_cf: pd.DataFrame, brand_orange: str):
    # 1) Cumulative cashflow
    fig1, ax1 = plt.subplots(figsize=(7.2, 3.6))
    ax1.plot(df_cf["Year"], df_cf["Cumulative ($)"], linewidth=3, color=brand_orange)
    ax1.fill_between(df_cf["Year"], df_cf["Cumulative ($)"], alpha=0.15, color=brand_orange)
    ax1.set_title("Cumulative Cashflow ($)", fontweight="bold")
    ax1.grid(True, alpha=0.25)
    ax1.set_xlabel("Year")
    ax1.set_ylabel("$")
    fig1.tight_layout()

    # 2) Revenue composition stacked bars (Energy + Carbon)
    fig2, ax2 = plt.subplots(figsize=(7.2, 3.6))
    ax2.bar(df_cf["Year"], df_cf["Energy Revenue ($)"], label="Energy", color="#1D4ED8", alpha=0.85)
    ax2.bar(df_cf["Year"], df_cf["Carbon Revenue ($)"],
            bottom=df_cf["Energy Revenue ($)"], label="Carbon", color=brand_orange, alpha=0.85)
    ax2.set_title("Revenue Composition — Energy vs Carbon", fontweight="bold")
    ax2.grid(True, axis="y", alpha=0.25)
    ax2.set_xlabel("Year")
    ax2.set_ylabel("$")
    ax2.legend(frameon=False)
    fig2.tight_layout()

    return fig1, fig2
def make_html_report_with_mpl_charts(df_cf, brand_orange, kpis, costs_table, feasibility_table):
    fig1, fig2 = make_mpl_charts(df_cf, brand_orange)
    img1_uri = "data:image/png;base64," + base64.b64encode(fig_to_png_bytes_matplotlib(fig1)).decode("utf-8")
    img2_uri = "data:image/png;base64," + base64.b64encode(fig_to_png_bytes_matplotlib(fig2)).decode("utf-8")

    ct = costs_table.copy()
    if "Cost ($)" in ct.columns:
        ct["Cost ($)"] = ct["Cost ($)"].map(lambda v: f"{float(v):,.0f}" if v == v else "—")

    html = f"""
    <html><head><meta charset="utf-8">
    <style>
      body {{ font-family: Arial; color:#0F172A; background:#F6F8FC; padding: 22px; }}
      .card {{ background:#fff; border:1px solid rgba(15,23,42,.12); border-radius:14px; padding:14px; margin-bottom:14px; }}
      .accent {{ height:4px; background:linear-gradient(90deg,{brand_orange}, rgba(255,106,0,0)); border-radius:999px; }}
      table {{ width:100%; border-collapse: collapse; font-size: 12px; }}
      th, td {{ border:1px solid rgba(15,23,42,.12); padding:8px; text-align:left; }}
      th {{ background:#F1F5F9; }}
      img {{ max-width:100%; }}
    </style></head><body>
      <div class="card">
        <h2 style="margin:0;">Renewable Investment Memo</h2>
        <div class="accent"></div>
        <p><b>Score:</b> {kpis.get("score","—")}/100 ({kpis.get("recommendation","—")})</p>
        <p><b>NPV:</b> {kpis.get("npv","—")} &nbsp; <b>IRR:</b> {kpis.get("irr","—")} &nbsp; <b>Payback:</b> {kpis.get("payback","—")}</p>
        <p><b>Initial outlay:</b> {kpis.get("initial_outlay","—")} &nbsp; <b>Build CAPEX:</b> {kpis.get("build_capex","—")}</p>
      </div>

      <div class="card">
        <h3>Costs Summary</h3>
        {ct.to_html(index=False)}
      </div>

      <div class="card">
        <h3>Pre-feasibility Highlights</h3>
        {feasibility_table.to_html(index=False)}
      </div>

      <div class="card">
        <h3>Charts</h3>
        <img src="{img1_uri}" />
        <br/><br/>
        <img src="{img2_uri}" />
      </div>
    </body></html>
    """
    return html
def build_pdf_report(
    *,
    logo_path: str,
    brand_orange: str,
    project_type: str,
    entry_stage: str,
    kpis: dict,
    costs_table: pd.DataFrame,
    feasibility_table: pd.DataFrame,
    df_cf: pd.DataFrame,
) -> bytes:
    """
    Pure-Python PDF report for Streamlit Cloud:
    - uses Matplotlib for charts
    - uses ReportLab for PDF layout
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Header
    y = height - 50
    if Path(logo_path).exists():
        c.drawImage(logo_path, 40, y - 10, width=90, height=28, mask='auto')
    c.setFont("Helvetica-Bold", 16)
    c.drawString(140, y, "Renewable Investment Memo")
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.25, 0.25, 0.25)
    c.drawString(140, y - 14, f"{project_type} • Entry stage: {entry_stage}")
    c.setFillColorRGB(0, 0, 0)

    # Accent line
    r = int(brand_orange[1:3], 16) / 255
    g = int(brand_orange[3:5], 16) / 255
    b = int(brand_orange[5:7], 16) / 255
    c.setStrokeColorRGB(r, g, b)
    c.setLineWidth(3)
    c.line(40, y - 26, width - 40, y - 26)

    # KPI block
    y2 = y - 70
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y2, "Executive KPIs")
    c.setFont("Helvetica", 10)

    kpi_lines = [
        f"Pre-feasibility score: {kpis.get('score','—')}/100 ({kpis.get('recommendation','—')})",
        f"NPV: {kpis.get('npv','—')}   |   IRR: {kpis.get('irr','—')}   |   Payback: {kpis.get('payback','—')}",
        f"Initial outlay: {kpis.get('initial_outlay','—')}   |   Build CAPEX: {kpis.get('build_capex','—')}",
    ]
    yy = y2 - 18
    for line in kpi_lines:
        c.drawString(40, yy, line)
        yy -= 14

    # Helper to draw simple tables
    def draw_table(title, df: pd.DataFrame, x, y, max_rows=10):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, y, title)
        y -= 14
        c.setFont("Helvetica", 8.8)

        # Column headers
        cols = list(df.columns)
        col_widths = [140] + [120] * (len(cols) - 1)
        # header
        xx = x
        for i, col in enumerate(cols):
            c.setFont("Helvetica-Bold", 8.8)
            c.drawString(xx, y, str(col)[:28])
            c.setFont("Helvetica", 8.8)
            xx += col_widths[i] if i < len(col_widths) else 110
        y -= 10

        # rows
        for _, row in df.head(max_rows).iterrows():
            xx = x
            for i, col in enumerate(cols):
                val = str(row[col])
                c.drawString(xx, y, val[:34])
                xx += col_widths[i] if i < len(col_widths) else 110
            y -= 10

        return y - 8

    # Prepare tables (format first)
    costs = costs_table.copy()
    if "Cost ($)" in costs.columns:
        costs["Cost ($)"] = costs["Cost ($)"].map(lambda v: f"{float(v):,.0f}" if v == v else "—")

    feas = feasibility_table.copy()

    # Tables on first page
    y_tables_top = yy - 10
    y_left_end = draw_table("Costs Summary (Top)", costs[["Bucket","Item","Cost ($)"]], 40, y_tables_top, max_rows=10)
    y_right_end = draw_table("Pre-feasibility Highlights", feas, 300, y_tables_top, max_rows=10)

    # Charts page
    c.showPage()
    fig1, fig2 = make_mpl_charts(df_cf, brand_orange)
    img1 = ImageReader(io.BytesIO(fig_to_png_bytes_matplotlib(fig1)))
    img2 = ImageReader(io.BytesIO(fig_to_png_bytes_matplotlib(fig2)))

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - 50, "Charts")
    c.drawImage(img1, 40, height - 350, width=520, height=260, preserveAspectRatio=True, mask='auto')
    c.drawImage(img2, 40, height - 650, width=520, height=260, preserveAspectRatio=True, mask='auto')

    c.showPage()

    # Cashflows page (first N rows)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - 50, "Cashflows (first 15 years)")
    cash = df_cf.copy()
    cash_small = cash[["Year","Total Revenue ($)","OPEX ($)","Net Cashflow ($)","Cumulative ($)"]].head(15)
    for col in cash_small.columns:
        if col != "Year":
            cash_small[col] = cash_small[col].map(lambda v: f"{float(v):,.0f}")

    _ = draw_table("Cashflow Table", cash_small, 40, height - 80, max_rows=15)

    c.save()
    buf.seek(0)
    return buf.read()
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  @page {{ size: A4; margin: 18mm; }}
  body {{ font-family: Arial, Helvetica, sans-serif; color: #0F172A; }}
  .header {{
    border: 1px solid rgba(15,23,42,.12);
    border-radius: 14px;
    padding: 12px 14px;
  }}
  .accent {{ height: 4px; background: linear-gradient(90deg, {BRAND_ORANGE}, rgba(255,106,0,0)); border-radius: 999px; margin-top: 10px; }}
  .row {{ display:flex; gap: 12px; align-items: stretch; }}
  .grow {{ flex: 1; }}
  .kpi {{
    border: 1px solid rgba(15,23,42,.12);
    border-radius: 14px;
    padding: 12px;
    background: #fff;
  }}
  .kpi-title {{ font-size: 11px; color: rgba(15,23,42,.70); }}
  .kpi-value {{ font-size: 26px; font-weight: 800; margin-top: 4px; }}
  .pill {{
    display:inline-block; padding: 6px 10px; border-radius: 999px; font-size: 12px;
    border: 1px solid rgba(15,23,42,0.10); background: #F8FAFF;
  }}
  .pill-good {{ border-color: rgba(22,163,74,.35); background: rgba(22,163,74,.08); color:#14532D; }}
  .pill-warn {{ border-color: rgba(217,119,6,.35); background: rgba(217,119,6,.10); color:#7C2D12; }}
  .pill-bad  {{ border-color: rgba(220,38,38,.35); background: rgba(220,38,38,.08); color:#7F1D1D; }}
  h2 {{ margin: 18px 0 8px 0; font-size: 16px; }}
  h3 {{ margin: 14px 0 8px 0; font-size: 13px; }}
  .muted {{ color: rgba(15,23,42,.70); font-size: 12px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  th, td {{ border: 1px solid rgba(15,23,42,.12); padding: 6px 8px; text-align: left; }}
  th {{ background: #F1F5F9; }}
  .chart {{ border: 1px solid rgba(15,23,42,.12); border-radius: 14px; padding: 10px; background: #fff; }}
  img {{ max-width: 100%; }}
  ul {{ margin: 6px 0 0 18px; }}
</style>
</head>
<body>

<div class="header">
  <div style="display:flex; justify-content:space-between; align-items:center; gap: 10px;">
    <div style="display:flex; align-items:center; gap: 12px;">
      {logo_tag}
      <div>
        <div style="font-weight:900; font-size:18px;">Renewable Investment Memo</div>
        <div class="muted">Generated: {today} • Project type: {project_type} • Entry stage: {entry_stage}</div>
      </div>
    </div>
    <div class="pill" style="border-color: rgba(255,106,0,.35); background: rgba(255,106,0,.10); color:#7A2E00;">
      Orange Accent
    </div>
  </div>
  <div class="accent"></div>
</div>

<h2>Executive Summary</h2>
<div class="row">
  <div class="kpi grow">
    <div class="kpi-title">Pre‑Feasibility Score</div>
    <div class="kpi-value">{scorecard["Score"]}/100</div>
    <div class="{rec_class} pill" style="margin-top:6px;">{scorecard["Recommendation"]}</div>
  </div>
  <div class="kpi grow">
    <div class="kpi-title">NPV (incl. carbon)</div>
    <div class="kpi-value" style="color:#1D4ED8;">{money(npv)}</div>
    <div class="muted">Initial outlay: {money(initial_outlay)}</div>
  </div>
  <div class="kpi grow">
    <div class="kpi-title">IRR</div>
    <div class="kpi-value" style="color:#15803D;">{pct(irr)}</div>
    <div class="muted">Discount rate: {discount:.2f}%</div>
  </div>
  <div class="kpi grow">
    <div class="kpi-title">Payback</div>
    <div class="kpi-value" style="color:#B45309;">{years(payback)}</div>
    <div class="muted">Lifetime: {lifetime} yrs</div>
  </div>
</div>

<h2>Pre‑Feasibility (Numbers)</h2>
{fn_html}

<h3>Investor insights</h3>
<ul>{insight_list}</ul>

<h2>Costs Summary</h2>
{ct_html}

<h2>Charts</h2>
<div class="row">
  <div class="chart grow">
    <div style="font-weight:700; margin-bottom:6px;">Cumulative Cashflow</div>
    <img src="{fig_cum_png_uri}" />
  </div>
  <div class="chart grow">
    <div style="font-weight:700; margin-bottom:6px;">Revenue Composition</div>
    <img src="{fig_rev_png_uri}" />
  </div>
</div>

<h2>Development Tasks</h2>
<h3>Pre‑licensing (total: {money(pre_total)})</h3>
{pre_html}

<h3>Licensing (total: {money(lic_total)})</h3>
{lic_html}

<p class="muted">
Transmission assumption: {km} km × $100,000/km = <b>{money(transmission_cost)}</b>.
Carbon assumption: ${carbon_price:.2f}/tCO₂ and {grid_intensity:.2f} tCO₂/MWh displaced.
</p>

</body>
</html>
"""
    return html

def make_html_report_with_mpl_charts(df_cf, brand_orange, kpis, costs_table, feasibility_table):
    fig1, fig2 = make_mpl_charts(df_cf, brand_orange)
    img1_uri = "data:image/png;base64," + base64.b64encode(fig_to_png_bytes_matplotlib(fig1)).decode("utf-8")
    img2_uri = "data:image/png;base64," + base64.b64encode(fig_to_png_bytes_matplotlib(fig2)).decode("utf-8")
    
    ct = costs_table.copy()
    if "Cost ($)" in ct.columns:
        ct["Cost ($)"] = ct["Cost ($)"].map(lambda v: f"{float(v):,.0f}" if v == v else "—")
    
    html = f"""
    <html><head><meta charset="utf-8">
    <style>
      body {{ font-family: Arial; color:#0F172A; background:#F6F8FC; padding: 22px; }}
      .card {{ background:#fff; border:1px solid rgba(15,23,42,.12); border-radius:14px; padding:14px; margin-bottom:14px; }}
      .accent {{ height:4px; background:linear-gradient(90deg,{brand_orange}, rgba(255,106,0,0)); border-radius:999px; }}
      table {{ width:100%; border-collapse: collapse; font-size: 12px; }}
      th, td {{ border:1px solid rgba(15,23,42,.12); padding:8px; text-align:left; }}
      th {{ background:#F1F5F9; }}
      img {{ max-width:100%; }}
    </style></head><body>
      <div class="card">
        <h2 style="margin:0;">Renewable Investment Memo</h2>
        <div class="accent"></div>
        <p><b>Score:</b> {kpis.get("score","—")}/100 ({kpis.get("recommendation","—")})</p>
        <p><b>NPV:</b> {kpis.get("npv","—")} &nbsp; <b>IRR:</b> {kpis.get("irr","—")} &nbsp; <b>Payback:</b> {kpis.get("payback","—")}</p>
        <p><b>Initial outlay:</b> {kpis.get("initial_outlay","—")} &nbsp; <b>Build CAPEX:</b> {kpis.get("build_capex","—")}</p>
      </div>
    
      <div class="card">
        <h3>Costs Summary</h3>
        {ct.to_html(index=False)}
      </div>
    
      <div class="card">
        <h3>Pre-feasibility Highlights</h3>
        {feasibility_table.to_html(index=False)}
      </div>
    
      <div class="card">
        <h3>Charts</h3>
        <img src="{img1_uri}" />
        <br/><br/>
        <img src="{img2_uri}" />
      </div>
    </body></html>
    """
    return html
st.markdown("### Report Export")
create_pdf = st.button("Create Report (PDF)", type="primary", use_container_width=True)

if create_pdf:
    # Example feasibility table (use your existing one)
    feas_table = feasibility_numbers_table()[["Metric","Value","Insight"]].copy()

    # Example costs table (use your existing one)
    costs = costs_table().copy()

    kpis = {
        "score": scorecard["Score"],
        "recommendation": scorecard["Recommendation"],
        "npv": money(npv),
        "irr": pct(irr),
        "payback": years(payback),
        "initial_outlay": money(initial_outlay),
        "build_capex": money(build_capex),
    }

    pdf_bytes = build_pdf_report(
        logo_path=LOGO_PATH,
        brand_orange=BRAND_ORANGE,
        project_type=project_type,
        entry_stage=entry_stage,
        kpis=kpis,
        costs_table=costs,
        feasibility_table=feas_table,
        df_cf=df_cf,
    )

    st.download_button(
        "Download report.pdf",
        data=pdf_bytes,
        file_name="investment_memo.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
st.markdown("### Report Export")
colA, colB = st.columns([1, 1], gap="medium")

with colA:
    create_pdf = st.button(
        "Create Report (PDF)",
        type="primary",
        use_container_width=True,
        key="create_report_pdf",
    )
with colB:
    create_html = st.button(
        "Download Report (HTML)",
        use_container_width=True,
        key="create_report_html",
    )
if create_html:
    # Reuse your existing HTML report builder if you have it.
    # If your old one depends on plotly->png exports, keep it HTML-only.
    html = make_html_report_with_mpl_charts(df_cf, BRAND_ORANGE, kpis, costs, feas_table)  # <-- replace with your existing HTML generator
    st.download_button(
        "Download investment_memo.html",
        data=html.encode("utf-8"),
        file_name="investment_memo.html",
        mime="text/html",
        use_container_width=True,
    )

if create_pdf:
    feas_table = feasibility_numbers_table()[["Metric", "Value", "Insight"]].copy()
    costs = costs_table().copy()

    kpis = {
        "score": scorecard["Score"],
        "recommendation": scorecard["Recommendation"],
        "npv": money(npv),
        "irr": pct(irr),
        "payback": years(payback),
        "initial_outlay": money(initial_outlay),
        "build_capex": money(build_capex),
    }

    pdf_bytes = build_pdf_report(
        logo_path=LOGO_PATH,
        brand_orange=BRAND_ORANGE,
        project_type=project_type,
        entry_stage=entry_stage,
        kpis=kpis,
        costs_table=costs,
        feasibility_table=feas_table,
        df_cf=df_cf,
    )

    st.download_button(
        "Download investment_memo.pdf",
        data=pdf_bytes,
        file_name="investment_memo.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
    
