"""
Dashboard Page — Results Visualization

Renders a rich, scannable verification dashboard. The page's job:
give a researcher an at-a-glance read of every claim's outcome and
let them drill into the numbers without leaving the page.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ── Status config ─────────────────────────────────────────────────────────────
_STATUS = {
    "reproduced":       {"label": "Reproduced",       "color": "#10B981", "bg": "rgba(16,185,129,0.12)",  "icon": "✓"},
    "marginal":         {"label": "Marginal",          "color": "#F59E0B", "bg": "rgba(245,158,11,0.12)", "icon": "~"},
    "not_reproduced":   {"label": "Not Reproduced",   "color": "#EF4444", "bg": "rgba(239,68,68,0.12)",  "icon": "✗"},
    "could_not_verify": {"label": "Could Not Verify", "color": "#8B95A9", "bg": "rgba(139,149,169,0.12)","icon": "?"},
}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', -apple-system, sans-serif !important;
}
.stApp { background: #0A0F1E; color: #E2E8F0; }

/* ── Page header ── */
.db-header {
    display: flex; align-items: flex-start; gap: 16px;
    margin-bottom: 32px;
    padding-bottom: 28px;
    border-bottom: 1px solid rgba(91,79,232,0.25);
}
.db-header-icon {
    width: 48px; height: 48px; flex-shrink: 0;
    background: linear-gradient(135deg, #5B4FE8, #7C3AED);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
    box-shadow: 0 4px 16px rgba(91,79,232,0.4);
}
.db-header-title { font-size: 24px; font-weight: 700; color: #F1F5F9; margin: 0; line-height: 1.2; }
.db-header-sub   { font-size: 13px; color: #64748B; margin-top: 3px; }

/* ── Score hero ── */
.db-score-hero {
    background: linear-gradient(135deg, rgba(91,79,232,0.15) 0%, rgba(124,58,237,0.08) 100%);
    border: 1px solid rgba(91,79,232,0.3);
    border-radius: 20px;
    padding: 28px 32px;
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 24px;
    position: relative; overflow: hidden;
}
.db-score-hero::before {
    content: '';
    position: absolute; top: -40px; right: -40px;
    width: 160px; height: 160px;
    background: radial-gradient(circle, rgba(91,79,232,0.18) 0%, transparent 70%);
    pointer-events: none;
}
.db-score-number { font-size: 56px; font-weight: 700; line-height: 1; color: #F1F5F9; }
.db-score-pct    { font-size: 28px; font-weight: 300; color: #5B4FE8; }
.db-score-label  { font-size: 11px; font-weight: 600; letter-spacing: .1em;
                   text-transform: uppercase; color: #64748B; margin-top: 6px; }
.db-score-note   { font-size: 12px; color: #94A3B8; max-width: 300px; line-height: 1.5; }

/* ── KPI strip ── */
.db-kpi-strip {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
    margin-bottom: 28px;
}
.db-kpi {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 18px 20px;
    position: relative; overflow: hidden;
    transition: border-color .2s;
}
.db-kpi:hover { border-color: rgba(255,255,255,0.16); }
.db-kpi-accent {
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    border-radius: 14px 14px 0 0;
}
.db-kpi-num   { font-size: 32px; font-weight: 700; line-height: 1; margin-top: 6px; }
.db-kpi-label { font-size: 11px; color: #64748B; margin-top: 5px;
                text-transform: uppercase; letter-spacing: .06em; font-weight: 500; }
.db-kpi-bar   { height: 3px; border-radius: 2px; margin-top: 12px;
                background: rgba(255,255,255,0.06); }
.db-kpi-bar-fill { height: 100%; border-radius: 2px; }

/* ── Section label ── */
.db-section-label {
    font-size: 10px; font-weight: 600; letter-spacing: .12em;
    text-transform: uppercase; color: #475569;
    margin: 28px 0 14px;
    display: flex; align-items: center; gap: 10px;
}
.db-section-label::after {
    content: ''; flex: 1; height: 1px;
    background: rgba(255,255,255,0.06);
}

/* ── Chart container ── */
.db-chart-wrap {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 8px 8px 4px;
    margin-bottom: 28px;
}

/* ── Claims table ── */
.db-table-wrap {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 28px;
}
.db-table-header {
    display: grid;
    grid-template-columns: 2fr 1fr 1.2fr 0.9fr 0.9fr 0.8fr;
    padding: 10px 20px;
    background: rgba(10,15,30,0.8);
    border-bottom: 1px solid rgba(255,255,255,0.07);
    font-size: 10px; font-weight: 600; letter-spacing: .1em;
    text-transform: uppercase; color: #475569;
}
.db-table-row {
    display: grid;
    grid-template-columns: 2fr 1fr 1.2fr 0.9fr 0.9fr 0.8fr;
    padding: 14px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    align-items: center;
    transition: background .15s;
    font-size: 13px;
}
.db-table-row:last-child { border-bottom: none; }
.db-table-row:hover { background: rgba(255,255,255,0.03); }

.db-claim-text {
    color: #CBD5E1; font-size: 12.5px; line-height: 1.4;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    max-width: 95%;
}
.db-test-badge {
    display: inline-block;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10.5px; font-weight: 500;
    color: #94A3B8;
    font-family: 'IBM Plex Mono', monospace;
}
.db-status-chip {
    display: inline-flex; align-items: center; gap: 5px;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 11px; font-weight: 600;
}
.db-pval {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11.5px; color: #94A3B8;
}
.db-delta-pos { color: #10B981; font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; }
.db-delta-neg { color: #EF4444; font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; }
.db-delta-neu { color: #8B95A9; font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; }

/* ── Explanation callout ── */
.db-callout {
    background: rgba(245,158,11,0.07);
    border: 1px solid rgba(245,158,11,0.2);
    border-radius: 12px;
    padding: 14px 18px;
    font-size: 12.5px; color: #FCD34D; line-height: 1.6;
    margin-bottom: 20px;
}
.db-callout b { font-weight: 600; }

/* ── Export row ── */
.db-export-row { display: flex; gap: 12px; align-items: center; margin-top: 4px; }
.db-export-label { font-size: 12px; color: #475569; }

/* Download button */
.db-download .stDownloadButton > button {
    background: transparent !important;
    color: #5B4FE8 !important;
    border: 1.5px solid #5B4FE8 !important;
    border-radius: 10px !important;
    padding: 9px 20px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    transition: all .2s !important;
}
.db-download .stDownloadButton > button:hover {
    background: rgba(91,79,232,0.1) !important;
}

/* ── Empty state ── */
.db-empty {
    text-align: center; padding: 72px 24px;
}
.db-empty-icon  { font-size: 48px; margin-bottom: 16px; }
.db-empty-title { font-size: 18px; font-weight: 600; color: #CBD5E1; margin-bottom: 8px; }
.db-empty-sub   { font-size: 13px; color: #64748B; }

/* ── Plotly override ── */
.js-plotly-plot .plotly { background: transparent !important; }
</style>
"""


