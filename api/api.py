import json
from datetime import datetime
from typing import Annotated, Union

from elasticsearch import Elasticsearch, NotFoundError, BadRequestError
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse, RedirectResponse

from classes.article import Article
from classes.comment import Comment
from classes.result import ApiResult

app = FastAPI(
    title="API электронной библиотеки текстов",
    description="""
Все эндпоинты возвращают следующую структуру данных:

```
{
    status: str,
    message: Optional[str]
    result: Optional[str | dict]
}
```

_status_ - "ok" или "error"\n
_message_ - содержит более подробную информацию об ошибке, если status = "error"\n
_result_ - содержит результат выполнения запроса\n
    """,
)

elastic_user = "elastic"
elastic_passwd = "elastic"

# Подключение к Elasticsearch
es = Elasticsearch(
    ["https://localhost:9200"],
    basic_auth=(elastic_user, elastic_passwd),
    verify_certs=False,
)

# es.indices.delete(index="articles")
# es.indices.delete(index="comments")

# Создание индекса (если не существует)

if not es.indices.exists(index="articles") or not es.indices.exists(index="comments"):
    article_mappings = {
        "properties": {
            "title": {
                "type": "text",
                "fields": {
                    "russian": {"type": "text", "analyzer": "russian"},
                    "english": {"type": "text", "analyzer": "english"},
                },
            },
            "content": {
                "type": "text",
                "fields": {
                    "russian": {"type": "text", "analyzer": "russian"},
                    "english": {"type": "text", "analyzer": "english"},
                },
            },
            "date": {"type": "date"},
        }
    }

    comments_mappings = {
        "properties": {
            "content": {
                "type": "text",
                "fields": {
                    "russian": {"type": "text", "analyzer": "russian"},
                    "english": {"type": "text", "analyzer": "english"},
                },
            }
        }
    }

    es.indices.create(index="articles", mappings=article_mappings)

    es.indices.create(index="comments", mappings=comments_mappings)


@app.post("/create_article")
async def create_article(title: str, content: str, tags: list[str], author: str):
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

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с ID созданной статьи или ошибкой.

    """

    article = Article(
        title=title,
        content=content,
        tags=tags,
        author=author,
        date=datetime.today().strftime("%Y-%m-%d"),
        content_indexes=list(range(len(content.split()))),
    ).model_dump()

    try:
        response = es.index(index="articles", document=article)
        res = ApiResult(
            status="ok",
            message="article created",
            result={"article_id": response.get("_id")},
        )
    except BadRequestError as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@app.post("/edit_article_content")
async def edit_article_content(article_id: str, article_text: str):
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
        response = es.update(index="articles", id=article_id, body=body)
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


@app.post("/delete_article")
async def delete_article(article_id: str):
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
        response = es.delete(index="articles", id=article_id)
        res = ApiResult(status="ok", result={"status": response.get("result")})
    except NotFoundError:
        res = ApiResult(
            status="error", message=f"Article with id {article_id} does not exist"
        )
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@app.post("/add_comment")
async def add_comment(
    article_id: str,
    comment_start_index: int,
    comment_end_index: int,
    content: str,
    author: str,
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
    - `content` (str):
        Содержание комментария.
    - `author` (str):
        Автор комментария.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с ID комментария или ошибкой.

    """

    comment = Comment(
        article_id=article_id,
        comment_start_index=comment_start_index,
        comment_end_index=comment_end_index,
        date=datetime.today().strftime("%Y-%m-%d"),
        content=content,
        author=author,
    ).model_dump()

    try:
        response = es.index(index="comments", document=comment)
        res = ApiResult(
            status="ok",
            message="comment published",
            result={"comment_id": response.get("_id")},
        )
    except BadRequestError as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@app.post("/edit_comment")
async def edit_comment(comment_id: str, comment_text: str):
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
        response = es.update(index="comments", id=comment_id, body=body)
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


@app.post("delete_comment")
async def delete_comment(comment_id: str):
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
        response = es.delete(index="comments", id=comment_id)
        res = ApiResult(status="ok", result={"status": response.get("result")})
    except NotFoundError:
        res = ApiResult(
            status="error", message=f"Comment with id {comment_id} does not exist"
        )
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@app.get("/search_article")
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
        response = es.search(index="articles", body=body)
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


@app.get("/search_comments")
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
        response = es.search(index="comments", body=body)

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


@app.get("/get_all_articles")
async def get_all_articles():
    """
    **Получение всех статей.**

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со списком всех статей или ошибкой.

    """

    try:
        response = es.search(index="articles", body={"query": {"match_all": {}}})
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


@app.get("/get_article_by_id")
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
        response = es.get(index="articles", id=article_id)
        article = Article(**response["_source"]).model_dump()

        res = ApiResult(status="ok", result={"article": article})
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@app.get("/get_article_comments")
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
        response = es.search(index="comments", body=body)

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


@app.get("/")
def redirect_to_doc(token: Annotated[str, Depends(oauth2_scheme)]):
    """
    Перенаправляет в раздел с документацией при обращении к корневому каталогу API

    """
    return RedirectResponse("/docs")


@app.on_event("shutdown")
def app_shutdown():
    es.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8001)
