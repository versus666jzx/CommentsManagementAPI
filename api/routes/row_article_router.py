from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api.postgres_tools.postgres_connection import pg_instance
from api.classes.result import ApiResult

row_article_router = APIRouter(
    prefix="/row_article",
    tags=["Article by row"],
    responses={404: {"description": "Not found"}},
)


@row_article_router.get("/get_article_rows")
async def get_article(article_id: str, from_row: int = 0, num_rows: int = 0):
    list_rows = []

    if num_rows == 0:
        sql = """
                 SELECT row_id, article_id, title, tags, date::text, content_indexes, row_content, author, row_number_in_article
                 FROM articles
                 WHERE article_id = %s AND %s < row_number_in_article;
              """
        pg_instance.cursor.execute(sql, (article_id, from_row))
        res = pg_instance.cursor.fetchall()
        for row in res:
            list_rows.append(
                {
                    "row_id": row[0],
                    "article_id": row[1],
                    "title": row[2],
                    "tags": row[3],
                    "date": row[4],
                    "content_indexes": row[5],
                    "row_content": row[6],
                    "author": row[7],
                    "row_number_in_article": row[8],
                }
            )
    else:
        sql = """
                 SELECT row_id, article_id, title, tags, date::text, content_indexes, row_content, author, row_number_in_article
                 FROM articles
                 WHERE article_id = %s AND %s < row_number_in_article AND row_number_in_article <= %s;
              """
        end_row = from_row + num_rows
        pg_instance.cursor.execute(sql, (article_id, from_row, end_row))
        res = pg_instance.cursor.fetchall()
        for row in res:
            list_rows.append(
                {
                    "row_id": row[0],
                    "article_id": row[1],
                    "title": row[2],
                    "tags": row[3],
                    "date": row[4],
                    "content_indexes": row[5],
                    "row_content": row[6],
                    "author": row[7],
                    "row_number_in_article": row[8],
                }
            )

    res = ApiResult(
        status="ok",
        result={"article_rows": list_rows}
    )

    return JSONResponse(res())


@row_article_router.get("/get_comments")
async def get_article(article_id: str):
    sql = """
    SELECT row_id, comment_id, article_id, comment_start_index, comment_end_index, date::text, content, author
    FROM comments
    WHERE article_id = %s
    """

    pg_instance.cursor.execute(sql, (article_id,))
    res = pg_instance.cursor.fetchall()
    article_comments = []
    for comment_row in res:
        article_comments.append(
            {
                "row_id": comment_row[0],
                "comment_id": comment_row[1],
                "article_id": comment_row[2],
                "comment_start_index": comment_row[3],
                "comment_end_index": comment_row[4],
                "date": comment_row[5],
                "content": comment_row[6],
                "author": comment_row[7],
            }
        )

    res = ApiResult(
        status="ok",
        result={"article_comments": article_comments}
    )

    return JSONResponse(res())
