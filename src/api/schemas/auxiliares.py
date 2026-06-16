from typing import Optional, List, Any
from pydantic import BaseModel

class TabulatorSort(BaseModel):
    field: str
    dir: str

class TabulatorFilter(BaseModel):
    field: str
    type: str
    value: Any

class TabulatorRequest(BaseModel):
    page: int = 1
    size: int = 50
    sort: Optional[List[TabulatorSort]] = []
    filter: Optional[List[TabulatorFilter]] = []
