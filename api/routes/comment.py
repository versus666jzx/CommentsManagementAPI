import secrets
from typing import Annotated

from elasticsearch import NotFoundError, BadRequestError
from fastapi import APIRouter, Body, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasicCredentials

from api.classes.comment import PGComment
from api.classes.result import ApiResult
from api.es_tools.es_connection import es_instance
from api.postgres_tools.postgres_connection import pg_instance
from api.tools.auth import security


router = APIRouter(
    prefix="/comment", tags=["Comment"], responses={404: {"description": "Not found"}}
)


@router.post("/add_comment")
async def add_comment(
    comment: PGComment, credentials: Annotated[HTTPBasicCredentials, Depends(security)]
):
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
    - `date` (str):
        Дата комментария
    - `content` (str):
        Содержание комментария.
    - `author` (str):
        Автор комментария.
    - `comment_html` (str):
        Текст комментария с HTML.
    - `row_number_in_article`:
        Номер строки в статье, которой принадлежит комментарий.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с ID комментария или ошибкой.

    """

    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = b"admin"
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = b"admin"
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    sql = """
    INSERT INTO comments (comment_id, article_id, comment_start_index, comment_end_index, date, content, author, comment_html, row_number_in_article)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    try:
        response = es_instance.es.index(index="comments", document=comment.model_dump())
        pg_instance.cursor.execute(
            sql,
            (
                response.get("_id"),
                comment.article_id,
                comment.comment_start_index,
                comment.comment_end_index,
                comment.date,
                comment.content,
                comment.author,
                comment.comment_html,
                comment.row_number_in_article,
            ),
        )

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
    comment_id: Annotated[str, Body(...)],
    comment_text: Annotated[str, Body(...)],
    comment_html: Annotated[str, Body(...)],
    credentials: Annotated[HTTPBasicCredentials, Depends(security)]
):
    """
    **Редактирование комментария.**

    Параметры:
    -----------
    - `comment_id` (str):
        Уникальный идентификатор комментария, который необходимо отредактировать.
    - `comment_text` (str):
        Новое содержание комментария.
    - `comment_html` (str):
        Новое содержание HTML-комментария

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со статусом изменения комментария и его версией или ошибкой.

    """

    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = b"admin"
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = b"admin"
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    body = {"doc": {"content": comment_text, "comment_html": comment_html}}

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
async def delete_comment(
        comment_id: Annotated[str, Body(...)],
        credentials: Annotated[HTTPBasicCredentials, Depends(security)]
):
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

    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = b"admin"
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = b"admin"
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    sql = """
    DELETE
    FROM comments
    WHERE comment_id = %s
    """

    try:
        response = es_instance.es.delete(index="comments", id=comment_id)
        pg_instance.cursor.execute(sql, (comment_id,))
        res = ApiResult(status="ok", result={"status": response.get("result")})
    except NotFoundError:
        res = ApiResult(
            status="error", message=f"Comment with id {comment_id} does not exist"
        )
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@router.post("/update_comment_in_row")
async def update_comment_in_row(
    comment_id: str, new_content: str, new_comment_html: str, credentials: Annotated[HTTPBasicCredentials, Depends(security)]
):

    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = b"admin"
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = b"admin"
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    sql = """
    UPDATE comments
    SET content = %s, comment_html = %s
    WHERE comment_id = %s;
    """
    pg_instance.cursor.execute(sql, (new_content, new_comment_html, comment_id))
    res = ApiResult(status="ok", result={"update_result": "comment_updated"})
    return JSONResponse(res())


@router.get("/search_comments")
async def search_comments(query: str, sort_by: str = "desc"):
    """
    **Поиск комментариев по содержанию.**

    Параметры:
    -----------
    - `query` (str):
        Запрос для поиска комментариев по содержанию.
    - `sort_by` (str):
        Сортировка по дате создания комментария. Может принимать значения 'desc' или 'asc'.

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
                "comment_start_index": hit.get("_source").get(
                    "comment_start_index", None
                ),
                "comment_end_index": hit.get("_source").get("comment_end_index", None),
                "date": hit.get("_source").get("date", ""),
                "content": hit.get("_source").get("content", None),
                "author": hit.get("_source").get("author", None),
                "article_id": hit.get("_source").get("article_id", None),
                "comment_html": hit.get("_source").get("comment_html", None),
                "row_number_in_article": hit.get("_source").get(
                    "row_number_in_article", None
                ),
            }
            for hit in response["hits"]["hits"]
        ]

        if sort_by not in ["desc", "asc"]:
            res = ApiResult(
                status="error",
                message=f"Параметр sort_by может принимать значения 'desc' или 'asc'. Передано значение: {sort_by}",
            )
            return JSONResponse(res())

        if sort_by == "desc":
            reverse = True
        else:
            reverse = False

        sorted_comments = sorted(comments, key=lambda x: x["date"], reverse=reverse)

        res = ApiResult(status="ok", result={"comments": sorted_comments})
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@router.get("/get_comments_by_rows")
async def get_comments_by_rows(
    article_id: str, from_row: int = 0, num_rows: int = 0, sort_by: str = "desc"
):
    article_comments = []

    if num_rows == 0:
        sql = """
        SELECT row_id, comment_id, article_id, comment_start_index, comment_end_index, date::text, content, author, row_number_in_article, comment_html
        FROM comments
        WHERE article_id = %s AND %s <= row_number_in_article
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
                    "comment_html": comment_row[9],
                }
            )
    else:
        sql = """
        SELECT row_id, comment_id, article_id, comment_start_index, comment_end_index, date::text, content, author, row_number_in_article, comment_html
        FROM comments
        WHERE article_id = %s AND %s <= row_number_in_article AND row_number_in_article <= %s
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
                    "comment_html": comment_row[9],
                }
            )

    if sort_by not in ["desc", "asc"]:
        res = ApiResult(
            status="error",
            message=f"Параметр sort_by может принимать значения 'desc' или 'asc'. Передано значение: {sort_by}",
        )
        return JSONResponse(res())

    if sort_by == "desc":
        reverse = True
    else:
        reverse = False

    sorted_comments = sorted(article_comments, key=lambda x: x["date"], reverse=reverse)
    res = ApiResult(status="ok", result={"article_comments": sorted_comments})

    return JSONResponse(res())
