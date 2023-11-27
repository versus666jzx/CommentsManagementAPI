from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Comment(BaseModel):
    article_id: int | str
    comment_start_index: int
    comment_end_index: int
    date: str = Field(default=datetime.today().strftime("%Y-%m-%d"))
    content: str
    author: str
    comment_html: str | None = Field(default=None)


class PGComment(Comment):
    row_number_in_article: int
