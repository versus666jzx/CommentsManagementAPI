from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # настройки ES
    ES_PASSWORD: str = Field(default="elastic")
    ES_USER: str = Field(default="elastic")
    ES_PROTO: str = Field(default="https")
    ES_HOST: str = Field(default="localhost")
    ES_PORT: str | int = Field(default="9200")
    ES_VERIFY_CERTS: bool = Field(default=False)
    # атрибуты
    DELETE_ALL_INDEXES_ON_STARTUP: bool = Field(default=False)
