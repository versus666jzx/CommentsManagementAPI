from typing import List, Optional

from pydantic import BaseModel


class Article(BaseModel):
    title: str
    content: str
    tags: List[str]
    author: str
    date: Optional[str]
    content_indexes: list[int]
