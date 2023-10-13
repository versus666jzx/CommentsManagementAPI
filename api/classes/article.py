from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel
from pydantic import Field


class Article(BaseModel):
    title: str
    content: str
    tags: List[str]
    author: str
    date: str | None = Field(default=None)
    content_indexes: list[int] | None = Field(default=None)

    def make_metadata(self):
        self.date: Optional[str] = datetime.now().strftime("%Y-%m-%d")
        self.content_indexes: list[int] = list(range(len(self.content.split())))
