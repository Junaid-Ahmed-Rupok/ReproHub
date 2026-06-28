"""Claim data model."""

from pydantic import BaseModel
from typing import Optional, Dict, Any

class Claim(BaseModel):
    id: str
    test_type: str
    claimed_p_value: float
    claimed_effect_size: Optional[float] = None
    params: Dict[str, Any]
    claim_statement: Optional[str] = None
    source: str = "manual"
    extraction_confidence: str = "unknown"
