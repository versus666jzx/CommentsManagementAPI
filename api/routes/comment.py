from typing import Annotated

from elasticsearch import NotFoundError, BadRequestError
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from api.classes.comment import Comment
from api.classes.result import ApiResult
from api.es_tools.es_connection import es_instance

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


@router.post("delete_comment")
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
                "content": query,
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
            }
            for hit in response["hits"]["hits"]
        ]

        res = ApiResult(status="ok", result={"comments": comments})
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())
