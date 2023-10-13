from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Comment(BaseModel):
    article_id: int | str
    comment_start_index: int
    comment_end_index: int
    date: str | None = Field(default=datetime.today().strftime("%Y-%m-%d"))
    content: str
    author: str
