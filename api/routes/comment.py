from typing import Annotated

from elasticsearch import NotFoundError, BadRequestError
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from api.classes.comment import Comment
from api.classes.result import ApiResult
from api.es_tools.es_connection import es_instance
from api.postgres_tools.postgres_connection import pg_instance

router = APIRouter(
    prefix="/comment", tags=["Comment"], responses={404: {"description": "Not found"}}
)


@router.post("/add_comment")
async def add_comment(comment: Comment):
    """
    **Добавление комментария к статье.**

    Параметры:
    -----------
    - `article_id` (str):
        Уникальный идентификатор статьи, к которой добавляется комментарий.
    - `comment_start_index` (int):
        Начальный индекс места в статье, к которому относится комментарий.
    - `comment_end_index` (int):
        Конечный индекс места в статье, к которому относится комментарий.
    - `content` (str):
        Содержание комментария.
    - `author` (str):
        Автор комментария.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с ID комментария или ошибкой.

    """

    try:
        response = es_instance.es.index(index="comments", document=comment.model_dump())
        res = ApiResult(
            status="ok",
            message="comment published",
            result={"comment_id": response.get("_id")},
        )
    except BadRequestError as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@router.post("/edit_comment")
async def edit_comment(
    comment_id: Annotated[str, Body(...)], comment_text: Annotated[str, Body(...)]
):
    """
    **Редактирование комментария.**

    Параметры:
    -----------
    - `comment_id` (str):
        Уникальный идентификатор комментария, который необходимо отредактировать.
    - `comment_text` (str):
        Новое содержание комментария.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со статусом изменения комментария и его версией или ошибкой.

    """

    body = {"doc": {"content": comment_text}}

    try:
        response = es_instance.es.update(index="comments", id=comment_id, body=body)
        res = ApiResult(
            status="ok",
            result={
                "updated": response.get("result"),
                "version": response.get("_version"),
            },
        )
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")

    return res()


@router.post("/delete_comment")
async def delete_comment(comment_id: Annotated[str, Body(...)]):
    """
    **Удаление комментария по его ID.**

    Параметры:
    -----------
    - `comment_id` (str):
        Уникальный идентификатор комментария, который необходимо удалить.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с результатом удаления комментария или ошибкой.

    """

    try:
        response = es_instance.es.delete(index="comments", id=comment_id)
        res = ApiResult(status="ok", result={"status": response.get("result")})
    except NotFoundError:
        res = ApiResult(
            status="error", message=f"Comment with id {comment_id} does not exist"
        )
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@router.post("/update_comment_in_row")
async def update_comment_in_row(comment_id: str, new_content: str):
    sql = """
    UPDATE comments
    SET content = %s
    WHERE comment_id = %s;
    """
    pg_instance.cursor.execute(sql, (new_content, comment_id))
    res = ApiResult(
        status="ok",
        result={"update_result": "comment_updated"}
    )
    return JSONResponse(res())


@router.get("/search_comments")
async def search_comments(query: str):
    """
    **Поиск комментариев по содержанию.**

    Параметры:
    -----------
    - `query` (str):
        Запрос для поиска комментариев по содержанию.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с результатами поиска комментариев или ошибкой.

    """

    body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["content", "content.russian", "content.english"],
            }
        }
    }

    try:
        response = es_instance.es.search(index="comments", body=body)

        comments = [
            {
                "id": hit.get("_id"),
                "index": hit.get("_index"),
                "comment_start_index": hit.get("_source").get("comment_start_index", None),
                "comment_end_index": hit.get("_source").get("comment_end_index", None),
                "date": hit.get("_source").get("date", ""),
                "content": hit.get("_source").get("content", None),
                "author": hit.get("_source").get("author", None),
                "article_id": hit.get("_source").get("article_id", None)
            }
            for hit in response["hits"]["hits"]
        ]

        res = ApiResult(status="ok", result={"comments": comments})
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@router.get("/get_comments_by_rows")
async def get_article(article_id: str, from_row: int = 0, num_rows: int = 0, sort_by: str = "desc"):
    article_comments = []

    if num_rows == 0:
        sql = """
        SELECT row_id, comment_id, article_id, comment_start_index, comment_end_index, date::text, content, author, row_number_in_article
        FROM comments
        WHERE article_id = %s AND %s < row_number_in_article
        ORDER BY row_number_in_article;
        """

        pg_instance.cursor.execute(sql, (article_id, from_row))
        res = pg_instance.cursor.fetchall()

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
                    "row_number_in_article": comment_row[8],
                }
            )
    else:
        sql = """
        SELECT row_id, comment_id, article_id, comment_start_index, comment_end_index, date::text, content, author, row_number_in_article
        FROM comments
        WHERE article_id = %s AND %s < row_number_in_article AND row_number_in_article <= %s
        ORDER BY row_number_in_article;
        """

        end_row = from_row + num_rows
        pg_instance.cursor.execute(sql, (article_id, from_row, end_row))
        res = pg_instance.cursor.fetchall()

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
                    "row_number_in_article": comment_row[8],
                }
            )

    if sort_by not in ["desc", "asc"]:
        res = ApiResult(
            status="error",
            message=f"Параметр sort_by может принимать значения 'desc' или 'asc'. Передано значение: {sort_by}"
        )
        return JSONResponse(res())
    
    if sort_by == "desc":
        reverse = True
    else:
        reverse = False

    sorted_comments = sorted(article_comments, key=lambda x: x["date"], reverse=reverse)
    res = ApiResult(status="ok", result={"article_comments": sorted_comments})

    return JSONResponse(res())
