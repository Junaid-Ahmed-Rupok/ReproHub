"""
Report Page — Real PDF Report Generation

Builds an actual PDF from the real verification results (core.comparator's
output, stored in st.session_state.results) using ReportLab. The PDF includes
an executive summary and/or a detailed per-claim results table, depending on
which sections the user selects.
"""

import io
from datetime import datetime

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

from app.config import config

# ── Status config ────────────────────────────────────────────────────────────
STATUS_META = {
    "reproduced":       {"label": "Reproduced",       "symbol": "✓", "hex": "#10B981"},
    "marginal":         {"label": "Marginal",          "symbol": "~", "hex": "#F59E0B"},
    "not_reproduced":   {"label": "Not Reproduced",   "symbol": "✗", "hex": "#EF4444"},
    "could_not_verify": {"label": "Could Not Verify", "symbol": "?", "hex": "#8B95A9"},
}

STATUS_LABELS = {k: v["label"] for k, v in STATUS_META.items()}

# ── PDF palette ───────────────────────────────────────────────────────────────
C_INK         = colors.HexColor("#0D1117")
C_SURFACE     = colors.HexColor("#FFFFFF")
C_RULE        = colors.HexColor("#E2E8F0")
C_MUTED       = colors.HexColor("#8B95A9")
C_ACCENT      = colors.HexColor("#5B4FE8")
C_HEADER_BG   = colors.HexColor("#0A0F1E")
C_ALT_ROW     = colors.HexColor("#F8FAFC")
C_REPRODUCED  = colors.HexColor("#10B981")
C_MARGINAL    = colors.HexColor("#F59E0B")
C_NOT_REPRO   = colors.HexColor("#EF4444")
C_UNVERIFIED  = colors.HexColor("#8B95A9")

STATUS_COLORS = {
    "reproduced":       C_REPRODUCED,
    "marginal":         C_MARGINAL,
    "not_reproduced":   C_NOT_REPRO,
    "could_not_verify": C_UNVERIFIED,
}


def _format_p(value) -> str:
    if value is None:
        return "—"
    if value < 0.001:
        return "<.001"
    return f"{value:.4f}"


def _score_color(score: int):
    if score >= 75:
        return C_REPRODUCED
    if score >= 40:
        return C_MARGINAL
    return C_NOT_REPRO