def _fmt_p(v) -> str:
    if v is None:
        return "—"
    if v < 0.001:
        return "<.001"
    return f"{v:.4f}"


def _score_color(score: int) -> str:
    if score >= 75:
        return "#10B981"
    if score >= 40:
        return "#F59E0B"
    return "#EF4444"


def _donut_chart(counts: dict, total: int):
    """Render a clean donut chart via Plotly go — no px defaults."""
    present = {k: v for k, v in counts.items() if v > 0}
    labels  = [_STATUS[k]["label"] for k in present]
    values  = list(present.values())
    colors  = [_STATUS[k]["color"] for k in present]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.62,
        marker=dict(
            colors=colors,
            line=dict(color="#0A0F1E", width=3),
        ),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value} claim(s) — %{percent}<extra></extra>",
        direction="clockwise",
        sort=False,
    ))

    # Central annotation
    score_pct = round(counts.get("reproduced", 0) / total * 100) if total else 0
    fig.add_annotation(
        text=f"<b style='font-size:28px'>{total}</b>",
        x=0.5, y=0.55, showarrow=False,
        font=dict(family="IBM Plex Sans", size=28, color="#F1F5F9"),
    )
    fig.add_annotation(
        text="claims",
        x=0.5, y=0.40, showarrow=False,
        font=dict(family="IBM Plex Sans", size=11, color="#64748B"),
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=16, b=16, l=16, r=16),
        height=290,
        showlegend=True,
        legend=dict(
            font=dict(family="IBM Plex Sans", size=12, color="#94A3B8"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            orientation="v",
            x=0.72, y=0.5,
            xanchor="left", yanchor="middle",
        ),
    )
    return fig


def _bar_chart(results: list):
    """Horizontal bar: p-value claimed vs reproduced per claim."""
    rows = [r for r in results
            if r.get("claimed_p_value") is not None
            and r.get("reproduced_p_value") is not None]
    if not rows:
        return None

    ids      = [r.get("claim_id", f"C{i+1}") for i, r in enumerate(rows)]
    claimed  = [r["claimed_p_value"]    for r in rows]
    reproduced = [r["reproduced_p_value"] for r in rows]
    statuses = [r.get("status", "could_not_verify") for r in rows]
    bar_cols = [_STATUS[s]["color"] for s in statuses]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Claimed p",
        y=ids, x=claimed,
        orientation="h",
        marker=dict(color="rgba(91,79,232,0.35)", line=dict(color="#5B4FE8", width=1.5)),
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
        height=max(220, 48 * len(rows)),
        font=dict(family="IBM Plex Sans", color="#94A3B8", size=11),
        legend=dict(
            font=dict(family="IBM Plex Sans", size=11, color="#94A3B8"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            orientation="h", x=0, y=1.06,
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.05)",
            zerolinecolor="rgba(255,255,255,0.1)",
            tickfont=dict(family="IBM Plex Mono", size=10),
            title=dict(text="p-value", font=dict(size=10, color="#475569")),
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(family="IBM Plex Mono", size=10),
        ),
    )
    return fig


