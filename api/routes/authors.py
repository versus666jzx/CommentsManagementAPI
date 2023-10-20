from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api.classes.result import ApiResult
from api.es_tools.es_connection import es_instance

authors_router = APIRouter(
    prefix="/authors", tags=["Authors"], responses={404: {"description": "Not found"}}
)


@authors_router.get("/get_all_articles_authors")
def get_all_articles_authors():
    """
    **Получение списка всех авторов.**

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со списком авторов.

    """

    body = {"aggs": {"author": {"terms": {"field": "author.keyword", "size": 10}}}}

    try:
        response = es_instance.es.search(index="articles", body=body)
        authors_list = list(
            {hit.get("_source").get("author", None) for hit in response["hits"]["hits"]}
        )
        res = ApiResult(status="ok", result={"authors_list": authors_list})
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@authors_router.get("/get_articles_by_author")
def get_articles_by_author(author_name: str, size: int = 10, get_from: int = 0):
    """
    **Получение всех статей от указанного автора.**

    Параметры:
    -----------
    - `author_name` (str):
        Имя автора, статьи которого необходимо получить.
    - `size` (int):
        Количество возвращаемых статей.
    - `get_from` (int)
        Стартовая позиция поиска.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со списком комментариев к статье или ошибкой.
    """

    body = {"query": {"match": {"author": author_name}}}

    try:
        response = es_instance.es.search(
            index="articles", body=body, size=size, from_=get_from
        )
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

        res = ApiResult(status="ok", result={"article_comments": articles})
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())