def _build_pdf(
    results: list,
    score: int,
    claim_lookup: dict,
    include_summary: bool,
    include_details: bool,
) -> bytes:
    """Render the verification results into a production-quality PDF."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.65 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # ── Custom style sheet ────────────────────────────────────────────────────
    def s(name, **kw):
        base = kw.pop("parent", styles["Normal"])
        return ParagraphStyle(name, parent=base, **kw)

    sty = {
        "cover_brand": s("CoverBrand",
            fontName="Helvetica-Bold", fontSize=9, textColor=C_ACCENT,
            spaceAfter=6, tracking=2),
        "cover_title": s("CoverTitle",
            fontName="Helvetica-Bold", fontSize=26, textColor=C_INK,
            leading=30, spaceAfter=4),
        "cover_sub":   s("CoverSub",
            fontName="Helvetica", fontSize=10, textColor=C_MUTED,
            spaceAfter=24),
        "section":     s("Section",
            fontName="Helvetica-Bold", fontSize=13, textColor=C_INK,
            spaceBefore=18, spaceAfter=6),
        "body":        s("Body",
            fontName="Helvetica", fontSize=9, textColor=C_INK,
            leading=14, spaceAfter=6),
        "note_label":  s("NoteLabel",
            fontName="Helvetica-Bold", fontSize=8.5, textColor=C_INK,
            leading=13),
        "note_body":   s("NoteBody",
            fontName="Helvetica", fontSize=8.5, textColor=colors.HexColor("#475569"),
            leading=13, spaceAfter=6),
        "score_big":   s("ScoreBig",
            fontName="Helvetica-Bold", fontSize=36, textColor=_score_color(score),
            alignment=TA_CENTER, spaceAfter=2),
        "score_label": s("ScoreLabel",
            fontName="Helvetica", fontSize=8, textColor=C_MUTED,
            alignment=TA_CENTER, spaceAfter=14),
        "stat_num":    s("StatNum",
            fontName="Helvetica-Bold", fontSize=18, textColor=C_INK,
            alignment=TA_CENTER, spaceAfter=0),
        "stat_lbl":    s("StatLbl",
            fontName="Helvetica", fontSize=7.5, textColor=C_MUTED,
            alignment=TA_CENTER, spaceAfter=0),
        "footer":      s("Footer",
            fontName="Helvetica", fontSize=7.5, textColor=C_MUTED,
            alignment=TA_CENTER),
    }

    total  = len(results)
    counts = {k: sum(1 for r in results if r.get("status") == k) for k in STATUS_META}

    def rule(color=C_RULE, thickness=0.5, space=8):
        return HRFlowable(
            width="100%", thickness=thickness, color=color,
            spaceAfter=space, spaceBefore=space,
        )

    elements = []

    # ── Cover block ───────────────────────────────────────────────────────────
    elements.append(Paragraph("REPROHUB", sty["cover_brand"]))
    elements.append(Paragraph("Verification Report", sty["cover_title"]))
    elements.append(Paragraph(
        f"Generated {datetime.now().strftime('%B %d, %Y at %H:%M')} &nbsp;·&nbsp; "
        f"{config.APP_NAME} v{config.APP_VERSION}",
        sty["cover_sub"],
    ))
    elements.append(rule(C_ACCENT, thickness=2, space=20))

    # ── Executive Summary ─────────────────────────────────────────────────────
    if include_summary:
        elements.append(Paragraph("Executive Summary", sty["section"]))

        # Score + stat grid as a table for precise layout
        stat_rows = [[
            Paragraph(f"{score}%", sty["score_big"]),
            Paragraph(str(counts["reproduced"]),       sty["stat_num"]),
            Paragraph(str(counts["marginal"]),          sty["stat_num"]),
            Paragraph(str(counts["not_reproduced"]),   sty["stat_num"]),
            Paragraph(str(counts["could_not_verify"]), sty["stat_num"]),
        ],[
            Paragraph("Reproducibility Score", sty["score_label"]),
            Paragraph("Reproduced",      sty["stat_lbl"]),
            Paragraph("Marginal",         sty["stat_lbl"]),
            Paragraph("Not Reproduced",  sty["stat_lbl"]),
            Paragraph("Could Not Verify", sty["stat_lbl"]),
        ]]
        stat_col_w = [1.7*inch, 1.2*inch, 1.1*inch, 1.3*inch, 1.3*inch]
        stat_table = Table(stat_rows, colWidths=stat_col_w)
        stat_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BACKGROUND",  (0, 0), (0,  1),  colors.HexColor("#EEF2FF")),
            ("LINEAFTER",   (0, 0), (0,  1),  0.75, C_RULE),
            ("TOPPADDING",  (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING",(0,0),(-1, -1),  10),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",(0, 0), (-1, -1), 12),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("ROUNDEDCORNERS", [4]),
            ("BOX",         (0, 0), (-1, -1), 0.5, C_RULE),
        ]))
        elements.append(stat_table)
        elements.append(Spacer(1, 10))

        elements.append(Paragraph(
            f"Of <b>{total}</b> statistical claim(s) examined, ReproHub successfully "
            f"reproduced <b>{counts['reproduced']}</b> "
            f"({round(counts['reproduced']/total*100) if total else 0}%), "
            f"found <b>{counts['marginal']}</b> marginal results within tolerance, "
            f"could not reproduce <b>{counts['not_reproduced']}</b>, and was unable "
            f"to verify <b>{counts['could_not_verify']}</b> due to insufficient data.",
            sty["body"],
        ))
        elements.append(rule())

    # ── Detailed Results ──────────────────────────────────────────────────────
    if include_details:
        elements.append(Paragraph("Detailed Results", sty["section"]))
        elements.append(Spacer(1, 4))

        col_w = [2.15*inch, 0.95*inch, 1.05*inch, 0.8*inch, 0.9*inch, 0.65*inch]
        header = ["Claim", "Test", "Status", "Claimed p", "Repro. p", "Δ"]
        table_data = [header]
        status_per_row = []

        for r in results:
            cid        = r.get("claim_id", "—")
            claim_text = claim_lookup.get(cid, cid)
            if len(claim_text) > 55:
                claim_text = claim_text[:52] + "…"
            status     = r.get("status", "")
            label      = STATUS_META.get(status, {}).get("label", status)
            table_data.append([
                claim_text,
                r.get("test_type", "—"),
                label,
                _format_p(r.get("claimed_p_value")),
                _format_p(r.get("reproduced_p_value")),
                _format_p(r.get("discrepancy")),
            ])
            status_per_row.append(status)

        # Base table style
        ts = TableStyle([
            # Header
            ("BACKGROUND",   (0, 0), (-1, 0), C_HEADER_BG),
            ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0), 7.5),
            ("TOPPADDING",   (0, 0), (-1, 0), 7),
            ("BOTTOMPADDING",(0, 0), (-1, 0), 7),
            # Body
            ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",     (0, 1), (-1, -1), 8),
            ("TOPPADDING",   (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 1), (-1, -1), 5),
            ("LEFTPADDING",  (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("ALIGN",        (1, 0), (-1, -1), "CENTER"),
            ("ALIGN",        (0, 0), (0, -1),  "LEFT"),
            ("GRID",         (0, 0), (-1, -1), 0.4, C_RULE),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_SURFACE, C_ALT_ROW]),
        ])

        # Per-row status colour on the Status column (col 2)
        for i, status in enumerate(status_per_row, start=1):
            c = STATUS_COLORS.get(status, C_MUTED)
            ts.add("TEXTCOLOR", (2, i), (2, i), c)
            ts.add("FONTNAME",  (2, i), (2, i), "Helvetica-Bold")

        table = Table(table_data, repeatRows=1, colWidths=col_w)
        table.setStyle(ts)
        elements.append(table)

        # Notes section (for could_not_verify explanations)
        notes = [r for r in results if r.get("explanation")]
        if notes:
            elements.append(Spacer(1, 14))
            elements.append(rule())
            elements.append(Paragraph("Verification Notes", sty["section"]))
            for r in notes:
                cid    = r.get("claim_id", "—")
                ttype  = r.get("test_type", "")
                expl   = r.get("explanation", "")
                elements.append(KeepTogether([
                    Paragraph(f"{cid} &nbsp;·&nbsp; {ttype}", sty["note_label"]),
                    Paragraph(expl, sty["note_body"]),
                ]))

    # ── Footer ────────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 20))
    elements.append(rule(C_RULE, space=6))
    elements.append(Paragraph(
        f"Confidential · {config.APP_NAME} v{config.APP_VERSION} · "
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        sty["footer"],
    ))

    doc.build(elements)
    return buffer.getvalue()


# ── Streamlit UI ──────────────────────────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

/* ── Global reset & base ── */
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.stApp {
    background: #0A0F1E;
    color: #E2E8F0;
}

/* ── Page header ── */
.rh-page-header {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 32px;
    padding-bottom: 28px;
    border-bottom: 1px solid rgba(91,79,232,0.25);
}
.rh-page-icon {
    width: 48px; height: 48px;
    background: linear-gradient(135deg, #5B4FE8 0%, #7C3AED 100%);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px; flex-shrink: 0;
    box-shadow: 0 4px 16px rgba(91,79,232,0.4);
}
.rh-page-title { font-size: 24px; font-weight: 700; color: #F1F5F9; margin: 0; line-height: 1.2; }
.rh-page-sub   { font-size: 13px; color: #64748B; margin-top: 3px; }

/* ── Score ring ── */
.rh-score-ring-wrap {
    display: flex; flex-direction: column; align-items: center;
    padding: 28px 0 20px;
}
.rh-ring-svg { filter: drop-shadow(0 0 14px rgba(91,79,232,0.35)); }
.rh-score-val  { font-size: 38px; font-weight: 700; color: #F1F5F9; margin-top: 12px; line-height: 1; }
.rh-score-label{ font-size: 11px; font-weight: 500; letter-spacing: .08em;
                  text-transform: uppercase; color: #64748B; margin-top: 4px; }

/* ── Stat pills ── */
.rh-stats-grid {
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;
    padding: 0 4px 20px;
}
.rh-stat-pill {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 12px 10px;
    text-align: center;
}
.rh-stat-pill .num { font-size: 22px; font-weight: 700; line-height: 1; }
.rh-stat-pill .lbl { font-size: 10px; color: #64748B; margin-top: 3px;
                      text-transform: uppercase; letter-spacing: .05em; font-weight: 500; }

/* ── Config panel ── */
.rh-config-panel {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 24px;
    height: 100%;
}
.rh-config-title {
    font-size: 11px; font-weight: 600; letter-spacing: .1em;
    text-transform: uppercase; color: #64748B; margin-bottom: 20px;
}

/* ── Toggle options ── */
.rh-option {
    display: flex; align-items: flex-start; gap: 12px;
    padding: 14px 16px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    margin-bottom: 10px;
    transition: border-color .2s;
}
.rh-option:hover { border-color: rgba(91,79,232,0.4); }
.rh-option-icon { font-size: 18px; flex-shrink: 0; margin-top: 1px; }
.rh-option-text .ot { font-size: 13px; font-weight: 600; color: #E2E8F0; }
.rh-option-text .os { font-size: 11px; color: #64748B; margin-top: 2px; }

/* ── Streamlit checkbox override ── */
[data-testid="stCheckbox"] { margin: 0 !important; }
[data-testid="stCheckbox"] label { cursor: pointer !important; }

/* ── Generate button ── */
.rh-generate-btn .stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #5B4FE8 0%, #7C3AED 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 24px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    letter-spacing: .01em !important;
    box-shadow: 0 4px 20px rgba(91,79,232,0.4) !important;
    transition: all .2s ease !important;
    margin-top: 12px !important;
}
.rh-generate-btn .stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 28px rgba(91,79,232,0.55) !important;
}
.rh-generate-btn .stButton > button:active { transform: translateY(0) !important; }

/* ── Download button ── */
.rh-download .stDownloadButton > button {
    width: 100%;
    background: transparent !important;
    color: #5B4FE8 !important;
    border: 1.5px solid #5B4FE8 !important;
    border-radius: 12px !important;
    padding: 12px 24px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    transition: all .2s ease !important;
    margin-top: 8px !important;
}
.rh-download .stDownloadButton > button:hover {
    background: rgba(91,79,232,0.1) !important;
    border-color: #7C6FF0 !important;
}

/* ── Success banner ── */
.rh-success {
    display: flex; align-items: center; gap: 10px;
    background: rgba(16,185,129,0.1);
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 12px;
    padding: 14px 16px;
    margin-top: 14px;
    font-size: 13px; color: #6EE7B7; font-weight: 500;
}

/* ── Warning banner ── */
.rh-warning {
    background: rgba(245,158,11,0.08);
    border: 1px solid rgba(245,158,11,0.25);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 13px; color: #FCD34D;
}

/* ── Empty state ── */
.rh-empty {
    text-align: center; padding: 60px 24px;
}
.rh-empty-icon { font-size: 48px; margin-bottom: 16px; }
.rh-empty-title { font-size: 18px; font-weight: 600; color: #CBD5E1; margin-bottom: 8px; }
.rh-empty-sub   { font-size: 13px; color: #64748B; }

/* ── Status legend ── */
.rh-legend {
    display: flex; flex-wrap: wrap; gap: 8px;
    padding: 16px;
    background: rgba(255,255,255,0.02);
    border-radius: 10px;
    margin-top: 8px;
}
.rh-legend-item {
    display: flex; align-items: center; gap: 6px;
    font-size: 11px; color: #94A3B8;
}
.rh-legend-dot {
    width: 8px; height: 8px; border-radius: 50%;
}

/* ── Divider ── */
.rh-divider {
    height: 1px;
    background: rgba(255,255,255,0.06);
    margin: 24px 0;
}

/* ── Spinner override ── */
.stSpinner { color: #5B4FE8 !important; }
</style>
"""


