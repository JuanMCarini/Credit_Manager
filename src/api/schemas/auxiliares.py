from typing import Optional, List, Any, Literal
from pydantic import BaseModel, Field


class TabulatorSort(BaseModel):
    field: str = Field(..., min_length=1, max_length=100)
    dir: Literal["asc", "desc"] = "asc"


class TabulatorFilter(BaseModel):
    field: str = Field(..., min_length=1, max_length=100)
    type: Literal["like", "=", "!=", ">", "<", ">=", "<="] = "="
    value: Any


class TabulatorRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=50, ge=1, le=5000)
    sort: Optional[List[TabulatorSort]] = []
    filter: Optional[List[TabulatorFilter]] = []
