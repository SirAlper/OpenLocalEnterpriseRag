from typing import Optional, List
from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class SyncTableRequest(BaseModel):
    table_name: str
    text_columns: Optional[List[str]] = None
    title_column: Optional[str] = None
    id_column: Optional[str] = None


class TestQueryRequest(BaseModel):
    query: str