def _score_ring_svg(score: int) -> str:
    """Generate an SVG score ring. Score 0-100."""
    r = 54
    cx = cy = 68
    circ = 2 * 3.14159 * r
    dash = circ * score / 100

    if score >= 75:
        arc_color = "#10B981"
    elif score >= 40:
        arc_color = "#F59E0B"
    else:
        arc_color = "#EF4444"

    return f"""
<svg class="rh-ring-svg" width="136" height="136" viewBox="0 0 136 136"
     xmlns="http://www.w3.org/2000/svg">
  <style>
    .arc-progress {{
      stroke-dasharray: {circ:.2f};
      stroke-dashoffset: {circ:.2f};
      animation: draw-arc 1.1s cubic-bezier(.4,0,.2,1) forwards;
    }}
    @keyframes draw-arc {{
      to {{ stroke-dashoffset: {circ - dash:.2f}; }}
    }}
  </style>
  <!-- Track -->
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
          stroke="rgba(255,255,255,0.07)" stroke-width="10"/>
  <!-- Progress -->
  <circle class="arc-progress" cx="{cx}" cy="{cy}" r="{r}" fill="none"
          stroke="{arc_color}" stroke-width="10" stroke-linecap="round"
          transform="rotate(-90 {cx} {cy})"/>
  <!-- Glow -->
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
          stroke="{arc_color}" stroke-width="3" opacity="0.18"
          stroke-dasharray="{circ:.2f}"
          stroke-dashoffset="{circ - dash:.2f}"
          transform="rotate(-90 {cx} {cy})"/>
</svg>
"""


