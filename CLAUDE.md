# CLAUDE.md — Application d'aide à la décision : portefeuille actions de 500 000 €

> Ce fichier donne à Claude Code le contexte, les règles et la méthode du projet.
> À lire en entier avant toute action. À mettre à jour dès qu'une décision est validée.

---

## 0. Environnement : multi-plateforme, déploiement web

**L'application est un site web** : interface sur Vercel, API sur Render, base sur Supabase. Le client l'ouvre dans un navigateur, quel que soit son appareil ; il n'y a **aucun exécutable** à produire (D-04).
**Le développement se fait sous Windows, Linux ou macOS** : chaque commande, script et chemin doit fonctionner sur les trois.

| Règle | Détail |
|---|---|
| Terminal | PowerShell (Windows) ou bash / zsh (Linux, macOS). La documentation donne les deux variantes quand elles diffèrent. |
| Python | **3.11** sur tous les postes et sur Render (fichier `backend/.python-version`). `uv` est conseillé : il installe la bonne version sur les trois systèmes. |
| Environnement virtuel | `backend/.venv`, créé par `uv venv` (ou `py -3.11 -m venv .venv` sous Windows, `python3.11 -m venv .venv` ailleurs). |
| Variables d'environnement | Fichier `.env` lu par `python-dotenv` (backend) ; `.env.local` lu par Vite (frontend). Jamais de variable à exporter à la main pour lancer le projet. |
| Chemins | `pathlib.Path` en Python, jamais de chemin écrit en dur avec `/` ou `\`. Aucun chemin absolu dans le code. |
| Fins de ligne | `.gitattributes` fait foi (`* text=auto`, `*.sql` en LF). `git config core.autocrlf true` sous Windows, `input` ailleurs. |
| Scripts | Scripts utilitaires **uniquement en Python** (`python -m tools.xxx`), jamais en `.ps1` ni en `.sh` : un seul script pour tous les systèmes. |
| Encodage | Fichiers en UTF-8. Ouvrir les fichiers avec `encoding="utf-8"` en Python (la valeur par défaut de Windows n'est pas UTF-8). |
| Noms de fichiers | Pas d'accents ni d'espaces dans les noms de fichiers et de dossiers. Windows et macOS ne distinguent pas les majuscules : ne jamais avoir deux fichiers qui ne diffèrent que par la casse. |
| Node | Node 24 LTS (D-05) ; `npm`. |
| Supabase | Projet Supabase **en ligne et partagé par tout le groupe** (pas de Docker). Voir les règles du §6.2 avant toute action sur la base. |
| Ports | API sur `http://localhost:8000`, frontend Vite sur `http://localhost:5173`. |

### Commandes de référence

```bash
# Backend (depuis backend/)
uv venv --python 3.11                 # une seule fois
uv pip install -r requirements.txt
# activer : .venv\Scripts\Activate.ps1 (Windows) · source .venv/bin/activate (Linux, macOS)
python -m uvicorn main:app --reload --port 8000
python -m pytest
python -m tools.check_supabase       # connexion à la base, lecture seule
python -m tools.reset_portfolio      # remet le portefeuille à 500 000 € sans opération (confirmation RESET)

# Frontend (depuis frontend/)
npm install
npm run dev

# Rafraîchir les données de marché à la main
python -m tools.refresh               # ou le bouton « Actualiser les données »
```

**Actualisation planifiée** (18 h et chaque heure en séance) : un workflow **GitHub Actions** planifié appelle `POST /api/market/refresh` sur l'API déployée. En local, le bouton « Actualiser les données » ou `python -m tools.refresh` suffit.

**Render gratuit** s'endort après 15 min sans visite : la première requête peut prendre 30 à 60 s (ENF-02). À traiter avant la soutenance (réveil préalable ou offre payante).

---

## 1. Documents de référence (`docs/`)

Lire `docs/README.md` pour l'ordre de lecture.

