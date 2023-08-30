from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ApiResult(BaseModel):
    status: str
    message: Optional[str] = None
    result: Optional[str | dict] = None

    def __repr__(self):
        return {"status": self.status, "message": self.message, "result": self.result}.__str__()

    def __call__(self, *args, **kwargs):
        return {"status": self.status, "message": self.message, "result": self.result}
