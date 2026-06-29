"""
Dashboard Page — Results Visualization
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from app.config import config

# Consistent colors per status across the whole dashboard, matching the
# four-state classification from core/comparator.py. Using all four
# everywhere (metrics, chart) rather than just two, since marginal and
# could_not_verify are first-class outcomes, not edge cases to omit.
_STATUS_COLORS = {
    "reproduced": "#28a745",
    "marginal": "#f0ad4e",
    "not_reproduced": "#dc3545",
    "could_not_verify": "#6c757d",
}
_STATUS_LABELS = {
    "reproduced": "✅ Reproduced",
    "marginal": "⚠️ Marginal",
    "not_reproduced": "❌ Not Reproduced",
    "could_not_verify": "🔧 Could Not Verify",
}


def render():
    st.title("📊 Verification Dashboard")

    if not st.session_state.analysis_complete:
        st.info("🔬 No analysis results found. Please upload and verify claims first.")
        return

    results = st.session_state.results
    score = st.session_state.reproducibility_score

    st.subheader("📈 Summary")

    total = len(results)
    counts = {
        status: sum(1 for r in results if r.get("status") == status)
        for status in _STATUS_COLORS
    }

    # All four statuses get a metric, not just reproduced/not_reproduced -
    # a claim that's marginal or could_not_verify previously vanished
    # from this summary entirely, with no indication it existed.
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🎯 Score", f"{score}%")
    with col2:
        st.metric(_STATUS_LABELS["reproduced"], counts["reproduced"])
    with col3:
        st.metric(_STATUS_LABELS["marginal"], counts["marginal"])
    with col4:
        st.metric(_STATUS_LABELS["not_reproduced"], counts["not_reproduced"])
    with col5:
        st.metric(_STATUS_LABELS["could_not_verify"], counts["could_not_verify"])

    if counts["could_not_verify"] > 0:
        st.caption(
            f"ℹ️ {counts['could_not_verify']} claim(s) could not be verified - "
            "this means ReproHub couldn't run the test (e.g. an unmapped "
            "column), not that the finding is wrong. See the Review page."
        )

    st.divider()

    results_df = pd.DataFrame(results)
    st.dataframe(results_df, use_container_width=True)

    # Visualization - now includes every status that actually has at
    # least one claim, instead of being hardcoded to exactly two slices.
    # The previous version's percentages didn't sum to the real total
    # whenever a marginal/could_not_verify claim existed, while still
    # rendering as if it were a complete 100% breakdown.
    if results:
        chart_statuses = [s for s in _STATUS_COLORS if counts[s] > 0]
        chart_df = pd.DataFrame({
            "status": [_STATUS_LABELS[s] for s in chart_statuses],
            "count": [counts[s] for s in chart_statuses],
        })
        # color=... + color_discrete_map={...} binds each color to its
        # category NAME, not its position in a list. px.pie's
        # color_discrete_sequence binds by position instead, and Plotly
        # is free to reorder slices internally (e.g. by value) - which
        # silently decouples the intended color from its legend label.
        # Confirmed by rendering: with color_discrete_sequence, the
        # legend read "Could Not Verify" next to a slice that was
        # actually colored for "Reproduced".
        fig = px.pie(
            chart_df,
            values="count",
            names="status",
            title="Reproducibility Status",
            color="status",
            color_discrete_map={_STATUS_LABELS[s]: _STATUS_COLORS[s] for s in chart_statuses},
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("📥 Export Options")

    # st.download_button sends bytes to the USER's browser. The previous
    # version called results_df.to_csv("reprohub_results.csv") inside a
    # plain st.button, which writes to the server's local filesystem -
    # on Streamlit Cloud that file is never visible to the user at all,
    # despite the success message claiming a download happened.
    csv_bytes = results_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📄 Download Results (CSV)",
        data=csv_bytes,
        file_name="reprohub_results.csv",
        mime="text/csv",
    )