| Réf. | Document | Ce qu'il fixe |
|---|---|---|
| [CdCF] | `docs/01_cahier_des_charges.md` (PDF : `docs/sources/01_cahier_des_charges_v2.pdf`) | Besoins, exigences EF / ENF, règles RG-01 à RG-06, recette REC-1 à REC-4 |
| [DCT] | `docs/02_dossier_conception.md` (original : `docs/sources/02_dossier_conception_v1.docx`) | Architecture, 7 tables (DDL), 5 services, 6 routes de l'API |
| [SPEC] | `docs/03_specification.md` (PDF avec schémas : `docs/sources/03_specification.pdf`) | Formules, seuils, algorithmes, UML, 16 cas de vérification, fonction SQL |
| [UI] | `docs/04_dossier_interface.md` (PDF avec schémas : `docs/sources/04_dossier_interface.pdf`) | Écrans, routes React, composants, connexions, interactions, charte |
| [CHARTE] | `docs/charte/` (`tokens.css`, `tokens.json`, `composants/*.md`) | Couleurs, typographie, espacements, règles des 8 composants |
| [MAQ] | `docs/maquettes/captures/*.png` et `docs/maquettes/sources/*.dc.html` | Mise en page exacte de chaque écran |

**Qui fait foi :**

- Architecture, tables, routes de l'API : **[DCT]**, complété par les ajustements du §9.
- Formules, seuils, algorithmes : **[SPEC]**.
- Pages, routes React, composants, navigation, interactions : **[UI]**. [UI] est plus récent que le DCT et la SPEC sur ce point : le simulateur est une **page à part** (`/simulateur`) et il y a une **page d'accueil**. Les mentions de `SimulatorPanel` intégré au tableau de bord dans le DCT et la SPEC sont **dépassées**.
- Apparence : **[CHARTE]**, puis [MAQ] pour la disposition.

En cas d'écart non listé au §9 : **signaler, ne pas trancher seul.**

- Chaque module, test et commit cite l'exigence qu'il sert (`RG-05`, `EF-02`, `REC-4`…).
- Documentation et échanges **en français**. Code, variables et messages de commit en anglais, **sauf les noms imposés par le DCT** (tables, colonnes, champs JSON en français : `cash_disponible`, `quantite_entiere`…). Textes affichés à l'utilisateur en français.

---

## 2. Contexte métier

| Élément | Valeur `[CdCF]` |
|---|---|
| Capital | **500 000 €**, portefeuille virtuel |
| Horizon | 1 an, nombreux allers-retours |
| Profil | Risque élevé ; objectif visé ~**+10 % par semaine** (jamais garanti) |
| Garde-fou | Perte max **10 % sur une semaine** (50 000 €) |
| Univers | DSY.PA (Dassault Systèmes), TTE.PA (TotalEnergies), CAP.PA (Capgemini), RMS.PA (Hermès), AI.PA (Air Liquide) |
| Posture | Le client ne voit jamais les formules ; il investit lui-même, guidé par des conseils argumentés |
| Hors périmètre | Ordres réels, fiscalité, levier, dérivés, crypto, modification des formules par le client |

---

## 3. Architecture `[DCT]` `[UI §2]`

```
React 18 + Vite (Vercel)  ──HTTPS JSON──►  FastAPI Python 3.11 (Render)  ──►  Supabase PostgreSQL 15
Tailwind, shadcn/ui,                         routers/ → services/ → db/          7 tables, JSONB
TradingView Lightweight Charts, Recharts     pandas, numpy, ta, Pydantic          fonction executer_transaction()
                                                 ▲
                           POST /api/market/refresh (planifié) : yfinance + RSS/NewsAPI + NLP
```

- **L'interface ne parle qu'à l'API.** Jamais d'appel direct à Supabase, yfinance ou NewsAPI depuis React.
- **Aucun appel externe** (yfinance, NewsAPI) pendant une action du client : tout est précalculé dans `scores_actions` (< 2 s, ENF-02).
- **Écritures en base uniquement par le backend.** Les clés restent dans `backend\.env`, jamais dans React ni dans git.
- CORS : seule l'origine Vercel (et `http://localhost:5173` en local) est autorisée.

### 3.1 Arborescence

