"""Visualization utilities."""

import plotly.express as px
import pandas as pd

def create_status_pie_chart(results: list):
    """Create a pie chart of reproducibility status."""
    df = pd.DataFrame(results)
    status_counts = df["status"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    
    return px.pie(
        status_counts,
        values="count",
        names="status",
        title="Reproducibility Status"
    )