def render():
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="rh-page-header">
      <div class="rh-page-icon">📄</div>
      <div>
        <div class="rh-page-title">Generate Report</div>
        <div class="rh-page-sub">Export a professional PDF summarising your verification results</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Guard: no results yet ─────────────────────────────────────────────────
    if not st.session_state.get("analysis_complete"):
        st.markdown("""
        <div class="rh-empty">
          <div class="rh-empty-icon">🔬</div>
          <div class="rh-empty-title">No analysis results yet</div>
          <div class="rh-empty-sub">Upload a paper and verify its claims first,<br>then return here to generate your report.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    results = st.session_state.results
    score   = st.session_state.reproducibility_score
    total   = len(results)

    claims       = st.session_state.get("confirmed_claims") or st.session_state.get("claims") or []
    claim_lookup = {c.get("id"): c.get("claim_statement") or c.get("id") for c in claims}

    counts = {k: sum(1 for r in results if r.get("status") == k) for k in STATUS_META}

    # ── Two-column layout ─────────────────────────────────────────────────────
    col_config, col_preview = st.columns([1.05, 0.95], gap="large")

    # ── LEFT — Configuration ──────────────────────────────────────────────────
    with col_config:
        st.markdown('<div class="rh-config-panel">', unsafe_allow_html=True)
        st.markdown('<div class="rh-config-title">Report Sections</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="rh-option">
          <div class="rh-option-icon">📋</div>
          <div class="rh-option-text">
            <div class="ot">Executive Summary</div>
            <div class="os">Score overview and per-status breakdown</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        include_summary = st.checkbox("Include executive summary", value=True, key="cb_summary",
                                      label_visibility="collapsed")

        st.markdown("""
        <div class="rh-option">
          <div class="rh-option-icon">📊</div>
          <div class="rh-option-text">
            <div class="ot">Detailed Results</div>
            <div class="os">Per-claim table with p-values and discrepancy</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        include_details = st.checkbox("Include detailed results", value=True, key="cb_details",
                                      label_visibility="collapsed")

        st.markdown('<div class="rh-divider"></div>', unsafe_allow_html=True)

        # Status legend
        legend_html = '<div class="rh-legend">'
        for key, meta in STATUS_META.items():
            legend_html += (
                f'<div class="rh-legend-item">'
                f'<div class="rh-legend-dot" style="background:{meta["hex"]}"></div>'
                f'{meta["label"]}: <b style="color:#CBD5E1">{counts[key]}</b>'
                f'</div>'
            )
        legend_html += '</div>'
        st.markdown(legend_html, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # close config panel

    # ── RIGHT — Score preview ─────────────────────────────────────────────────
    with col_preview:
        ring_svg = _score_ring_svg(score)
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
                    border-radius:16px;overflow:hidden;">
          <div class="rh-score-ring-wrap">
            {ring_svg}
            <div class="rh-score-val">{score}%</div>
            <div class="rh-score-label">Reproducibility Score</div>
          </div>
          <div class="rh-stats-grid" style="padding:0 20px 20px;">
            <div class="rh-stat-pill">
              <div class="num" style="color:#10B981">{counts['reproduced']}</div>
              <div class="lbl">Reproduced</div>
            </div>
            <div class="rh-stat-pill">
              <div class="num" style="color:#F59E0B">{counts['marginal']}</div>
              <div class="lbl">Marginal</div>
            </div>
            <div class="rh-stat-pill">
              <div class="num" style="color:#EF4444">{counts['not_reproduced']}</div>
              <div class="lbl">Not Reproduced</div>
            </div>
            <div class="rh-stat-pill">
              <div class="num" style="color:#8B95A9">{counts['could_not_verify']}</div>
              <div class="lbl">Unverifiable</div>
            </div>
          </div>
          <div style="padding:0 20px 20px;font-size:11px;color:#475569;text-align:center;">
            {total} claim{"s" if total != 1 else ""} examined &nbsp;·&nbsp;
            {datetime.now().strftime('%Y-%m-%d %H:%M')}
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Generate + Download ───────────────────────────────────────────────────
    st.markdown('<div class="rh-divider"></div>', unsafe_allow_html=True)

    if not include_summary and not include_details:
        st.markdown(
            '<div class="rh-warning">⚠️ Select at least one section to include in the report.</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown('<div class="rh-generate-btn">', unsafe_allow_html=True)
    generate = st.button("Generate PDF Report", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if generate:
        with st.spinner("Building your report…"):
            try:
                pdf_bytes = _build_pdf(
                    results, score, claim_lookup,
                    include_summary, include_details,
                )
            except Exception as exc:
                st.error(f"Report generation failed: {exc}")
                if config.DEBUG:
                    st.exception(exc)
                return

        st.session_state.report_generated = True
        st.session_state.report_data      = pdf_bytes

        st.markdown(
            '<div class="rh-success">✅ &nbsp; Report generated — ready to download.</div>',
            unsafe_allow_html=True,
        )

    if st.session_state.get("report_generated") and st.session_state.get("report_data"):
        fname = f"reprohub_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        st.markdown('<div class="rh-download">', unsafe_allow_html=True)
        st.download_button(
            label="⬇ Download PDF",
            data=st.session_state.report_data,
            file_name=fname,
            mime="application/pdf",
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