```
backend\
├── main.py                    # FastAPI, CORS
├── config.py                  # POIDS, SEUILS, contrôle RG-04 au démarrage
├── db\       supabase_client.py · repository.py (seul accès à Supabase) · cached_repository.py (mémoire courte)
├── models\   schemas.py (validation des requêtes)
├── routers\  dashboard.py · simulator.py · transactions.py (+ historique) · stocks.py (+ refresh) · deps.py
├── services\ info_scoring.py · technical_scoring.py · ratio_scoring.py · randomness_service.py · decision_engine.py
│             sentiment.py · market_data.py · refresh_service.py · portfolio_service.py · common.py
├── tools\    refresh.py · stress_test.py · seed.py · check_supabase.py · reset_portfolio.py (D-23)
└── tests\
frontend\
└── src\
    ├── styles\tokens.css      # copie de docs\charte\tokens.css
    ├── api\client.js          # seul module qui appelle l'API (VITE_API_URL)
    ├── components\ui\         # Button, DecisionBadge, KpiCard, AlertBanner, AmountInput, StockCheckbox, ForecastBar, AdviceCard
    ├── components\layout\     # AppLayout, NavBar, Toast, LoadingState, ErrorState
    └── pages\                 # AccueilPage, DashboardPage, SimulatorPage, StockDetailPage, HistoryPage
supabase\
└── migrations\  001_init.sql (DDL du DCT) · 002_executer_transaction.sql · 003_ajustements.sql
docs\
```

### 3.2 Tables `[DCT §4]`

`actions`, `historique_cours`, `ratios_financiers`, `actualites`, `scores_actions`, `portefeuille`, `transactions`. Pas de table des positions : elles se déduisent de `transactions` (SPEC §10.2).

### 3.3 Routes de l'API `[DCT §6]` `[UI §6.1]`

| Route | Rôle | Appelée par | Exigences |
|---|---|---|---|
| `GET /api/dashboard` | Capital, cash, variation hebdo, niveau d'alerte, 5 actions | Accueil, Tableau de bord, en-tête du Simulateur, NavBar, AlertBanner | EF-01, RG-01 |
| `POST /api/simulate` | Conseil sur une opération, **sans écriture** | Simulateur | EF-02, RG-03, RG-05, ENF-02 |
| `POST /api/transactions` | Enregistre une opération validée (via `executer_transaction`) | Fenêtre de confirmation | EF-02, RG-05 |
| `GET /api/stocks/{ticker}` | Fiche action + onglet Infos (un seul appel pour les deux onglets) | Fiche action | EF-03 |
| `GET /api/portfolio/history` | Historique 1 an, paginé, filtrable | Historique | RG-06 |
| `POST /api/market/refresh` | Collecte + recalcul de `scores_actions` | Bouton Actualiser, GitHub Actions planifié | ENF-02 |

Codes : `400` règle de gestion violée (cash insuffisant, vente > position, conseil expiré), `404` ticker inconnu, `422` entrée invalide. Contrats JSON : SPEC Annexe A.

### 3.4 Pages et navigation `[UI §3–§5]` `[MAQ]`

| Page | Route React | Maquette |
|---|---|---|
| `AccueilPage` | `/` | `01_accueil.png` |
| `DashboardPage` | `/tableau-de-bord` | `02_tableau_de_bord.png`, `05_tableau_de_bord_alerte.png` |
| `SimulatorPage` (+ `ConfirmDialog`) | `/simulateur` | `03_simulateur.png`, `04_confirmation.png` |
| `StockDetailPage` (onglets Graphique / Infos) | `/action/:ticker` | `06_fiche_action_graphique.png`, `07_fiche_action_infos.png` |
| `HistoryPage` | `/historique` | `08_historique.png` |

- `NavBar` sur toutes les pages : 5 onglets (Accueil, Tableau de bord, Simulateur, Actions, Historique), date des données, bouton « Actualiser les données ».
- `AlertBanner` sous la NavBar, sur toutes les pages, dès que le niveau d'alerte n'est pas `AUCUN`.
- **Seul chemin d'écriture** : Simulateur → Simuler → Valider → ConfirmDialog → `POST /api/transactions` → retour au tableau de bord. Les parcours détaillés sont dans [UI §5].

