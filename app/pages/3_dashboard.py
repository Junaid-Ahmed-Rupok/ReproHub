"""
Dashboard Page — Results Visualization

Renders a rich, scannable verification dashboard. The page's job:
give a researcher an at-a-glance read of every claim's outcome and
let them drill into the numbers without leaving the page.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Any

# ── Status config ─────────────────────────────────────────────────────────────
_STATUS = {
    "reproduced": {
        "label": "Reproduced",
        "color": "#10B981",
        "bg": "rgba(16,185,129,0.15)",
        "icon": "✓",
        "rank": 1,
    },
    "marginal": {
        "label": "Marginal",
        "color": "#F59E0B",
        "bg": "rgba(245,158,11,0.15)",
        "icon": "~",
        "rank": 2,
    },
    "not_reproduced": {
        "label": "Not Reproduced",
        "color": "#EF4444",
        "bg": "rgba(239,68,68,0.15)",
        "icon": "✗",
        "rank": 3,
    },
    "could_not_verify": {
        "label": "Could Not Verify",
        "color": "#8B95A9",
        "bg": "rgba(139,149,169,0.15)",
        "icon": "?",
        "rank": 4,
    },
}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif !important;
}

.stApp {
    background: #0B0F19;
    color: #E2E8F0;
}

/* ── Glassmorphism Utility ── */
.glass-panel {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 20px;
}

/* ── Page header ── */
.db-header {
    display: flex;
    align-items: center;
    gap: 18px;
    margin-bottom: 32px;
    padding-bottom: 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.db-header-icon {
    width: 52px;
    height: 52px;
    flex-shrink: 0;
    background: linear-gradient(135deg, #7C3AED, #5B4FE8);
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    box-shadow: 0 8px 24px rgba(91, 79, 232, 0.25);
}
.db-header-title {
    font-size: 26px;
    font-weight: 700;
    color: #F8FAFC;
    margin: 0;
    line-height: 1.2;
    letter-spacing: -0.02em;
}
.db-header-sub {
    font-size: 13px;
    color: #94A3B8;
    margin-top: 2px;
    font-weight: 400;
}

/* ── Score hero ── */
.db-score-hero {
    background: linear-gradient(135deg, rgba(91, 79, 232, 0.12) 0%, rgba(124, 58, 237, 0.05) 100%);
    border: 1px solid rgba(91, 79, 232, 0.2);
    border-radius: 24px;
    padding: 32px 36px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.db-score-hero::before {
    content: '';
    position: absolute;
    top: -60px;
    right: -60px;
    width: 240px;
    height: 240px;
    background: radial-gradient(circle, rgba(91, 79, 232, 0.15) 0%, transparent 70%);
    pointer-events: none;
}
.db-score-number {
    font-size: 64px;
    font-weight: 700;
    line-height: 1;
    color: #F8FAFC;
    letter-spacing: -0.03em;
}
.db-score-pct {
    font-size: 32px;
    font-weight: 300;
    color: #7C3AED;
}
.db-score-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #64748B;
    margin-top: 8px;
}
.db-score-note {
    font-size: 13px;
    color: #94A3B8;
    max-width: 320px;
    line-height: 1.6;
}

/* ── KPI strip ── */
.db-kpi-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 32px;
}
.db-kpi {
    padding: 22px 24px;
    position: relative;
    overflow: hidden;
    transition: all 0.2s ease;
}
.db-kpi:hover {
    border-color: rgba(255, 255, 255, 0.12);
    transform: translateY(-2px);
}
.db-kpi-accent {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    border-radius: 20px 20px 0 0;
}
.db-kpi-num {
    font-size: 36px;
    font-weight: 700;
    line-height: 1;
    margin-top: 8px;
    letter-spacing: -0.02em;
}
.db-kpi-label {
    font-size: 11px;
    color: #64748B;
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 500;
}
.db-kpi-bar {
    height: 4px;
    border-radius: 4px;
    margin-top: 14px;
    background: rgba(255, 255, 255, 0.06);
}
.db-kpi-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.8s cubic-bezier(0.22, 1, 0.36, 1);
}

/* ── Section label ── */
.db-section-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #475569;
    margin: 32px 0 16px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.db-section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: rgba(255, 255, 255, 0.06);
}

/* ── Chart container ── */
.db-chart-wrap {
    padding: 12px 12px 4px;
    margin-bottom: 0;
}

/* ── Callout ── */
.db-callout {
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid rgba(245, 158, 11, 0.15);
    border-radius: 14px;
    padding: 16px 20px;
    font-size: 13px;
    color: #FCD34D;
    line-height: 1.6;
    margin-bottom: 24px;
}
.db-callout b {
    font-weight: 600;
}

/* ── Empty state ── */
.db-empty {
    text-align: center;
    padding: 80px 24px;
}
.db-empty-icon {
    font-size: 56px;
    margin-bottom: 20px;
    opacity: 0.6;
}
.db-empty-title {
    font-size: 20px;
    font-weight: 600;
    color: #CBD5E1;
    margin-bottom: 8px;
}
.db-empty-sub {
    font-size: 14px;
    color: #64748B;
}

/* ── Table override (st.dataframe) ── */
[data-testid="stDataFrame"] {
    background: transparent !important;
}
[data-testid="stDataFrame"] table {
    border-collapse: separate !important;
    border-spacing: 0 4px !important;
}
[data-testid="stDataFrame"] thead tr th {
    background: rgba(255, 255, 255, 0.04) !important;
    color: #94A3B8 !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
    padding: 12px 16px !important;
}
[data-testid="stDataFrame"] tbody tr td {
    background: rgba(255, 255, 255, 0.02) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
    padding: 12px 16px !important;
    color: #E2E8F0 !important;
    font-size: 13px !important;
}
[data-testid="stDataFrame"] tbody tr:hover td {
    background: rgba(255, 255, 255, 0.05) !important;
}

/* ── Download Button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #5B4FE8, #7C3AED) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 28px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 16px rgba(91, 79, 232, 0.3) !important;
}
.stDownloadButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(91, 79, 232, 0.4) !important;
}

/* ── Plotly override ── */
.js-plotly-plot .plotly {
    background: transparent !important;
}
</style>
"""


