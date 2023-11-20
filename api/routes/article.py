import io
import json
from datetime import datetime
from typing import Annotated

import pandas as pd
from elasticsearch import NotFoundError, BadRequestError
from fastapi import APIRouter, Body, UploadFile
from fastapi.responses import JSONResponse

from api.classes.article import Article
from api.classes.result import ApiResult
from api.es_tools.es_connection import es_instance
from api.routes.comment import add_comment
from api.tools.data_preprocess import (
    preprocess_excel_article,
    make_article,
    make_comments,
)
from api.postgres_tools.pg_scripts import insert_article_in_pg, insert_comments_in_pg
from api.postgres_tools.postgres_connection import pg_instance


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


@router.post("/create_article_from_excel")
async def create_article_from_excel(excel_file: UploadFile) -> JSONResponse:
    article_title, article_author = (
        excel_file.filename.split("_")[0],
        excel_file.filename.split("_")[1].split(".")[0],
    )
    article_file = await excel_file.read()
    data = pd.read_excel(io.BytesIO(article_file))
    processed_data = preprocess_excel_article(data)
    res = make_article(processed_data)
    created = await create_article(
        Article(
            title=article_title,
            content=res["article_content"],
            tags=[],
            author=article_author,
            content_indexes=res["list_indexes"],
        )
    )
    created = json.loads(created.body.decode("utf-8"))

    list_of_comments = make_comments(
        data=processed_data, article_id=created["result"]["article_id"]
    )

    created_comments_batch = []
    for comment in list_of_comments:
        res = await add_comment(comment=comment)

        res = json.loads(res.body.decode("utf-8"))

        created_comments_batch.append(
            (
                res["result"]["comment_id"],
                created["result"]["article_id"],
                comment.comment_start_index,
                comment.comment_end_index,
                comment.date,
                comment.content,
                comment.author,
                comment.row_number_in_article,
            )
        )

    insert_article_in_pg(
        article_id=created["result"]["article_id"],
        title=article_title,
        tags=[],
        date=datetime.now().strftime("%Y-%m-%d"),
        author=article_author,
        data=processed_data,
    )

    insert_comments_in_pg(comments_batch=created_comments_batch)

    result = ApiResult(
        status="ok", result={"article_id": created["result"]["article_id"]}
    )

    return JSONResponse(result())


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


@router.post("/update_article_content_by_row")
async def update_article_content_by_row(article_id: str, new_content: str, article_row: int):
    sql = """
    UPDATE articles
    SET row_content = %s
    WHERE article_id = %s
    AND row_number_in_article = %s;
    """

    pg_instance.cursor.execute(sql, (new_content, article_id, article_row))
    res = ApiResult(
        status="ok",
        result={"update_result": "article content updated"}
    )
    return JSONResponse(res())


@router.get("/search_article")
async def search_articles(query: str, size: int = 10, get_from: int = 0):
    """
    **Полнотекстовый поиск статей.**

    Параметры:
    -----------
    - `query` (str):
        Запрос для полнотекстового поиска статей.
    - `size` (int):
        Количество возвращаемых статей.
    - `get_from` (int)
        Стартовая позиция поиска.

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
        response = es_instance.es.search(
            index="articles", body=body, size=size, from_=get_from
        )
        print(response)
        articles = [
            {         
                "id": hit.get("_id"),
                "author": hit.get("_source").get("author"),
                "title": hit.get("_source").get("title"),
                "content": hit.get("_source").get("content"),
                "tags": hit.get("_source").get("tags"),
                # "content_indexes": hit.get("_source").get("content_indexes"),
            }
            for hit in response["hits"]["hits"]
        ]

        res = ApiResult(status="ok", result={"articles": articles})
    except Exception as err:
        res = ApiResult(status="error", message=f"{err}")
    return JSONResponse(res())


@router.get("/get_all_articles")
async def get_all_articles(size: int = 10, get_from: int = 0):
    """
    **Получение всех статей.**

    Параметры:
    -----------
    - `size` (int):
        Количество возвращаемых статей.
    - `get_from` (int)
        Стартовая позиция поиска.

    Возвращает:
    -----------
    `JSONResponse`
        Ответ в формате JSON со списком всех статей или ошибкой.

    """

    try:
        response = es_instance.es.search(
            index="articles",
            body={"query": {"match_all": {}}},
            size=size,
            from_=get_from,
        )
        articles = [
            {
                "id": hit.get("_id"),
                "index": hit.get("_index"),
                "title": hit.get("_source").get("title", ""),
                "author": hit.get("_source").get("author", ""),
                "content": 'тут будет описание', 
                # "content": hit.get("_source").get("content", ""),
                "tags": hit.get("_source").get("tags", []),
                "date": hit.get("_source").get("date", ""),
                # "content_indexes": hit.get("_source").get("content_indexes", []),
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
        response = es_instance.es.search(index="comments", body=body, size=1000)

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


@router.get("/get_article_by_rows")
async def get_article(article_id: str, from_row: int = 0, num_rows: int = 0):

    list_rows = []

    if num_rows == 0:
        sql = """
                 SELECT row_id, article_id, title, tags, date::text, content_indexes, row_content, author, row_number_in_article
                 FROM articles
                 WHERE article_id = %s AND %s < row_number_in_article
                 ORDER BY row_number_in_article;
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
                    # "content_indexes": row[5],
                    "row_content": row[6],
                    "author": row[7],
                    "row_number_in_article": row[8],
                }
            )
    else:
        sql = """
                 SELECT row_id, article_id, title, tags, date::text, content_indexes, row_content, author, row_number_in_article
                 FROM articles
                 WHERE article_id = %s AND %s < row_number_in_article AND row_number_in_article <= %s
                 ORDER BY row_number_in_article;
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
                    # "content_indexes": row[5],
                    "row_content": row[6],
                    "author": row[7],
                    "row_number_in_article": row[8],
                }
            )

    res = ApiResult(status="ok", result={"article_rows": list_rows})

    return JSONResponse(res())
