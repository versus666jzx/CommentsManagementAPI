from typing import Annotated

from elasticsearch import NotFoundError, BadRequestError
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from api.classes.article import Article
from api.classes.result import ApiResult
from api.es_tools.es_connection import es_instance

router = APIRouter(
    prefix="/article", tags=["Article"], responses={404: {"description": "Not found"}}
)


@router.post("/create_article")
async def create_article(article: Article):
    """
        **Создание статьи.**

    Параметры:
    -----------
    - `title` (str):
        Заголовок статьи.
    - `content` (str):
        Содержание статьи.
    - `tags` (list[str]):
        Список тегов, связанных со статьей.
    - `author` (str):
        Автор статьи.
    - `date` (str):
        Необязательное поле. Дата создания статьи в формате YYYY-mm-dd. Если не задана, то будет
        присвоена актуальная дата на момент вызова API запроса.
    - `content_indexes` (list[int])
        Необязательное поле. Список индексов слов/токенов контента статьи. Необходим для определения позиции
        комментария в статье. Если не задано, то будет посчитано автоматически.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с ID созданной статьи или ошибкой.

    """

    article.make_metadata()

    try:
        response = es_instance.es.index(index="articles", document=article.model_dump())
        res = ApiResult(
            status="ok",
            message="article created",
            result={"article_id": response.get("_id")},
        )
    except BadRequestError as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@router.post("/edit_article_content")
async def edit_article_content(
    article_id: Annotated[str, Body(...)], article_text: Annotated[str, Body(...)]
):
    """
    **Редактирование содержания статьи.**

    Параметры:
    -----------
    - `article_id` (str):
        Уникальный идентификатор статьи, которую необходимо отредактировать.
    - `article_text` (str):
        Новое содержание статьи.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со статусом редкатирования статьи и её версии.

    """

    body = {
        "doc": {
            "content": article_text,
            "content_indexes": list(range(len(article_text.split()))),
        }
    }

    try:
        response = es_instance.es.update(index="articles", id=article_id, body=body)
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


@router.post("/delete_article")
async def delete_article(article_id: Annotated[str, Body(...)]):
    """
    **Удаление статьи по её ID.**

    Параметры:
    -----------
    - `article_id` (str):
        Уникальный идентификатор статьи, которую необходимо удалить.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с результатом удаления статьи или ошибкой.

    """

    try:
        response = es_instance.es.delete(index="articles", id=article_id)
        res = ApiResult(status="ok", result={"status": response.get("result")})
    except NotFoundError:
        res = ApiResult(
            status="error", message=f"Article with id {article_id} does not exist"
        )
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@router.get("/search_article")
async def search_articles(query: str):
    """
    **Полнотекстовый поиск статей.**

    Параметры:
    -----------
    - `query` (str):
        Запрос для полнотекстового поиска статей.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с результатами поиска статей или ошибкой.
    """

    body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "title",
                    "title.russian",
                    "title.english",
                    "content",
                    "content.russian",
                    "content.english",
                ],
                "type": "most_fields",
            }
        }
    }

    try:
        response = es_instance.es.search(index="articles", body=body)
        print(response)
        articles = [
            {
                "title": hit.get("_source").get("title"),
                "content": hit.get("_source").get("content"),
                "author": hit.get("_source").get("author"),
                "tags": hit.get("_source").get("tags"),
                "content_indexes": hit.get("_source").get("content_indexes"),
            }
            for hit in response["hits"]["hits"]
        ]

        res = ApiResult(status="ok", result={"articles": articles})
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@router.get("/get_all_articles")
async def get_all_articles():
    """
    **Получение всех статей.**

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со списком всех статей или ошибкой.

    """

    try:
        response = es_instance.es.search(
            index="articles", body={"query": {"match_all": {}}}
        )
        articles = [
            {
                "id": hit.get("_id"),
                "index": hit.get("_index"),
                "title": hit.get("_source").get("title", ""),
                "content": hit.get("_source").get("content", ""),
                "tags": hit.get("_source").get("tags", []),
                "date": hit.get("_source").get("date", ""),
                "content_indexes": hit.get("_source").get("content_indexes", []),
            }
            for hit in response["hits"]["hits"]
        ]
        res = ApiResult(status="ok", result={"articles": articles})
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@router.get("/get_article_by_id")
async def get_article_by_id(article_id: str):
    """
    **Получение статьи по её ID.**

    Параметры:
    -----------
    - `article_id` (str):
        Уникальный идентификатор статьи, которую необходимо получить.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с данными статьи или ошибкой.

    """

    try:
        response = es_instance.es.get(index="articles", id=article_id)
        article = Article(**response["_source"]).model_dump()

        res = ApiResult(status="ok", result={"article": article})
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@router.get("/get_article_comments")
async def get_article_comments(article_id: str):
    """
    **Получение комментариев к статье.**

    Параметры:
    -----------
    - `article_id` (str):
        Уникальный идентификатор статьи, комментарии к которой необходимо получить.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со списком комментариев к статье или ошибкой.

    """

    body = {"query": {"match": {"article_id": article_id}}}

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

        res = ApiResult(status="ok", result={"article_comments": comments})
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())