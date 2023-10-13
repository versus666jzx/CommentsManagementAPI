from __future__ import annotations

import pandas as pd
import re
from api.classes.comment import Comment


class TokenCounter:
    value = 0


def get_list(row: str, counter: TokenCounter) -> list:
    res = list(range(counter.value, counter.value + len(row.split())))
    counter.value += len(row.split())
    return res


def find_word_indexes(source: str, search: str) -> tuple[int, int]:
    # Удаление знаков препинания и приведение к нижнему регистру для более точного поиска
    source_cleaned = re.sub(r"[^\w\s]", "", source.lower())
    search_cleaned = re.sub(r"[^\w\s]", "", search.lower())

    words = source_cleaned.split()
    search_words = search_cleaned.split()

    start_index = None
    end_index = None

    for i in range(len(words) - len(search_words) + 1):
        if words[i : i + len(search_words)] == search_words:
            start_index = i
            end_index = i + len(search_words) - 1
            break

    return start_index, end_index


def preprocess_excel_article(article_dataframe: pd.DataFrame) -> pd.DataFrame:
    article_dataframe["Комментарий"] = (
        article_dataframe["Комментарий"].replace("-", "").replace(pd.NA, "")
    )
    article_dataframe["Комментируемое слово"] = (
        article_dataframe["Комментируемое слово"].replace("-", "").replace(pd.NA, "")
    )

    grouped_data = article_dataframe.groupby("Номер строки текста для отображения")[
        ["Строка", "Комментируемое слово", "Комментарий"]
    ].agg(
        {
            "Строка": lambda x: set(x).pop(),
            "Комментируемое слово": set,
            "Комментарий": set,
        }
    )
    counter = TokenCounter()
    grouped_data["list_tokens"] = grouped_data["Строка"].apply(lambda x: get_list(x, counter))

    return grouped_data


def make_article(data: pd.DataFrame) -> dict[str, str | list]:
    article_content = ""
    article_list_indexes = []

    for idx, row in data[["Строка", "list_tokens"]].iterrows():
        article_content += f" {row['Строка']}"
        article_list_indexes.extend(row["list_tokens"])

    return {"article_content": article_content, "list_indexes": article_list_indexes}


def make_comments(data: pd.DataFrame, article_id: str | int) -> list[Comment]:
    list_comments = []
    for idx, row in data[["Строка", "list_tokens", "Комментируемое слово", "Комментарий"]].iterrows():
        indexes = []
        for comment in row["Комментируемое слово"]:
            if comment != "":
                indexes.append(find_word_indexes(row["Строка"], comment))
        if len(indexes) > 0:
            try:
                for index, comment_content in zip(indexes, row["Комментарий"]):
                    if index[0] == index[1]:
                        comment_start_index = comment_end_index = row["list_tokens"][index[0]]
                    else:
                        comment_start_index = row["list_tokens"][index[0]]
                        comment_end_index = row["list_tokens"][index[-1]]
                    list_comments.append(
                        Comment(
                            article_id=article_id,
                            comment_start_index=comment_start_index,
                            comment_end_index=comment_end_index,
                            content=comment_content,
                            author="Unknown"
                        )
                    )
            except TypeError:
                continue

    return list_comments
