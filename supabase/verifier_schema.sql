-- Vérification du schéma Supabase — LECTURE SEULE (aucune modification).
-- À coller dans Supabase > SQL Editor > Run. Une seule requête : copier tout le tableau résultat.
-- Contrôle ce que l'API REST ne montre pas : contraintes CHECK / UNIQUE, index,
-- précision des NUMERIC, RLS et code de executer_transaction (DCT §4, SPEC A.3, CLAUDE.md §6.2).

with tables as (
  select unnest(array['actions','historique_cours','ratios_financiers','actualites',
                      'scores_actions','portefeuille','transactions']) as t
)
select '1_colonne' as rubrique, c.table_name as objet,
       c.column_name || ' ' || c.data_type
       || coalesce('(' || c.numeric_precision || ',' || c.numeric_scale || ')', '')
       || coalesce('(' || c.character_maximum_length || ')', '') as detail
from information_schema.columns c
join tables on tables.t = c.table_name
where c.table_schema = 'public' and c.data_type in ('numeric', 'character varying')

union all
select '2_contrainte', rel.relname, con.conname || ' : ' || pg_get_constraintdef(con.oid)
from pg_constraint con
join pg_class rel on rel.oid = con.conrelid
join pg_namespace n on n.oid = rel.relnamespace
join tables on tables.t = rel.relname
where n.nspname = 'public' and con.contype in ('c', 'u', 'f')

union all
select '3_index', i.tablename, i.indexdef
from pg_indexes i
join tables on tables.t = i.tablename
where i.schemaname = 'public'

union all
select '4_rls', c.relname,
       'rls=' || c.relrowsecurity || ' force=' || c.relforcerowsecurity
       || ' politiques=' || (select count(*) from pg_policies p
                             where p.schemaname = 'public' and p.tablename = c.relname)
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
join tables on tables.t = c.relname
where n.nspname = 'public'

union all
select '5_politique', p.tablename, p.policyname || ' roles=' || p.roles::text || ' cmd=' || p.cmd
from pg_policies p
join tables on tables.t = p.tablename
where p.schemaname = 'public'

union all
select '6_fonction', p.proname, pg_get_functiondef(p.oid)
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public' and p.proname in ('executer_transaction', 'rls_auto_enable')

union all
select '7_droits_fonction', p.proname, coalesce(array_to_string(p.proacl, ' '), 'droits par défaut (PUBLIC)')
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public' and p.proname in ('executer_transaction', 'rls_auto_enable')

order by 1, 2, 3;