def _fmt_p(v: Any) -> str:
    if v is None or pd.isna(v):
        return "—"
    try:
        v = float(v)
        if v < 0.001:
            return "<.001"
        return f"{v:.4f}"
    except (ValueError, TypeError):
        return "—"


def _score_color(score: int) -> str:
    if score >= 75:
        return "#10B981"
    if score >= 40:
        return "#F59E0B"
    return "#EF4444"


def _donut_chart(counts: Dict[str, int], total: int):
    """Render a clean donut chart via Plotly go."""
    present = {k: v for k, v in counts.items() if v > 0}
    labels = [_STATUS[k]["label"] for k in present]
    values = list(present.values())
    colors = [_STATUS[k]["color"] for k in present]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.60,
        marker=dict(
            colors=colors,
            line=dict(color="#0B0F19", width=3),
        ),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value} claim(s) — %{percent}<extra></extra>",
        direction="clockwise",
        sort=False,
    ))

    score_pct = round(counts.get("reproduced", 0) / total * 100) if total else 0
    fig.add_annotation(
        text=f"<b style='font-size:32px; color:#F8FAFC;'>{total}</b>",
        x=0.5, y=0.58, showarrow=False,
        font=dict(family="Inter", size=32, color="#F8FAFC"),
    )
    fig.add_annotation(
        text="claims",
        x=0.5, y=0.42, showarrow=False,
        font=dict(family="Inter", size=12, color="#64748B"),
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=16, b=16, l=16, r=16),
        height=300,
        showlegend=True,
        legend=dict(
            font=dict(family="Inter", size=12, color="#94A3B8"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            orientation="v",
            x=0.72, y=0.5,
            xanchor="left", yanchor="middle",
        ),
    )
    return fig


