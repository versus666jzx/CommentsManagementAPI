from datetime import datetime

from elasticsearch import Elasticsearch, NotFoundError, BadRequestError
from fastapi import FastAPI
from fastapi.responses import JSONResponse

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
    """
)

elastic_user = "elastic"
elastic_passwd = "elastic"

# Подключение к Elasticsearch
es = Elasticsearch(["https://elastic:9200"], basic_auth=(elastic_user, elastic_passwd), verify_certs=False)

# Список всех индексов в эластике
ALL_ARTICLE_INDEXES = ["ru_articles", "en_articles", "other_articles"]
ALL_COMMENTS_INDEXES = ["ru_comments", "en_comments", "other_comments"]

# es.indices.delete(index="ru_articles")
# es.indices.delete(index="en_articles")
# es.indices.delete(index="other_articles")

# Создание индекса (если не существует)

if (not es.indices.exists(index="ru_articles") or
    not es.indices.exists(index="en_articles") or
    not es.indices.exists(index="other_articles") or

    not es.indices.exists(index="ru_comments") or
    not es.indices.exists(index="en_comments") or
    not es.indices.exists(index="other_comments")
):
    ru_article_mappings = {
        "properties": {
            "title": {"type": "text", "analyzer": "russian"},
            "content": {"type": "text", "analyzer": "russian"},
            "date": {"type": "date"}
        }
    }

    en_article_mappings = {
        "properties": {
            "title": {"type": "text", "analyzer": "english"},
            "content": {"type": "text", "analyzer": "english"},
            "date": {"type": "date", "format": "yyy-MM-dd"}
        }
    }

    other_article_mappings = {
        "properties": {
            "title": {"type": "text", "analyzer": "standard"},
            "content": {"type": "text", "analyzer": "standard"},
            "date": {"type": "date"}
        }
    }

    ru_comments_mappings = {
        "properties": {
            "content": {"type": "text", "analyzer": "russian"}
        }
    }

    en_comments_mappings = {
        "properties": {
            "content": {"type": "text", "analyzer": "english"}
        }
    }

    other_comments_mappings = {
        "properties": {
            "content": {"type": "text", "analyzer": "standard"}
        }
    }

    es.indices.create(
        index="ru_articles",
        mappings=ru_article_mappings
    )

    es.indices.create(
        index="en_articles",
        mappings=en_article_mappings
    )

    es.indices.create(
        index="other_articles",
        mappings=other_article_mappings
    )

    es.indices.create(
        index="ru_comments",
        mappings=ru_comments_mappings
    )

    es.indices.create(
        index="en_comments",
        mappings=en_comments_mappings
    )

    es.indices.create(
        index="other_comments",
        mappings=other_comments_mappings
    )


def select_article_index_by_article_lang(index_lang: str):
    match index_lang:
        case "ru" | "RU":
            return "ru_articles"
        case "en" | "EN":
            return "en_articles"
        case _:
            return "other_articles"


def select_comment_index_by_article_lang(index_lang: str):
    match index_lang:
        case "ru" | "RU":
            return "ru_comments"
        case "en" | "EN":
            return "en_comments"
        case _:
            return "other_comments"


@app.post("/create_article")
def create_article(
        article_lang: str,
        title: str,
        content: str,
        tags: list[str],
        author: str
):
    """
        **Создание статьи.**

    Параметры:
    -----------
    - `article_lang` (str):
        Язык статьи.
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
        content_indexes=list(range(len(content.split())))
    ).model_dump()

    match_index = select_article_index_by_article_lang(index_lang=article_lang)

    try:
        response = es.index(index=match_index, document=article)
        res = ApiResult(
            status="ok",
            message="article created",
            result={"article_id": response.get("_id")}
        )
    except BadRequestError as err:
        res = ApiResult(
            status="error",
            message=f"{err}"
        )
    return JSONResponse(res())


