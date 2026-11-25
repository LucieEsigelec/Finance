# Journal des décisions

Chaque décision validée est notée ici avec sa date, ce qui a été décidé et pourquoi. Voir CLAUDE.md §11.

| # | Date | Décision | Raison | Impact |
|---|---|---|---|---|
| D-01 | 2026-11-25 | Les noms du squelette de l'équipe (dépôt `LucieEsigelec/Finance`, commit `7e62087`) sont conservés : variable `SUPABASE_KEY` pour la clé `service_role` (et non `SUPABASE_SERVICE_ROLE_KEY`). | Le squelette existait déjà ; le DCT §9.2 utilise aussi `SUPABASE_KEY`. | `backend/.env.example`, CLAUDE.md §6.2 |
| D-02 | 2026-11-25 | Les pages du squelette sont conservées (`DashboardPage`, `StockDetailPage`, `HistoryPage`, `SimulatorPanel`) ; on ajoute `AccueilPage` (`/`) et `SimulatorPage` (`/simulateur`) prévues par [UI]. | Ne pas casser le travail de l'équipe tout en suivant le dossier interface. | CLAUDE.md §9 ; rôle exact de `SimulatorPanel` dans `SimulatorPage` à préciser à l'étape interface |

## À trancher

- Fichiers SQL : `supabase/schema.sql` + `seed.sql` (squelette) ou `supabase/migrations/001…003` + `tools/seed.py` (CLAUDE.md) ?
- Versions frontend : React 19 / Vite 8 (squelette) ou React 18 + Tailwind + shadcn/ui (docs) ?
- Onglet « Actions » de la NavBar : quelle page ouvre-t-il (la maquette ouvre la fiche DSY.PA) ?
