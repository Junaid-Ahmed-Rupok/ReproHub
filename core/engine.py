"""
Statistical Test Engine - runs real statistical tests against the
uploaded dataset using SciPy/statsmodels.

Each test type expects a specific params shape (the columns it needs
from the dataset). Columns must already be resolved to real names in
the uploaded DataFrame - resolving them from a paper's prose ("cognitive
scores" -> "cognitive_score") happens upstream, in core/matcher.py or
the Review page, not here.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from scipy import stats


class EngineError(Exception):
    """Raised when a test can't be run against the supplied data/params."""


class StatisticalTestEngine:
    """Runs real statistical tests against a pandas DataFrame."""

    SUPPORTED_TESTS = {
        "t_test_independent",
        "paired_t_test",
        "one_way_anova",
        "pearson_correlation",
        "spearman_correlation",
        "chi_square",
        "mann_whitney_u",
    }

    def __init__(self, data: Optional[pd.DataFrame]):
        self.data = data

    def run_test(self, test_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a real statistical test.

        Args:
            test_type: one of SUPPORTED_TESTS.
            params: column references the test needs. Shape depends on
                test_type - see the individual _run_* methods.

        Returns:
            A result dict: {test_type, statistic, p_value, effect_size,
            n, assumptions_checked (where applicable)}, or
            {"error": "..."} if the test can't be run (missing/invalid
            columns, insufficient data, unsupported test_type). An error
            dict is returned rather than an exception raised, since a
            single bad claim shouldn't crash a batch of several - see
            core/comparator.py, which calls this per-claim in a loop.
        """
        if self.data is None:
            return {"error": "No dataset loaded."}

        if test_type not in self.SUPPORTED_TESTS:
            return {"error": f"Test {test_type} not implemented"}

        try:
            handler = getattr(self, f"_run_{test_type}")
            return handler(params)
        except EngineError as exc:
            return {"error": str(exc)}
        except Exception as exc:  # noqa: BLE001 - never let one bad claim crash the batch
            return {"error": f"Unexpected error running {test_type}: {exc}"}

    # -- helpers --------------------------------------------------------

    def _require_columns(self, *cols: str) -> None:
        missing = [c for c in cols if c not in self.data.columns]
        if missing:
            raise EngineError(f"Column(s) not found in dataset: {', '.join(missing)}")

    def _numeric_series(self, col: str) -> pd.Series:
        series = pd.to_numeric(self.data[col], errors="coerce").dropna()
        if series.empty:
            raise EngineError(f"Column '{col}' has no usable numeric values.")
        return series

    # -- test implementations --------------------------------------------

    def _run_t_test_independent(self, params: dict) -> dict:
        group_col, value_col = params.get("group_col"), params.get("value_col")
        if not group_col or not value_col:
            raise EngineError("t_test_independent requires 'group_col' and 'value_col'.")
        self._require_columns(group_col, value_col)

        sub = self.data[[group_col, value_col]].dropna()
        groups = sub[group_col].unique()
        if len(groups) != 2:
            raise EngineError(
                f"t_test_independent requires exactly 2 groups in '{group_col}', "
                f"found {len(groups)}: {list(groups)}"
            )

        a = pd.to_numeric(sub[sub[group_col] == groups[0]][value_col], errors="coerce").dropna()
        b = pd.to_numeric(sub[sub[group_col] == groups[1]][value_col], errors="coerce").dropna()
        if len(a) == 0 or len(b) == 0:
            raise EngineError(
                f"Column '{value_col}' does not contain numeric values for one or "
                f"both groups - check that 'value_col' and 'group_col' aren't swapped."
            )
        if len(a) < 2 or len(b) < 2:
            raise EngineError("Each group needs at least 2 observations for a t-test.")

        # Shapiro-Wilk normality check (informational - doesn't block the
        # test, since real papers rarely meet normality perfectly either).
        normal_a = stats.shapiro(a).pvalue > 0.05 if len(a) >= 3 else None
        normal_b = stats.shapiro(b).pvalue > 0.05 if len(b) >= 3 else None
        # Levene's test for equal variances - determines whether to use
        # Welch's correction.
        equal_var = stats.levene(a, b).pvalue > 0.05

        result = stats.ttest_ind(a, b, equal_var=equal_var)
        pooled_std = np.sqrt(((len(a) - 1) * a.std(ddof=1) ** 2 + (len(b) - 1) * b.std(ddof=1) ** 2)
                              / (len(a) + len(b) - 2))
        cohens_d = (a.mean() - b.mean()) / pooled_std if pooled_std > 0 else 0.0

        return {
            "test_type": "t_test_independent",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "cohens_d", "value": float(cohens_d)},
            "n": int(len(a) + len(b)),
            "assumptions_checked": {
                "normality": bool(normal_a) and bool(normal_b) if normal_a is not None and normal_b is not None else None,
                "equal_variance": bool(equal_var),
            },
        }

    def _run_paired_t_test(self, params: dict) -> dict:
        col1, col2 = params.get("col1"), params.get("col2")
        if not col1 or not col2:
            raise EngineError("paired_t_test requires 'col1' and 'col2'.")
        self._require_columns(col1, col2)

        sub = self.data[[col1, col2]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(sub) < 2:
            raise EngineError("paired_t_test requires at least 2 paired observations.")

        result = stats.ttest_rel(sub[col1], sub[col2])
        diffs = sub[col1] - sub[col2]
        cohens_d = diffs.mean() / diffs.std(ddof=1) if diffs.std(ddof=1) > 0 else 0.0

        return {
            "test_type": "paired_t_test",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "cohens_d", "value": float(cohens_d)},
            "n": int(len(sub)),
        }

    def _run_one_way_anova(self, params: dict) -> dict:
        group_col, value_col = params.get("group_col"), params.get("value_col")
        if not group_col or not value_col:
            raise EngineError("one_way_anova requires 'group_col' and 'value_col'.")
        self._require_columns(group_col, value_col)

        sub = self.data[[group_col, value_col]].dropna()
        sub[value_col] = pd.to_numeric(sub[value_col], errors="coerce")
        sub = sub.dropna()
        groups = [g[value_col].values for _, g in sub.groupby(group_col) if len(g) >= 2]
        if len(groups) < 2:
            raise EngineError(f"one_way_anova requires at least 2 groups with 2+ observations each.")

        result = stats.f_oneway(*groups)

        # Eta-squared effect size: SS_between / SS_total.
        grand_mean = sub[value_col].mean()
        ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
        ss_total = ((sub[value_col] - grand_mean) ** 2).sum()
        eta_sq = ss_between / ss_total if ss_total > 0 else 0.0

        return {
            "test_type": "one_way_anova",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "eta_squared", "value": float(eta_sq)},
            "n": int(sum(len(g) for g in groups)),
        }

    def _run_pearson_correlation(self, params: dict) -> dict:
        col1, col2 = params.get("col1"), params.get("col2")
        if not col1 or not col2:
            raise EngineError("pearson_correlation requires 'col1' and 'col2'.")
        self._require_columns(col1, col2)

        sub = self.data[[col1, col2]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(sub) < 3:
            raise EngineError("pearson_correlation requires at least 3 paired observations.")

        result = stats.pearsonr(sub[col1], sub[col2])

        return {
            "test_type": "pearson_correlation",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "r", "value": float(result.statistic)},
            "n": int(len(sub)),
        }

    def _run_spearman_correlation(self, params: dict) -> dict:
        col1, col2 = params.get("col1"), params.get("col2")
        if not col1 or not col2:
            raise EngineError("spearman_correlation requires 'col1' and 'col2'.")
        self._require_columns(col1, col2)

        sub = self.data[[col1, col2]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(sub) < 3:
            raise EngineError("spearman_correlation requires at least 3 paired observations.")

        result = stats.spearmanr(sub[col1], sub[col2])

        return {
            "test_type": "spearman_correlation",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "rho", "value": float(result.statistic)},
            "n": int(len(sub)),
        }

    def _run_chi_square(self, params: dict) -> dict:
        col1, col2 = params.get("col1"), params.get("col2")
        if not col1 or not col2:
            raise EngineError("chi_square requires 'col1' and 'col2'.")
        self._require_columns(col1, col2)

        sub = self.data[[col1, col2]].dropna()
        if len(sub) < 1:
            raise EngineError("chi_square requires at least 1 observation.")

        contingency = pd.crosstab(sub[col1], sub[col2])
        if contingency.shape[0] < 2 or contingency.shape[1] < 2:
            raise EngineError(
                f"chi_square requires at least 2 categories in each of '{col1}' and '{col2}'."
            )

        chi2, p, dof, expected = stats.chi2_contingency(contingency)

        # Cramer's V effect size.
        n = contingency.values.sum()
        min_dim = min(contingency.shape) - 1
        cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 and n > 0 else 0.0

        return {
            "test_type": "chi_square",
            "statistic": float(chi2),
            "p_value": float(p),
            "effect_size": {"type": "cramers_v", "value": float(cramers_v)},
            "n": int(n),
            "degrees_of_freedom": int(dof),
        }

    def _run_mann_whitney_u(self, params: dict) -> dict:
        group_col, value_col = params.get("group_col"), params.get("value_col")
        if not group_col or not value_col:
            raise EngineError("mann_whitney_u requires 'group_col' and 'value_col'.")
        self._require_columns(group_col, value_col)

        sub = self.data[[group_col, value_col]].dropna()
        groups = sub[group_col].unique()
        if len(groups) != 2:
            raise EngineError(
                f"mann_whitney_u requires exactly 2 groups in '{group_col}', found {len(groups)}."
            )

        a = pd.to_numeric(sub[sub[group_col] == groups[0]][value_col], errors="coerce").dropna()
        b = pd.to_numeric(sub[sub[group_col] == groups[1]][value_col], errors="coerce").dropna()
        if len(a) == 0 or len(b) == 0:
            raise EngineError(
                f"Column '{value_col}' does not contain numeric values for one or "
                f"both groups - check that 'value_col' and 'group_col' aren't swapped."
            )
        if len(a) < 1 or len(b) < 1:
            raise EngineError("Each group needs at least 1 observation for Mann-Whitney U.")

        result = stats.mannwhitneyu(a, b, alternative="two-sided")

        return {
            "test_type": "mann_whitney_u",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": None,
            "n": int(len(a) + len(b)),
        }