@app.post("/edit_article_content")
def edit_article_content(article_lang: str, article_id: str, article_text: str):
    """
    **Редактирование содержания статьи.**

    Параметры:
    -----------
    - `article_lang` (str):
        Язык статьи, которую необходимо отредактировать.
    - `article_id` (str):
        Уникальный идентификатор статьи, которую необходимо отредактировать.
    - `article_text` (str):
        Новое содержание статьи.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со статусом редкатирования статьи и её версии.

    """

    index = select_article_index_by_article_lang(index_lang=article_lang)

    body = {
        "doc": {
            "content": article_text,
            "content_indexes": list(range(len(article_text.split())))
        }
    }

    try:
        response = es.update(index=index, id=article_id, body=body)
        res = ApiResult(
            status="ok",
            result={"updated": response.get("result"), "version": response.get("_version")}
        )
    except Exception as err:
        res = ApiResult(
            status="error",
            message=f"{err}"
        )

    return res()


@app.post("/delete_article")
def delete_article(article_lang: str, article_id: str):
    """
    **Удаление статьи по её ID.**

    Параметры:
    -----------
    - `article_lang` (str):
        Язык статьи, которую необходимо удалить.
    - `article_id` (str):
        Уникальный идентификатор статьи, которую необходимо удалить.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с результатом удаления статьи или ошибкой.

    """

    index = select_article_index_by_article_lang(article_lang)

    try:
        response = es.delete(index=index, id=article_id)
        res = ApiResult(
            status="ok",
            result={"status": response.get("result")}
        )
    except NotFoundError:
        res = ApiResult(
            status="error",
            message=f"Article with id {article_id} does not exist"
        )
    except Exception as err:
        res = ApiResult(
            status="error",
            message=f"{err}"
        )
    return JSONResponse(res())


