from psycopg2 import connect

from api.classes.settings import Settings

settings = Settings()


class PGInstance:
    def __init__(self):
        self.pg_connect = connect(
            host=settings.PG_HOST,
            port=settings.PG_PORT,
            user=settings.PG_USER,
            password=settings.PG_PASSWORD,
            dbname="public"
        )

    def close_connection(self):
        self.pg_connect.close()
