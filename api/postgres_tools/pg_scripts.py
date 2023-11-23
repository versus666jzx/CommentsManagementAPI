import pandas as pd
from psycopg2.extras import execute_batch

from api.postgres_tools.postgres_connection import pg_instance


def insert_article_in_pg(
    article_id: str,
    title: str,
    tags: list[str],
    date: str,
    author: str,
    data: pd.DataFrame,
    article_description: str,
):
    sql = """
        INSERT INTO articles (article_id, title, tags, date, content_indexes, row_content, author, row_number_in_article, row_number_to_display, description) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
    """
    batch = []

    for _, row in data.iterrows():
        batch.append(
            (
                article_id,
                title,
                tags,
                date,
                row["list_tokens"],
                row["Строка"],
                author,
                row["Порядковый номер (по всему тексту)"],
                row["Номер строки текста для отображения"],
                article_description,
            )
        )

    execute_batch(pg_instance.cursor, sql, batch)


def insert_comments_in_pg(comments_batch):
    sql = """
    INSERT INTO comments (comment_id, article_id, comment_start_index, comment_end_index, date, content, author, row_number_in_article) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
    """

    execute_batch(pg_instance.cursor, sql, comments_batch)
