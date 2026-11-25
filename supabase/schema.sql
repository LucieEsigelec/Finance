-- Schéma de la base Supabase — Portefeuille 500k (DCT §4, SPEC A.3)
-- Reconstitué le 2026-11-25 à partir de la base en ligne (supabase/verifier_schema.sql + API REST).
-- Sert à RECRÉER la base à l'identique sur un projet VIDE. Ne pas exécuter sur la base partagée :
-- les tables y existent déjà. Les évolutions passent par supabase/migrations/ (003 et suivantes).
-- Point non vérifiable à distance : les colonnes id BIGINT ont été écrites en BIGSERIAL (DCT).

-- 1. Référentiel des 5 actions
create table actions (
  id               uuid primary key default gen_random_uuid(),
  ticker           varchar(16)  not null unique,
  nom              varchar(100) not null,
  secteur          varchar(80)  not null,
  dernier_cours    numeric(12,2) not null default 0,
  dividende_estime numeric(10,2) not null default 0,
  maj_le           timestamptz  not null default now()
);

-- 2. Historique des cours (OHLCV)
create table historique_cours (
  id          bigserial primary key,
  action_id   uuid not null references actions(id) on delete cascade,
  date_seance date not null,
  open        numeric(12,2),
  high        numeric(12,2),
  low         numeric(12,2),
  close       numeric(12,2) not null,
  volume      bigint,
  unique (action_id, date_seance)
);

-- 3. Ratios financiers
create table ratios_financiers (
  id                   bigserial primary key,
  action_id            uuid not null references actions(id) on delete cascade,
  date_maj             date not null,
  chiffre_affaires     numeric(18,2),
  dividende_par_action numeric(10,2),
  rendement_pct        numeric(6,2)
);

-- 4. Actualités (pilier Informations, onglet Infos)
create table actualites (
  id           uuid primary key default gen_random_uuid(),
  action_id    uuid not null references actions(id) on delete cascade,
  date_pub     timestamptz not null,
  titre        text not null,
  source       varchar(100),
  url          text,
  resume       text,
  score_impact numeric(5,2) not null check (score_impact >= 0 and score_impact <= 100)
);

-- 5. Scores pré-calculés
create table scores_actions (
  id                    uuid primary key default gen_random_uuid(),
  action_id             uuid not null references actions(id) on delete cascade,
  date_calcul           timestamptz not null default now(),
  score_global          numeric(5,2) not null check (score_global >= 0 and score_global <= 100),
  decision              varchar(10) not null check (decision in ('ACHAT', 'VENTE', 'RIEN')),
  prevision_semaine_pct numeric(6,2),
  details_piliers       jsonb not null
);

-- 6. Portefeuille
create table portefeuille (
  id               uuid primary key default gen_random_uuid(),
  capital_initial  numeric(14,2) not null default 500000.00,
  cash_disponible  numeric(14,2) not null default 500000.00 check (cash_disponible >= 0),
  val_semaine_prec numeric(14,2) not null default 500000.00,
  date_ref_semaine date not null default current_date
);

-- 7. Transactions (RG-05 : quantités entières)
create table transactions (
  id               uuid primary key default gen_random_uuid(),
  portefeuille_id  uuid not null references portefeuille(id) on delete cascade,
  action_id        uuid not null references actions(id) on delete restrict,
  type_op          varchar(10) not null check (type_op in ('ACHAT', 'VENTE')),
  quantite_entiere integer not null check (quantite_entiere > 0),
  prix_unitaire    numeric(12,2) not null,
  montant_total    numeric(14,2) not null,
  conseil_algo     jsonb not null,
  date_execution   timestamptz not null default now()
);

-- Index
create index idx_hist_action_date   on historique_cours (action_id, date_seance desc);
create index idx_news_action_date   on actualites (action_id, date_pub desc);
create index idx_ratios_action_date on ratios_financiers (action_id, date_maj desc);
create index idx_scores_action_date on scores_actions (action_id, date_calcul desc);
create index idx_tx_pf_date         on transactions (portefeuille_id, date_execution desc);

-- Sécurité par ligne : activée, aucune politique => seul service_role (backend) accède (CLAUDE.md §6.2)
alter table actions           enable row level security;
alter table historique_cours  enable row level security;
alter table ratios_financiers enable row level security;
alter table actualites        enable row level security;
alter table scores_actions    enable row level security;
alter table portefeuille      enable row level security;
alter table transactions      enable row level security;

-- Enregistrement atomique d'une opération (SPEC A.3, RG-05)
create or replace function public.executer_transaction(
  p_portefeuille uuid, p_action uuid, p_type text, p_qte integer, p_conseil jsonb)
returns transactions
language plpgsql
as $function$
declare
    v_prix numeric(12, 2);
    v_cash numeric(14, 2);
    v_detenu int;
    v_tx transactions;
begin
    if p_type not in ('ACHAT', 'VENTE') then
        raise exception 'TYPE_OPERATION_INVALIDE';
    end if;

    if p_qte <= 0 then
        raise exception 'QUANTITE_INVALIDE';
    end if;

    -- Verrouillage exclusif de la ligne portefeuille pendant la transaction
    select cash_disponible into v_cash
    from portefeuille
    where id = p_portefeuille
    for update;

    if not found then
        raise exception 'PORTEFEUILLE_INTROUVABLE';
    end if;

    -- Lecture du dernier cours connu
    select dernier_cours into v_prix
    from actions
    where id = p_action;

    if not found then
        raise exception 'ACTION_INTROUVABLE';
    end if;

    -- Position actuelle détenue sur ce titre
    select coalesce(
        sum(case when type_op = 'ACHAT' then quantite_entiere else -quantite_entiere end),
        0)
    into v_detenu
    from transactions
    where portefeuille_id = p_portefeuille and action_id = p_action;

    -- Contrôles métier (RG-05)
    if p_type = 'ACHAT' and (p_qte * v_prix) > v_cash then
        raise exception 'RG05_CASH_INSUFFISANT';
    end if;

    if p_type = 'VENTE' and p_qte > v_detenu then
        raise exception 'VENTE_SUPERIEURE_A_LA_POSITION';
    end if;

    insert into transactions (
        portefeuille_id, action_id, type_op,
        quantite_entiere, prix_unitaire, montant_total, conseil_algo)
    values (
        p_portefeuille, p_action, p_type,
        p_qte, v_prix, p_qte * v_prix, p_conseil)
    returning * into v_tx;

    -- Mise à jour atomique du cash disponible
    update portefeuille
    set cash_disponible = cash_disponible
        + (case when p_type = 'ACHAT' then -1 else 1 end) * (p_qte * v_prix)
    where id = p_portefeuille;

    return v_tx;
end;
$function$;

-- Puis appliquer supabase/migrations/003_ajustements.sql (nom_client, contraintes, droits).
