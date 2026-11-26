-- Migration 005 — profil de risque du client (onglet Profil, D-17)
-- Ajoute UNE colonne facultative à portefeuille (1 ligne existante, laissée vide = réglage par défaut).
-- Additive et rejouable. NE PAS EXÉCUTER sans accord explicite (base partagée, CLAUDE.md §6.2).
-- Exécution : Supabase > SQL Editor > coller tout le fichier > Run.

begin;

alter table public.portefeuille
  add column if not exists profil_risque text;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'portefeuille_profil_risque_check') then
    alter table public.portefeuille
      add constraint portefeuille_profil_risque_check
      check (profil_risque is null or profil_risque in ('prudent', 'equilibre', 'dynamique'));
  end if;
end $$;

commit;
