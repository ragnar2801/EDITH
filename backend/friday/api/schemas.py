"""Response models shared by several route modules."""

from datetime import date

from pydantic import BaseModel

from friday.core.schema_types import Nav


class NavPointOut(BaseModel):
    date: date
    nav: Nav


class FundRef(BaseModel):
    id: int
    name: str
    amfi_code: str | None
    fund_house: str | None
    fund_category: str | None
    plan: str | None
    option: str | None
    is_active: bool


class CoverageOut(BaseModel):
    first: date | None
    last: date | None
    count: int


class ModelRef(BaseModel):
    id: int
    name: str


class BucketRef(BaseModel):
    id: int
    name: str
    paper: bool
    """Pretend purchases at real NAVs, kept out of the portfolio's totals."""