### 3.5 Charte graphique `[CHARTE]`

- Importer `src\styles\tokens.css` (copie de `docs\charte\tokens.css`) et brancher les variables dans `tailwind.config.js` comme indiqué dans [UI §8.1].
- **Aucune couleur en dur** dans les composants : toujours une variable (`var(--buy)`) ou une classe Tailwind reliée à une variable (`bg-buy-soft`).
- Polices : Inter (interface) et IBM Plex Mono (codes boursiers), chiffres tabulaires dans les tableaux et cartes.
- Les 8 composants de `components\ui\` suivent les règles de `docs\charte\composants\*.md`. `docs\charte\bundle.js` et `bundle.css` sont une implémentation de **référence** : les réécrire en composants React + Tailwind, ne pas les importer.
- Formats français : `Intl.NumberFormat('fr-FR')`, signe moins `−`, `+` toujours affiché sur les variations (voir [CHARTE] README §2).
- Un conseil s'affiche toujours avec son mot et son signe : ▲ ACHAT, ▼ VENTE, ■ RIEN.

---

## 4. Règles de calcul `[SPEC]` — résumé

| Élément | Règle | SPEC |
|---|---|---|
| Échelle | Signaux de critère entre −1 et +1 ; notes de pilier et finale **sur 100** ; `note = 50 + 50 × signal`, 50 = neutre | §1.2 |
| Technique | MM20/50/200, tendance 20 j, MACD 12/26/9, Bollinger 20/2, RSI 14 ; importances 9 (Bollinger) / 7 (RSI) / 6 (MACD) / 5 (MM) / 5 (tendance). Indicateurs **calculés par nous** avec `ta` à partir des cours yfinance | §3 |
| Informations | `note d'impact = 50 + 50 × s × importance` (1 annonce, 0,5 sinon) ; demi-vie 2 j, fenêtre 7 j ; aucun article → 50 | §4 |
| Ratios | CA, dividende par action, rendement ; importances 7/6/6 ; dividende estimé = actions × dividende attendu | §5 |
| Hasard | note = 100 × u, graine = SHA-256(ticker + semaine ISO), enregistrée ; influence ≤ 5 points | §6 |
| Poids | Infos **40 %**, Graphique 25 %, Ratios 25 %, Hasard 10 % ; **RG-04 vérifié au démarrage** | §7.1 |
| Décision | note finale `≥ 60` → ACHAT ; `≤ 40` → VENTE ; sinon RIEN (réglables par `SEUIL_ACHAT` / `SEUIL_VENTE` ; essai 55 / 45 en ligne, D-10) | §7.2 |
| Raisons | 2 à 4 phrases claires, une par pilier important + point de vigilance ; hasard jamais cité | §8 |
| Prévision | central = μ + (note − 50) / 50 × σ ; favorable / défavorable = central ± σ (52 semaines) | §9 |
| Simulateur | `q = floor(M / P)`, reste en cash ; pas de frais ; champ `verdict` en plus de `conseil` | §10 |
| Garde-fou | `variation = V / val_semaine_prec − 1` ; APPROCHE ≤ −7 %, ATTEINT ≤ −10 % ; remise à zéro chaque lundi | §11.2 |

Toutes les valeurs numériques viennent de `config.py`, jamais en dur dans les services.

---

## 5. Règles non négociables

### Exactitude
- Aucune donnée postérieure à `date_calcul` dans un calcul (test dédié par service).
- Quantités **toujours entières** ; cash **jamais négatif** ; jamais de vente supérieure à la position (RG-05).
- Montants en `Decimal` (Python) / `NUMERIC` (SQL), jamais en `float`.
- **Toute écriture de transaction passe par `executer_transaction()`** (une seule requête `rpc`, code en SPEC Annexe A.3) : jamais d'insertion + mise à jour du cash en deux appels séparés.

