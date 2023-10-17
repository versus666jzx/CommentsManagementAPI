from psycopg2 import connect

from dataclasses import dataclass
from api.classes.settings import Settings

settings = Settings()


@dataclass
class PGInstance:
    def __init__(self):
        self.pg_connect = connect(
            host=settings.PG_HOST,
            port=settings.PG_PORT,
            user=settings.PG_USER,
            password=settings.PG_PASSWORD,
            dbname="public",
            autocommit=True,
            options="-c statement_timeout=300000",
        )

    def __post_init__(self):
        self.pg_connect.autocommit = True

    def close_connection(self):
        self.pg_connect.close()


pg_instance = PGInstance()
