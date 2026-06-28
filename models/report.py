"""Report data model."""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Report(BaseModel):
    title: str
    paper_title: Optional[str] = None
    authors: Optional[str] = None
    generation_date: datetime = datetime.now()
    reproducibility_score: int
    results: List[dict]
    include_summary: bool = True
    include_details: bool = True
