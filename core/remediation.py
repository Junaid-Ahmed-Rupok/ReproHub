"""
Remediation Guidance - Provides actionable advice for failed claims.

Per the project's design: a claim's outcome falls into one of two
fundamentally different categories, and conflating them is misleading:

- App-side (status == "could_not_verify"): ReproHub itself couldn't run
  the test - a column wasn't mapped, the test type is unsupported, the
  data couldn't support it. This is something the USER can fix and
  re-run; it says nothing about whether the paper's finding holds up.
- Paper-side (status in reproduced/marginal/not_reproduced): the claim
  was identified and the test WAS run successfully. The result itself -
  whether it matches, is borderline, or diverges - is the finding. There
  is no in-app action that "fixes" this; it's information to interpret.

generate_remediation() keeps these visually distinguishable (different
icons/headers) so a user never mistakes "please fix a column mapping"
for "this finding is questionable", and vice versa.
"""

from typing import Optional


def generate_remediation(result: dict) -> str:
    """
    Generate remediation guidance for a single claim result (the dict
    shape returned by core.comparator.ComparisonEngine.run_test).

    Builds on the `explanation` and `score_breakdown` fields comparator.py
    already computes rather than restating generic boilerplate, so the
    guidance reflects what actually happened with THIS claim.
    """
    status = result.get("status", "unknown")

    if status == "reproduced":
        return _remediation_reproduced(result)
    if status == "marginal":
        return _remediation_marginal(result)
    if status == "not_reproduced":
        return _remediation_not_reproduced(result)
    if status == "could_not_verify":
        return _remediation_could_not_verify(result)

    return (
        "⚠️ **Unrecognized status.** This claim's result could not be "
        "classified into a known outcome category - this likely indicates "
        "a bug upstream rather than anything about the claim itself."
    )


# -- Paper-side: the test ran; the result itself is the finding ------------

def _remediation_reproduced(result: dict) -> str:
    score = result.get("composite_score")
    score_str = f" (composite score: {score:.2f})" if score is not None else ""
    return (
        f"✅ **Reproduced — paper-side finding.**{score_str}\n\n"
        "The claimed result matches what running the same test against the "
        "dataset actually produces. No action is needed in ReproHub; this "
        "is the verification outcome itself, not something to fix."
    )


def _remediation_marginal(result: dict) -> str:
    explanation = result.get("explanation", "")
    breakdown = result.get("score_breakdown") or {}
    return (
        "⚠️ **Marginally reproduced — paper-side finding.**\n\n"
        "The result is close to the claimed value but not a clean match - "
        "this is information about the original study's reproducibility, "
        "not something to fix in ReproHub. Common causes worth noting in "
        "a citation or discussion: borderline crossing of the 0.05 "
        "significance threshold, a moderate effect-size discrepancy, or a "
        "small sample size making the result sensitive to noise.\n\n"
        f"Score breakdown: {_format_breakdown(breakdown)}\n\n"
        f"Detail: {explanation}" if explanation else
        "⚠️ **Marginally reproduced — paper-side finding.** The result is "
        "close to the claimed value but not a clean match."
    )


def _remediation_not_reproduced(result: dict) -> str:
    explanation = result.get("explanation", "")
    breakdown = result.get("score_breakdown") or {}
    worst_driver = _primary_failure_driver(breakdown)
    driver_note = f" The primary driver of the mismatch was **{worst_driver}** agreement.\n\n" if worst_driver else "\n\n"

    return (
        "❌ **Not reproduced — paper-side finding.**\n\n"
        "The claim was clearly identified and the test ran successfully, "
        "but the result diverges from what was claimed. This is not "
        "something to fix in ReproHub - it IS the finding, and the most "
        "useful next step is understanding *why* the result differs:"
        f"{driver_note}"
        "- Check whether the dataset's assumption checks (normality, equal "
        "variance, sample size) flagged a violation that would call the "
        "original test choice into question.\n"
        "- Check for outliers or a sample-size mismatch between the paper "
        "and the uploaded dataset.\n"
        "- Consider whether a non-parametric alternative would have been "
        "more appropriate for this data.\n\n"
        f"Detail: {explanation}" if explanation else ""
    )


# -- App-side: ReproHub couldn't run the test; the user can act on this ----

def _remediation_could_not_verify(result: dict) -> str:
    reason = result.get("explanation") or "No specific reason was recorded."
    return (
        "🔧 **Could not verify — app-side, you can fix this.**\n\n"
        "ReproHub was not able to run this claim's test against the "
        "dataset. This says nothing about whether the paper's finding is "
        "correct - it means a step before verification needs attention. "
        f"Specific reason: {reason}\n\n"
        "Go to the Review page and check that every required column for "
        "this claim's test type is mapped to a real dataset column, then "
        "re-run verification."
    )


# -- helpers -----------------------------------------------------------------

def _format_breakdown(breakdown: dict) -> str:
    if not breakdown:
        return "not available"
    parts = []
    if breakdown.get("p_component") is not None:
        parts.append(f"p-value agreement {breakdown['p_component']:.2f}")
    if breakdown.get("effect_component") is not None:
        parts.append(f"effect-size agreement {breakdown['effect_component']:.2f}")
    if breakdown.get("stat_component") is not None:
        parts.append(f"statistic agreement {breakdown['stat_component']:.2f}")
    return ", ".join(parts) if parts else "not available"


def _primary_failure_driver(breakdown: dict) -> Optional[str]:
    if not breakdown:
        return None
    candidates = {
        "p-value": breakdown.get("p_component"),
        "effect size": breakdown.get("effect_component"),
        "statistic": breakdown.get("stat_component"),
    }
    candidates = {k: v for k, v in candidates.items() if v is not None}
    if not candidates:
        return None
    return min(candidates, key=candidates.get)
