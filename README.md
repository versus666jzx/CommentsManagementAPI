## API электронной библиотеки текстов

### Запуск

1. Клонировать репозиторий
2. Перейти в директорию CommentsManagementAPI и выполнить следующую команду:

```shell
docker-compose -up -d
```

После успешного запуска документация по API будет доступна по ссылке: http://localhost/docs/
 
### Настройки

**API** поддерживает настройки через переменные окружения контейнера.

| Имя переменной                | Описание                                                | Значение по умолчанию  |
|-------------------------------|---------------------------------------------------------|------------------------|
| ES_USER                       | имя пользователя для подключения к ElasticSearch        | elastic                |
| ES_PASSWORD                   | пароль для подключения к ElasticSearch                  | elastic                |
| ES_PROTO                      | протокол для подключения к ElasticSearch                | https                  |
| ES_HOST                       | хост с ElasticSearch                                    | localhost              |
| ES_PORT                       | порт для подключения к ElasticSearch                    | 9200                   |
| ES_VERIFY_CERTS               | вкл/выкл верификацию htpps сертификатов в ElasticSearch | False                  |
| DELETE_ALL_INDEXES_ON_STARTUP | очистить индексы ElasticSearch при рестарте контейнера  | False                  |

```
ES_USER - имя пользователя для подключения к ElasticSearch (default="elastic")
ES_PASSWORD - пароль для подключения к ElasticSearch (default="elastic")
ES_PROTO - протокол для подключения к ElasticSearch (default="https")
ES_HOST - хост с ElasticSearch (default="localhost")
ES_PORT - порт для подключения к ElasticSearch (default="9200")
ES_VERIFY_CERTS - вкл/выкл верификацию htpps сертификатов в ElasticSearch (default=False)
DELETE_ALL_INDEXES_ON_STARTUP - очистить индексы ElasticSearch при рестарте контейнера (default=False)
```