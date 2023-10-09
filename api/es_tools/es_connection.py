from elasticsearch import Elasticsearch

from api.classes.settings import Settings

settings = Settings()


class EsInstance:
    def __init__(self):
        self.es = Elasticsearch(
            hosts=[f"{settings.ES_PROTO}://{settings.ES_HOST}:{settings.ES_PORT}"],
            basic_auth=(settings.ES_USER, settings.ES_PASSWORD),
            verify_certs=settings.ES_VERIFY_CERTS,
        )

    def close_connection(self):
        self.es.close()

    def create_index_if_not_exist(self):
        if not self.es.indices.exists(index="articles") or not self.es.indices.exists(
            index="comments"
        ):
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
                    "author": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 10000
                            }
                        }
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

            self.es.indices.create(index="articles", mappings=article_mappings)
            self.es.indices.create(index="comments", mappings=comments_mappings)

    def delete_all_indexes(self):
        self.es.indices.delete(index="articles")
        self.es.indices.delete(index="comments")


es_instance = EsInstance()
if settings.DELETE_ALL_INDEXES_ON_STARTUP:
    es_instance.delete_all_indexes()
es_instance.create_index_if_not_exist()
