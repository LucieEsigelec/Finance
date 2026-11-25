-- Migration 003 — ajustements du schéma existant (CLAUDE.md §9, DCT §4, SPEC A.3)
-- Additive et rejouable : peut être relancée sans erreur ni doublon.
-- NE PAS EXÉCUTER sans accord explicite du groupe (base partagée, CLAUDE.md §6.2).
-- Exécution : Supabase > SQL Editor > coller tout le fichier > Run.

begin;

-- 1. Nom du client affiché sur l'Accueil (UI §4.2, CLAUDE.md §9).
--    ALTER sur une table qui contient 1 ligne : ajout d'une colonne nullable, aucune donnée modifiée.
alter table public.portefeuille
  add column if not exists nom_client text;

-- 2. Un cours nul ou négatif rendrait un achat gratuit dans executer_transaction (RG-05).
--    Les 5 lignes actuelles ont toutes un cours > 0 : la contrainte est valide immédiatement.
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'actions_dernier_cours_positif') then
    alter table public.actions
      add constraint actions_dernier_cours_positif check (dernier_cours > 0);
  end if;
end $$;

-- 3. Éviter les doublons quand l'actualisation est relancée (ENF-02, seed rejouable §6.2).
--    Tables vides aujourd'hui.
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'ratios_financiers_action_date_key') then
    alter table public.ratios_financiers
      add constraint ratios_financiers_action_date_key unique (action_id, date_maj);
  end if;
  -- url peut être NULL : plusieurs articles sans url restent possibles.
  if not exists (select 1 from pg_constraint where conname = 'actualites_action_url_key') then
    alter table public.actualites
      add constraint actualites_action_url_key unique (action_id, url);
  end if;
end $$;

-- 4. Seul le backend (service_role) peut enregistrer une opération.
--    Aujourd'hui executer_transaction est exécutable par PUBLIC, anon et authenticated.
revoke execute on function public.executer_transaction(uuid, uuid, text, integer, jsonb)
  from public, anon, authenticated;
grant execute on function public.executer_transaction(uuid, uuid, text, integer, jsonb)
  to service_role;

-- 5. Sécurité par ligne sur les 7 tables, sans politique publique (CLAUDE.md §6.2).
--    Déjà active dans la base (activée automatiquement par Supabase) : ces lignes ne changent
--    rien ici, mais garantissent la même protection si la base est recréée avec schema.sql.
alter table public.actions           enable row level security;
alter table public.historique_cours  enable row level security;
alter table public.ratios_financiers enable row level security;
alter table public.actualites        enable row level security;
alter table public.scores_actions    enable row level security;
alter table public.portefeuille      enable row level security;
alter table public.transactions      enable row level security;

commit;