### Honnêteté (ENF-03)
- Avertissement « Les conseils sont une aide à la décision, ils ne garantissent pas le succès : vous restez seul décideur. » en pied de page de **toutes** les pages (`AppLayout`, D-25 ; remplace la mention « outil d'aide à la décision… »).
- L'objectif de ~10 % par semaine est **visé**, jamais promis.
- Donnée manquante : l'interface le dit, le calcul ne l'invente pas.

### Lisibilité (ENF-01, RG-03)
- Le client ne voit jamais un indicateur brut seul (« MACD = −0,42 ») : toujours une phrase claire (SPEC §8.2).
- Aucune recommandation sans raisons.

### Qualité
- Couverture de tests ≥ 70 % ; les **16 cas de vérification de la SPEC §12.1 (V1 à V16)** sont des tests pytest obligatoires.
- Même données + même config + même semaine = même résultat.

---

## 6. Git, Supabase et secrets

### 6.1 Git

- **Ne jamais committer ni pousser sur `main`.** Une branche par étape : `feat/db-migrations`, `feat/data-refresh`, `feat/scoring-services`, `feat/api-routes`, `feat/frontend-shell`, `feat/page-<nom>`… Fusion par **Pull Request** relue par un membre du groupe.
- Avant de créer une branche : `git pull origin main`.
- Commits courts et ciblés, en anglais, avec l'exigence : `feat(RG-05): integer share quantity in simulator`, `fix(EF-02): …`, `test(REC-4): …`.
- `git status` avant chaque commit : **aucun `.env`**, aucun fichier de `node_modules\`, `.venv\`, `dist\`, `__pycache__\`.
- Ne jamais réécrire l'historique partagé (`push --force`, `rebase` d'une branche déjà poussée) sans accord explicite.

### 6.2 Supabase (projet partagé)

- La base est **commune à tout le groupe** : une erreur casse le travail des autres.
- Toute modification de structure passe par un **fichier de migration numéroté** dans `supabase\migrations\`. **Montrer le SQL et attendre l'accord explicite** avant de l'exécuter.
- **Interdit sans accord explicite** : `DROP`, `TRUNCATE`, `DELETE` sans `WHERE`, `ALTER` sur une table qui contient des données.
- Les données de test sont insérées par `tools\seed.py`, qui doit pouvoir être relancé sans créer de doublons.
- Clés : `SUPABASE_URL` + clé **`service_role`** (variable `SUPABASE_KEY`, nom repris du squelette de l'équipe) uniquement dans `backend\.env`. La clé `service_role` ne va **jamais** dans le frontend, dans un log ou dans git. Le frontend n'a besoin d'aucune clé Supabase.
- Activer la sécurité par ligne (RLS) sur les 7 tables, sans politique publique : seul le backend (`service_role`) y accède.

### 6.3 Fichiers de configuration

- `.gitignore` et `.gitattributes` à la racine (déjà fournis).
- `backend\.env.example` et `frontend\.env.example` versionnés, **sans valeurs réelles**.

---

## 7. Tests de recette

| Test | Vérifie |
|---|---|
| `test_rec1_five_stocks_have_decision_forecast_dividend` | REC-1, RG-02 |
| `test_rec2_simulate_then_record_round_trip` | REC-2, EF-02, ENF-02 (< 2 s) |
| `test_rec3_every_buy_has_reasons_and_info_tab` | REC-3, RG-03 |
| `test_rec4_guard_triggers_at_minus_10pct` | REC-4, RG-01 (via `tools\stress_test.py`) |
| `test_rg04_info_weight_strictly_highest` | RG-04 |
| `test_rg05_dct_example_1436_shares` | 50 000 € à 34,80 € → 1 436 actions, reste 27,20 € |
| `test_transactions_atomic_on_insufficient_cash` | 400, rien n'est écrit |
| `test_v01` … `test_v16` | SPEC §12.1 |

---

## 8. Livrables

| # | Livrable | État |
|---|---|---|
| 1 | Cahier des charges | Fait (v2.0) |
| 2 | Dossier de conception | Fait (v1.0) — ajustements au §9 |
| 3 | Dossier de spécification + dossier interface + charte + maquettes | Fait |
| 4 | Application | **Prototype complet** (backend, API, interface, déploiement prêt) — guide : `docs/05_guide_du_code.md` |

Ne pas coder une partie dont la formule n'est pas dans la SPEC, ni un écran qui n'est pas dans [UI] / [MAQ].

---

## 9. Écarts à intégrer

### Base de données (migration `003_ajustements.sql`)
- [x] Ajouter `resume TEXT` à `actualites` (déjà présent dans la base).
- [ ] Ajouter `nom_client TEXT` à `portefeuille` (affiché sur l'Accueil) — migration `003`, en attente d'accord.
- [x] Créer la fonction `executer_transaction()` (SPEC Annexe A.3) — déjà présente dans la base.
- [x] Charger au moins 1 an d'historique (2 ans recommandés) au premier refresh (MM200, 52 semaines).

### API
- [x] Ajouter `verdict` et `niveau_alerte` à la réponse de `/api/simulate`, et `niveau_alerte` + horodatage des données à `/api/dashboard`.

### Interface (par rapport au DCT §7)
- [x] Nouvelle page `AccueilPage` sur `/`.
- [x] `DashboardPage` déplacée sur `/tableau-de-bord`, **sans** simulateur.
- [x] `SimulatorPage` sur `/simulateur` (remplace `SimulatorPanel` intégré au tableau de bord ; `SimulatorPanel` devient son formulaire).
- Pages du squelette de l'équipe conservées (`DashboardPage`, `StockDetailPage`, `HistoryPage`, `SimulatorPanel`) ; `AccueilPage` et `SimulatorPage` ajoutées en plus (voir `docs/decisions.md`).
- [x] `NavBar` à 5 onglets + bouton Actualiser.

## 10. Questions ouvertes

- [ ] Seuils de décision 60 / 40 et seuil d'alerte −7 % : validés ?
- [ ] Bollinger et RSI : lecture « retour à la moyenne » ?
- [ ] Plusieurs titres cochés : montant appliqué à chacun ou réparti ?
- [ ] Importance des actualités (1 / 0,5), demi-vie de 2 jours : à confirmer après un premier test.
- [x] Nom de l'application : **PrimeInvest** (D-14). Logo : « Prisme » (D-21), composant `layout/Logo.jsx`.

---

## 11. Méthode de travail

### Ordre de développement conseillé

1. **Socle** : structure des dossiers, `requirements.txt`, projet Vite, `.env.example`, lancement à vide du backend et du frontend.
2. **Base** : migrations `001` à `003` (SQL montré et validé avant exécution), `tools\seed.py` (5 actions, portefeuille de 500 000 €).
3. **Collecte** : `POST /api/market/refresh` (yfinance, RSS / NewsAPI), historique d'au moins 1 an.
4. **Calculs** : les 5 services + `DecisionEngine`, avec les tests V1 à V16.
5. **API** : les 6 routes et leurs contrats JSON.
6. **Interface** : `tokens.css` + Tailwind, les 8 composants de la charte, `NavBar` / `AlertBanner`, puis les pages dans l'ordre Tableau de bord → Simulateur (+ confirmation) → Fiche action → Historique → Accueil.
7. **Recette** : REC-1 à REC-4, actualisation planifiée (GitHub Actions), déploiement (Vercel, Render).

### À chaque session

1. Relire ce fichier, puis `docs/decisions.md` (le créer s'il n'existe pas ; y noter chaque décision prise).
2. **Proposer un plan avant de coder** et attendre la validation pour toute étape importante.
3. Travailler une étape à la fois, sur sa branche ; lancer les tests ; expliquer ce qui a été fait.
4. Vérifier que les commandes proposées fonctionnent **sous Windows (PowerShell) comme sous Linux / macOS**.
5. Rattacher tout travail à une exigence et à une section de la SPEC ou de [UI].
6. Lancer `python -m pytest` avant tout commit sur `services\` ou `routers\` ; `npm run build` avant tout commit sur `frontend\`.
7. En fin de tâche : ce qui a été fait, ce qui reste, les questions pour le groupe.
