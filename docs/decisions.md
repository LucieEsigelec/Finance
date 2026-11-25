# Journal des décisions

Chaque décision validée est notée ici avec sa date, ce qui a été décidé et pourquoi. Voir CLAUDE.md §11.

| # | Date | Décision | Raison | Impact |
|---|---|---|---|---|
| D-01 | 2026-11-25 | Les noms du squelette de l'équipe (dépôt `LucieEsigelec/Finance`, commit `7e62087`) sont conservés : variable `SUPABASE_KEY` pour la clé `service_role` (et non `SUPABASE_SERVICE_ROLE_KEY`). | Le squelette existait déjà ; le DCT §9.2 utilise aussi `SUPABASE_KEY`. | `backend/.env.example`, CLAUDE.md §6.2 |
| D-02 | 2026-11-25 | Les pages du squelette sont conservées (`DashboardPage`, `StockDetailPage`, `HistoryPage`, `SimulatorPanel`) ; on ajoute `AccueilPage` (`/`) et `SimulatorPage` (`/simulateur`) prévues par [UI]. | Ne pas casser le travail de l'équipe tout en suivant le dossier interface. | CLAUDE.md §9 ; rôle exact de `SimulatorPanel` dans `SimulatorPage` à préciser à l'étape interface |
| D-03 | 2026-11-25 | La base en ligne (créée à la main) est conservée : elle est conforme au DCT et à SPEC A.3. `supabase/schema.sql` et `seed.sql` sont ceux de Lucie (commit `a649da2`, script d'origine de la base) ; la sécurité par ligne, absente de ce script, est ajoutée par la migration 003 ; les évolutions passent par `supabase/migrations/003_ajustements.sql` et suivantes. Proposition, en attente de relecture par la PR. | Pas de recréation : on ne casse pas la base partagée. | `supabase/` |
| D-04 | 2026-11-25 | Application livrée comme **site web** (Vercel + Render + Supabase), pas d'exécutable. Développement multi-plateforme (Windows, Linux, macOS) ; scripts en Python uniquement ; actualisation planifiée par GitHub Actions au lieu du Planificateur Windows. | Utilisable sur tout appareil sans installation ; l'équipe ne travaille pas que sous Windows. | CLAUDE.md §0, §3.1, §11 ; README |

## À trancher

- Versions frontend : React 19 / Vite 8 (squelette) ou React 18 + Tailwind + shadcn/ui (docs) ?
- Onglet « Actions » de la NavBar : quelle page ouvre-t-il (la maquette ouvre la fiche DSY.PA) ?
