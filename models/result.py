"""Result data model."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ReproducibilityStatus(str, Enum):
    """
    The four possible verification outcomes for a claim, per
    README.md's "Understanding Results" table:
        reproduced        composite_score >= 0.80
        marginal          composite_score >= 0.55
        not_reproduced    composite_score < 0.55
        could_not_verify  the test couldn't be run at all
    """
    REPRODUCED = "reproduced"
    MARGINAL = "marginal"
    NOT_REPRODUCED = "not_reproduced"
    COULD_NOT_VERIFY = "could_not_verify"


class Result(BaseModel):
    """
    The outcome of verifying one claim against the dataset.

    claimed_p_value, reproduced_p_value, discrepancy, composite_score,
    score_breakdown, and effect size fields are all Optional: a
    `could_not_verify` result has no test to report on.
    """
    claim_id: str
    test_type: str
    status: ReproducibilityStatus
    claimed_p_value: Optional[float] = None
    reproduced_p_value: Optional[float] = None
    discrepancy: Optional[float] = None
    # Composite scoring (new)
    composite_score: Optional[float] = None
    score_breakdown: Optional[dict] = None
    claimed_effect_size: Optional[float] = None
    reproduced_effect_size: Optional[dict] = None   # {"type": str, "value": float}
    explanation: Optional[str] = None
