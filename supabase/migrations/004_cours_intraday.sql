-- Migration 004 — cours intrajournaliers pour les graphiques 1 jour / 1 semaine (D-12)
-- Additive et rejouable. Crée UNE nouvelle table (vide) : aucune table existante n'est modifiée.
-- NE PAS EXÉCUTER sans accord explicite du groupe (base partagée, CLAUDE.md §6.2).
-- Exécution : Supabase > SQL Editor > coller tout le fichier > Run.
--
-- Contenu : une bougie toutes les 5 minutes (yfinance) sur les 5 dernières séances.
-- L'actualisation remplace les bougies déjà connues et supprime celles de plus de 10 jours
-- (DELETE ... WHERE horodatage < limite, jamais sans condition) : la table reste petite
-- (environ 5 titres × 5 séances × 102 bougies = 2 550 lignes).

begin;

create table if not exists public.cours_intraday (
  id          bigserial primary key,
  action_id   uuid not null references public.actions(id) on delete cascade,
  horodatage  timestamptz not null,
  open        numeric(12,2),
  high        numeric(12,2),
  low         numeric(12,2),
  close       numeric(12,2) not null,
  volume      bigint,
  unique (action_id, horodatage)
);

create index if not exists idx_intraday_action_time
  on public.cours_intraday (action_id, horodatage desc);

-- Même protection que les 7 autres tables : seul le backend (service_role) y accède.
alter table public.cours_intraday enable row level security;

commit;