def _claims_table_html(results: list, claim_lookup: dict) -> str:
    """Render the claim results as a custom HTML table."""
    rows_html = ""
    for r in results:
        cid        = r.get("claim_id", "—")
        text       = claim_lookup.get(cid, cid)
        if len(text) > 68:
            text = text[:65] + "…"

        status     = r.get("status", "could_not_verify")
        meta       = _STATUS.get(status, _STATUS["could_not_verify"])
        test       = r.get("test_type") or "—"
        claimed_p  = _fmt_p(r.get("claimed_p_value"))
        repro_p    = _fmt_p(r.get("reproduced_p_value"))

        disc = r.get("discrepancy")
        if disc is None:
            delta_html = '<span class="db-delta-neu">—</span>'
        elif disc < 0.001:
            delta_html = f'<span class="db-delta-pos">+{disc:.4f}</span>'
        else:
            delta_html = f'<span class="db-delta-neg">{disc:.4f}</span>'

        rows_html += f"""
        <div class="db-table-row">
          <div class="db-claim-text" title="{text}">{text}</div>
          <div><span class="db-test-badge">{test}</span></div>
          <div>
            <span class="db-status-chip"
                  style="color:{meta['color']};background:{meta['bg']};">
              {meta['icon']}&nbsp;{meta['label']}
            </span>
          </div>
          <div class="db-pval">{claimed_p}</div>
          <div class="db-pval">{repro_p}</div>
          <div>{delta_html}</div>
        </div>
        """

    return f"""
    <div class="db-table-wrap">
      <div class="db-table-header">
        <div>Claim</div>
        <div>Test</div>
        <div>Status</div>
        <div>Claimed p</div>
        <div>Repro. p</div>
        <div>Δ</div>
      </div>
      {rows_html}
    </div>
    """


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
    score   = st.session_state.reproducibility_score
    total   = len(results)
    counts  = {k: sum(1 for r in results if r.get("status") == k) for k in _STATUS}

    claims       = st.session_state.get("confirmed_claims") or st.session_state.get("claims") or []
    claim_lookup = {c.get("id"): c.get("claim_statement") or c.get("id") for c in claims}

    score_c = _score_color(score)

    # ── Score hero ────────────────────────────────────────────────────────────
    repro_rate = round(counts["reproduced"] / total * 100) if total else 0
    st.markdown(f"""
    <div class="db-score-hero">
      <div>
        <div class="db-score-number" style="color:{score_c};">
          {score}<span class="db-score-pct">%</span>
        </div>
        <div class="db-score-label">Reproducibility Score</div>
      </div>
      <div class="db-score-note">
        {counts['reproduced']} of {total} claim{'s' if total != 1 else ''}
        reproduced ({repro_rate}%). {counts['marginal']} marginal,
        {counts['not_reproduced']} failed, {counts['could_not_verify']} unverifiable.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI strip ─────────────────────────────────────────────────────────────
    kpi_html = '<div class="db-kpi-strip">'
    for key, meta in _STATUS.items():
        n    = counts[key]
        pct  = round(n / total * 100) if total else 0
        kpi_html += f"""
        <div class="db-kpi">
          <div class="db-kpi-accent" style="background:{meta['color']};"></div>
          <div style="font-size:10px;color:{meta['color']};font-weight:600;
                      letter-spacing:.07em;text-transform:uppercase;">{meta['label']}</div>
          <div class="db-kpi-num" style="color:{meta['color']};">{n}</div>
          <div class="db-kpi-label">of {total} claims</div>
          <div class="db-kpi-bar">
            <div class="db-kpi-bar-fill"
                 style="width:{pct}%;background:{meta['color']};"></div>
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
        st.markdown('<div class="db-chart-wrap">', unsafe_allow_html=True)
        fig_donut = _donut_chart(counts, total)
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_bar:
        fig_bar = _bar_chart(results)
        if fig_bar:
            st.markdown('<div class="db-chart-wrap">', unsafe_allow_html=True)
            st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="db-chart-wrap" style="display:flex;align-items:center;
                 justify-content:center;height:180px;color:#475569;font-size:13px;">
              No p-value data available for comparison chart
            </div>
            """, unsafe_allow_html=True)

    # ── Claims table ──────────────────────────────────────────────────────────
    st.markdown('<div class="db-section-label">Claim-level results</div>', unsafe_allow_html=True)
    st.markdown(_claims_table_html(results, claim_lookup), unsafe_allow_html=True)

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown('<div class="db-section-label">Export</div>', unsafe_allow_html=True)

    results_df = pd.DataFrame(results)
    csv_bytes  = results_df.to_csv(index=False).encode("utf-8")

    st.markdown('<div class="db-download">', unsafe_allow_html=True)
    st.download_button(
        label="⬇ Download Results (CSV)",
        data=csv_bytes,
        file_name="reprohub_results.csv",
        mime="text/csv",
    )
    st.markdown('</div>', unsafe_allow_html=True)
