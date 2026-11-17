from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class KeyClaim(BaseModel):
    claim: str
    source_url: str = ""


class CompanyProfile(BaseModel):
    name: str
    industry: str = ""
    products_services: list[str] = Field(default_factory=list)
    target_customers: str = ""
    pricing_signals: str = ""
    key_claims: list[KeyClaim] = Field(default_factory=list)


class ComparisonMatrix(BaseModel):
    dimensions: list[str] = Field(default_factory=list)
    # rows: {dimension: {company: "value"}}
    rows: dict[str, dict[str, str]] = Field(default_factory=dict)


class AnalysisResult(BaseModel):
    comparison: ComparisonMatrix = Field(default_factory=ComparisonMatrix)
    positioning: dict[str, str] = Field(default_factory=dict)
    strengths: dict[str, list[str]] = Field(default_factory=dict)
    weaknesses: dict[str, list[str]] = Field(default_factory=dict)
    opportunities: list[str] = Field(default_factory=list)


class ClaimCheck(BaseModel):
    claim: str
    status: Literal["supported", "unsupported", "conflicting"]
    supporting_sources: list[str] = Field(default_factory=list)
    note: str = ""


class FactCheckResult(BaseModel):
    checks: list[ClaimCheck] = Field(default_factory=list)
    support_ratio: float = 0.0


class ResearchState(TypedDict, total=False):
    company: str
    competitors: list[str]
    industry: str
    research_type: str
    retried: bool
    raw_sources: list[dict[str, Any]]
    extracted: dict[str, dict[str, Any]]
    analysis: dict[str, Any]
    factcheck: dict[str, Any]
    final_report: str
    sources: list[str]
    error: str