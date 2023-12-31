create table articles
(
    row_id                serial,
    article_id            text,
    title                 text,
    tags                  text[],
    date                  timestamp,
    content_indexes       integer[],
    row_content           text,
    author                text,
    row_number_in_article integer,
    row_number_to_display integer,
    description           text
);

alter table articles
    owner to postgres;

create index articles_article_id_index
    on articles (article_id);

create index articles_article_id_row_id_index
    on articles (article_id, row_id);

create table comments
(
    row_id                serial,
    comment_id            text,
    article_id            text,
    comment_start_index   integer,
    comment_end_index     integer,
    date                  timestamp,
    content               text,
    author                text,
    row_number_in_article integer,
    comment_html          text
);

alter table comments
    owner to postgres;

create index comments_article_id_index
    on comments (article_id);

