from typing import Union, Optional

from pydantic import BaseModel


class Comment(BaseModel):
    article_id: Union[int, str]
    comment_start_index: int
    comment_end_index: int
    date: Optional[str]
    content: str
    author: str