def _bar_chart(results: List[Dict]):
    """Horizontal bar: p-value claimed vs reproduced per claim."""
    rows = [
        r for r in results
        if r.get("claimed_p_value") is not None and not pd.isna(r.get("claimed_p_value"))
        and r.get("reproduced_p_value") is not None and not pd.isna(r.get("reproduced_p_value"))
    ]
    if not rows:
        return None

    ids = [r.get("claim_id", f"C{i+1}") for i, r in enumerate(rows)]
    claimed = [float(r["claimed_p_value"]) for r in rows]
    reproduced = [float(r["reproduced_p_value"]) for r in rows]
    statuses = [r.get("status", "could_not_verify") for r in rows]
    bar_cols = [_STATUS[s]["color"] for s in statuses]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Claimed p",
        y=ids, x=claimed,
        orientation="h",
        marker=dict(color="rgba(91, 79, 232, 0.4)", line=dict(color="#5B4FE8", width=1.5)),
        hovertemplate="<b>%{y}</b><br>Claimed p = %{x:.4f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Reproduced p",
        y=ids, x=reproduced,
        orientation="h",
        marker=dict(color=bar_cols, opacity=0.85),
        hovertemplate="<b>%{y}</b><br>Reproduced p = %{x:.4f}<extra></extra>",
    ))

    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=16, b=8, l=8, r=16),
        height=max(240, 48 * len(rows)),
        font=dict(family="Inter", color="#94A3B8", size=11),
        legend=dict(
            font=dict(family="Inter", size=11, color="#94A3B8"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            orientation="h", x=0, y=1.08,
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.04)",
            zerolinecolor="rgba(255,255,255,0.08)",
            tickfont=dict(family="JetBrains Mono", size=10),
            title=dict(text="p-value", font=dict(size=10, color="#64748B")),
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(family="JetBrains Mono", size=10),
        ),
    )
    return fig


def _format_dataframe(df: pd.DataFrame, claim_lookup: Dict[str, str]) -> pd.DataFrame:
    """Prepare and clean the dataframe for display."""
    df_display = df.copy()

    # 1. Map Claim ID to Claim Text
    df_display["Claim"] = df_display["claim_id"].map(claim_lookup).fillna(df_display["claim_id"])
    df_display["Claim"] = df_display["Claim"].astype(str).apply(lambda x: x[:75] + "…" if len(x) > 75 else x)

    # 2. Map Status to HTML Chip
    def status_chip(status):
        meta = _STATUS.get(status, _STATUS["could_not_verify"])
        return f"""
        <span style="display:inline-flex; align-items:center; gap:4px; 
                     background:{meta['bg']}; color:{meta['color']}; 
                     padding:2px 10px; border-radius:12px; font-size:11px; font-weight:600;">
            {meta['icon']} {meta['label']}
        </span>
        """
    df_display["Status"] = df_display["status"].apply(status_chip)

    # 3. Format P-Values
    df_display["Claimed p"] = df_display["claimed_p_value"].apply(_fmt_p)
    df_display["Repro. p"] = df_display["reproduced_p_value"].apply(_fmt_p)

    # 4. Format Delta with color
    def fmt_delta(val):
        if val is None or pd.isna(val):
            return "—"
        try:
            val = float(val)
            if val < 0.001:
                return f"<span style='color:#10B981;font-family:JetBrains Mono;'>+{val:.4f}</span>"
            else:
                return f"<span style='color:#EF4444;font-family:JetBrains Mono;'>{val:.4f}</span>"
        except (ValueError, TypeError):
            return "—"
    df_display["Δ"] = df_display["discrepancy"].apply(fmt_delta)

    # 5. Test Type
    df_display["Test"] = df_display["test_type"].fillna("—").astype(str)

    # 6. Select and reorder columns
    df_display = df_display[["Claim", "Test", "Status", "Claimed p", "Repro. p", "Δ"]]
    return df_display


