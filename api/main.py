from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware


from api.es_tools.es_connection import es_instance
from api.postgres_tools.postgres_connection import pg_instance
from api.routes import article, comment

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

app.include_router(article.router)
app.include_router(comment.router)

origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Service"])
def redirect_to_doc():
    """
    Перенаправляет в раздел с документацией при обращении к корневому каталогу API

    """
    return RedirectResponse("/docs")


@app.on_event("shutdown")
def app_shutdown():
    es_instance.close_connection()
    pg_instance.close_connection()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8001)
