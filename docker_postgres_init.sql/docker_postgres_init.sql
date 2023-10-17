create table articles
(
    row_id          serial,
    article_id      text,
    title           text,
    tags            text[],
    date            timestamp,
    content_indexes integer[]
);

alter table articles
    owner to postgres;

create index articles_article_id_index
    on articles (article_id);

create table comments
(
    row_id              serial,
    comment_id          text,
    article_id          text,
    comment_start_index integer,
    comment_end_index   integer,
    date                timestamp,
    content             text,
    author              text
);

alter table comments
    owner to postgres;

create index comments_article_id_index
    on comments (article_id);

