"""Result data model."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ReproducibilityStatus(str, Enum):
    """
    The four possible verification outcomes for a claim, per
    README.md's "Understanding Results" table:
        reproduced        p-value difference < 0.01
        marginal          p-value difference 0.01 - 0.05
        not_reproduced     p-value difference >= 0.05
        could_not_verify   the test couldn't be run at all (missing/
                            invalid columns, no claimed p-value, etc.)
    """
    REPRODUCED = "reproduced"
    MARGINAL = "marginal"
    NOT_REPRODUCED = "not_reproduced"
    COULD_NOT_VERIFY = "could_not_verify"


class Result(BaseModel):
    """
    The outcome of verifying one claim against the dataset.

    claimed_p_value, reproduced_p_value, and discrepancy are all
    Optional: a `could_not_verify` result (core/comparator.py) has no
    test to report on, so none of these have a value to fill in. Every
    other status always carries all three.
    """
    claim_id: str
    test_type: str
    status: ReproducibilityStatus
    claimed_p_value: Optional[float] = None
    reproduced_p_value: Optional[float] = None
    discrepancy: Optional[float] = None
    explanation: Optional[str] = None