@app.post("/add_comment")
def add_comment(
        comment_lang: str,
        article_id: str,
        comment_start_index: int,
        comment_end_index: int,
        content: str,
        author: str
):

    """
    **Добавление комментария к статье.**

    Параметры:
    -----------
    - `comment_lang` (str):
        Язык комментария.
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
        author=author
    ).model_dump()

    index = select_comment_index_by_article_lang(comment_lang)

    try:
        response = es.index(index=index, document=comment)
        res = ApiResult(
            status="ok",
            message="comment published",
            result={"comment_id": response.get("_id")}
        )
    except BadRequestError as err:
        res = ApiResult(
            status="error",
            message=f"{err}"
        )
    return JSONResponse(res())


@app.post("/edit_comment")
def edit_comment(comment_lang: str, comment_id: str, comment_text: str):
    """
    **Редактирование комментария.**

    Параметры:
    -----------
    - `comment_lang` (str):
        Язык комментария, который необходимо отредактировать.
    - `comment_id` (str):
        Уникальный идентификатор комментария, который необходимо отредактировать.
    - `comment_text` (str):
        Новое содержание комментария.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со статусом изменения комментария и его версией или ошибкой.

    """

    index = select_comment_index_by_article_lang(index_lang=comment_lang)

    body = {
        "doc": {
            "content": comment_text
        }
    }

    try:
        response = es.update(index=index, id=comment_id, body=body)
        res = ApiResult(
            status="ok",
            result={"updated": response.get("result"), "version": response.get("_version")}
        )
    except Exception as err:
        res = ApiResult(
            status="error",
            message=f"{err}"
        )

    return res()


@app.post("delete_comment")
def delete_comment(comment_lang: str, comment_id: str):
    """
    **Удаление комментария по его ID.**

    Параметры:
    -----------
    - `comment_lang` (str):
        Язык комментария, который необходимо удалить.
    - `comment_id` (str):
        Уникальный идентификатор комментария, который необходимо удалить.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с результатом удаления комментария или ошибкой.

    """

    index = select_comment_index_by_article_lang(comment_lang)

    try:
        response = es.delete(index=index, id=comment_id)
        res = ApiResult(
            status="ok",
            result={"status": response.get("result")}
        )
    except NotFoundError:
        res = ApiResult(
            status="error",
            message=f"Comment with id {comment_id} does not exist"
        )
    except Exception as err:
        res = ApiResult(
            status="error",
            message=f"{err}"
        )
    return JSONResponse(res())


@app.get("/search_article")
def search_articles(query: str):
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
                "fields": ["title", "content"]
            }
        }
    }

    try:
        response = es.search(index=ALL_ARTICLE_INDEXES, body=body)
        articles = [{
            "title": hit.get("_source").get("title"),
            "content": hit.get("_source").get("content"),
            "author": hit.get("_source").get("author"),
            "tags": hit.get("_source").get("tags"),
            "content_indexes": hit.get("_source").get("content_indexes")
        }
            for hit in response["hits"]["hits"]]
        print(articles)
        res = ApiResult(
            status="ok",
            result={"articles": articles}
        )
    except Exception as err:
        res = ApiResult(
            status="error",
            message=f"{err}"
        )
    return JSONResponse(res())


@app.get("/search_comments")
def search_comments(query: str):
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
            "match": {
                "content": query
            }
        }
    }

    try:
        response = es.search(index=ALL_COMMENTS_INDEXES, body=body)

        comments = [{
            "id": hit.get("_id"),
            "index": hit.get("_index"),
            "comment_start_index": hit.get("_source").get("comment_start_index", None),
            "comment_end_index": hit.get("_source").get("comment_end_index", None),
            "date": hit.get("_source").get("date", ""),
            "content": hit.get("_source").get("content", None),
            "author": hit.get("_source").get("author", None)
        }
            for hit in response["hits"]["hits"]]

        res = ApiResult(
            status="ok",
            result={"comments": comments}
        )
    except Exception as err:
        res = ApiResult(
            status="error",
            message=f"{err}"
        )
    return JSONResponse(res())


@app.get("/get_all_articles")
def get_all_articles():
    """
    **Получение всех статей.**

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со списком всех статей или ошибкой.

    """

    try:
        response = es.search(index=ALL_ARTICLE_INDEXES, body={"query": {"match_all": {}}})
        articles = [{
            "id": hit.get("_id"),
            "index": hit.get("_index"),
            "title": hit.get("_source").get("title", ""),
            "content": hit.get("_source").get("content", ""),
            "tags": hit.get("_source").get("tags", []),
            "date": hit.get("_source").get("date", ""),
            "content_indexes": hit.get("_source").get("content_indexes", [])
        }
            for hit in response["hits"]["hits"]]
        res = ApiResult(
            status="ok",
            result={"articles": articles}
        )
    except Exception as err:
        res = ApiResult(
            status="error",
            message=f"{err}"
        )
    return JSONResponse(res())


@app.get("/get_article_by_id")
def get_article_by_id(article_lang: str, article_id: str):
    """
    **Получение статьи по её ID.**

    Параметры:
    -----------
    - `article_lang` (str):
        Язык статьи, которую необходимо получить.
    - `article_id` (str):
        Уникальный идентификатор статьи, которую необходимо получить.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON с данными статьи или ошибкой.

    """

    index = select_article_index_by_article_lang(article_lang)

    try:
        response = es.get(index=index, id=article_id)
        article = Article(**response["_source"]).model_dump()

        res = ApiResult(
            status="ok",
            result={"article": article}
        )
    except Exception as err:
        res = ApiResult(
            status="error",
            message=f"{err}"
        )
    return JSONResponse(res())


@app.get("/get_article_comments")
def get_article_comments(article_lang: str, article_id: str):
    """
    **Получение комментариев к статье.**

    Параметры:
    -----------
    - `article_lang` (str):
        Язык статьи, комментарии к которой необходимо получить.
    - `article_id` (str):
        Уникальный идентификатор статьи, комментарии к которой необходимо получить.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со списком комментариев к статье или ошибкой.

    """

    index = select_comment_index_by_article_lang(article_lang)

    body = {
        "query": {
            "match": {
                "article_id": article_id
            }
        }
    }

    try:
        response = es.search(index=index, body=body)

        comments = [{
            "id": hit.get("_id"),
            "index": hit.get("_index"),
            "comment_start_index": hit.get("_source").get("comment_start_index", None),
            "comment_end_index": hit.get("_source").get("comment_end_index", None),
            "date": hit.get("_source").get("date", ""),
            "content": hit.get("_source").get("content", None),
            "author": hit.get("_source").get("author", None)
        }
            for hit in response["hits"]["hits"]]

        res = ApiResult(
            status="ok",
            result={"article_comments": comments}
        )
    except Exception as err:
        res = ApiResult(
            status="error",
            message=f"{err}"
        )
    return JSONResponse(res())


@app.on_event("shutdown")
def app_shutdown():
    es.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
