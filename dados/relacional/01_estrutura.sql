-- Estrutura fornecida pelo autor. Executar em um banco novo, com PostgreSQL 18+.
-- As constraints NOT NULL nomeadas foram colocadas junto das colunas,
-- sem repetir a mesma restricao na definicao da tabela.
BEGIN;

CREATE TABLE public.categories (
    id serial4 CONSTRAINT categories_id_not_null NOT NULL,
    name varchar(64) CONSTRAINT categories_name_not_null NOT NULL,
    description text NULL,
    created_at timestamptz DEFAULT now() CONSTRAINT categories_created_at_not_null NOT NULL,
    CONSTRAINT categories_pkey PRIMARY KEY (id)
);

CREATE TABLE public.events (
    id bigserial CONSTRAINT events_id_not_null NOT NULL,
    title text CONSTRAINT events_title_not_null NOT NULL,
    start_time timestamptz CONSTRAINT events_start_time_not_null NOT NULL,
    end_time timestamptz NULL,
    "location" text NULL,
    notes text NULL,
    recorded_at timestamptz DEFAULT now() CONSTRAINT events_recorded_at_not_null NOT NULL,
    source_text text CONSTRAINT events_source_text_not_null NOT NULL,
    CONSTRAINT events_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_events_start_time ON public.events USING btree (start_time DESC);

CREATE TABLE public.transaction_types (
    id serial4 CONSTRAINT transaction_types_id_not_null NOT NULL,
    "type" text CONSTRAINT transaction_types_type_not_null NOT NULL,
    CONSTRAINT transaction_types_pkey PRIMARY KEY (id)
);

CREATE TABLE public.transactions (
    id bigserial CONSTRAINT transactions_id_not_null NOT NULL,
    amount numeric(14, 2) CONSTRAINT transactions_amount_not_null NOT NULL,
    "type" int4 DEFAULT 2 CONSTRAINT transactions_type_not_null NOT NULL,
    category_id int4 NULL,
    description text NULL,
    payment_method varchar(32) NULL,
    occurred_at timestamptz CONSTRAINT transactions_occurred_at_not_null NOT NULL,
    source_text text CONSTRAINT transactions_source_text_not_null NOT NULL,
    CONSTRAINT transactions_pkey PRIMARY KEY (id),
    CONSTRAINT transactions_category_id_fkey FOREIGN KEY (category_id)
        REFERENCES public.categories(id) ON DELETE SET NULL,
    CONSTRAINT transactions_type_fkey FOREIGN KEY ("type")
        REFERENCES public.transaction_types(id)
);

CREATE INDEX idx_transactions_category_time ON public.transactions USING btree (category_id, occurred_at DESC);
CREATE INDEX idx_transactions_localday ON public.transactions USING btree (((occurred_at AT TIME ZONE 'America/Sao_Paulo'::text)::date));
CREATE INDEX idx_transactions_occurred_at ON public.transactions USING btree (occurred_at DESC);

COMMIT;
