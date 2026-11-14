from pydantic import BaseModel, Field
from typing import Literal

class BugAnalysis(BaseModel):

    error_category: str = Field(
        description="Category of the detected error"
    )

    likely_root_cause: str = Field(
        description="Most likely reason behind the error"
    )

    evidence: list[str] = Field(
        description="Exact log messages supporting the analysis"
    )

    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    suggested_fixes: list[str] = Field(
        description="Actionable steps to investigate or fix the error"
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1"
    )