def render():
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="db-header">
      <div class="db-header-icon">📊</div>
      <div>
        <div class="db-header-title">Verification Dashboard</div>
        <div class="db-header-sub">Statistical reproducibility results at a glance</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Guard ─────────────────────────────────────────────────────────────────
    if not st.session_state.get("analysis_complete"):
        st.markdown("""
        <div class="db-empty">
          <div class="db-empty-icon">🔬</div>
          <div class="db-empty-title">No results yet</div>
          <div class="db-empty-sub">Upload a paper and verify its claims first,<br>then return here to explore the results.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    results = st.session_state.results
    score = st.session_state.reproducibility_score
    total = len(results)
    counts = {k: sum(1 for r in results if r.get("status") == k) for k in _STATUS}

    claims = st.session_state.get("confirmed_claims") or st.session_state.get("claims") or []
    claim_lookup = {c.get("id"): c.get("claim_statement") or c.get("id") for c in claims}

    score_c = _score_color(score)

    # ── Score hero ────────────────────────────────────────────────────────────
    repro_rate = round(counts["reproduced"] / total * 100) if total else 0
    st.markdown(f"""
    <div class="db-score-hero glass-panel">
      <div>
        <div class="db-score-number" style="color:{score_c};">
          {score}<span class="db-score-pct">%</span>
        </div>
        <div class="db-score-label">Reproducibility Score</div>
      </div>
      <div class="db-score-note">
        <b style="color:{_STATUS['reproduced']['color']};">{counts['reproduced']} reproduced</b>, 
        <b style="color:{_STATUS['marginal']['color']};">{counts['marginal']} marginal</b>, 
        <b style="color:{_STATUS['not_reproduced']['color']};">{counts['not_reproduced']} failed</b>, 
        <b style="color:{_STATUS['could_not_verify']['color']};">{counts['could_not_verify']} unverifiable</b>.
        <br>Overall success rate: {repro_rate}% of {total} claims.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI strip ─────────────────────────────────────────────────────────────
    kpi_html = '<div class="db-kpi-strip">'
    for key, meta in _STATUS.items():
        n = counts[key]
        pct = round(n / total * 100) if total else 0
        kpi_html += f"""
        <div class="db-kpi glass-panel">
          <div class="db-kpi-accent" style="background:{meta['color']};"></div>
          <div style="font-size:11px;color:{meta['color']};font-weight:600; letter-spacing:.07em;text-transform:uppercase;">{meta['label']}</div>
          <div class="db-kpi-num" style="color:{meta['color']};">{n}</div>
          <div class="db-kpi-label">of {total} claims</div>
          <div class="db-kpi-bar">
            <div class="db-kpi-bar-fill" style="width:{pct}%;background:{meta['color']};"></div>
          </div>
        </div>
        """
    kpi_html += '</div>'
    st.markdown(kpi_html, unsafe_allow_html=True)

    # ── Unverifiable callout ──────────────────────────────────────────────────
    if counts["could_not_verify"] > 0:
        st.markdown(f"""
        <div class="db-callout">
          <b>ℹ️ {counts['could_not_verify']} claim(s) could not be verified</b> —
          this means ReproHub was unable to run the test (e.g. an unmapped column or
          unsupported test type), not that the finding is incorrect.
          See the Review page for per-claim explanations.
        </div>
        """, unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    st.markdown('<div class="db-section-label">Outcome breakdown</div>', unsafe_allow_html=True)

    col_donut, col_bar = st.columns([1, 1.6], gap="medium")

    with col_donut:
        with st.container():
            st.markdown('<div class="glass-panel db-chart-wrap">', unsafe_allow_html=True)
            fig_donut = _donut_chart(counts, total)
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

    with col_bar:
        with st.container():
            fig_bar = _bar_chart(results)
            if fig_bar:
                st.markdown('<div class="glass-panel db-chart-wrap">', unsafe_allow_html=True)
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="glass-panel db-chart-wrap" style="display:flex;align-items:center;
                     justify-content:center;height:200px;color:#64748B;font-size:13px;">
                  No comparable p-value data available for chart
                </div>
                """, unsafe_allow_html=True)

    # ── Claims table ──────────────────────────────────────────────────────────
    st.markdown('<div class="db-section-label">Claim-level results</div>', unsafe_allow_html=True)

    # Process dataframe for display
    df_raw = pd.DataFrame(results)
    df_display = _format_dataframe(df_raw, claim_lookup)

    # Use st.dataframe with custom column config to fix the bug
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Claim": st.column_config.TextColumn("Claim", width="large"),
            "Test": st.column_config.TextColumn("Test", width="small"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
            "Claimed p": st.column_config.TextColumn("Claimed p", width="small"),
            "Repro. p": st.column_config.TextColumn("Repro. p", width="small"),
            "Δ": st.column_config.TextColumn("Δ", width="small"),
        }
    )

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown('<div class="db-section-label">Export</div>', unsafe_allow_html=True)

    results_df = pd.DataFrame(results)
    csv_bytes = results_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇ Download Results (CSV)",
        data=csv_bytes,
        file_name="reprohub_results.csv",
        mime="text/csv",
    )
