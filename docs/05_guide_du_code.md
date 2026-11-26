# Guide du code — PrimeInvest

Ce guide explique **simplement** comment le code est organisé et comment il fonctionne. Il est complété à chaque étape du développement. Pour les règles du projet, voir `CLAUDE.md` ; pour les formules exactes, la spécification (`docs/03_specification.md`).

## 1. Vue d'ensemble

L'application a trois morceaux qui se parlent dans un seul sens :

```
Navigateur (React)  ──►  API (FastAPI, Python)  ──►  Base de données (Supabase)
                               ▲
              Actualisation : cours (yfinance) + actualités (RSS, NewsAPI)
```

- **La base** garde tout : les 5 actions, leurs cours, les actualités, les notes calculées, le portefeuille et les opérations.
- **L'API** fait tous les calculs et est la seule à lire ou écrire dans la base.
- **L'interface** affiche ce que l'API lui donne. Elle ne calcule rien d'important.

Les calculs lourds (indicateurs, notes) sont faits **à l'avance**, lors d'une « actualisation » (bouton ou tâche planifiée). Quand le client clique, l'API ne fait que relire ces résultats : c'est pour ça que la réponse arrive en moins de 2 secondes.

## 2. Le socle du backend (`backend/`)

| Fichier | À quoi il sert, en une phrase |
|---|---|
| `config.py` | Tous les réglages (poids, seuils, durées) sont ici ; il vérifie au démarrage que le pilier Informations pèse le plus (RG-04). |
| `main.py` | Crée l'API, autorise seulement le site de l'application à l'appeler (CORS), et contient la route `/api/health`. |
| `db/supabase_client.py` | Ouvre la connexion à la base une seule fois et la réutilise. |
| `tools/check_supabase.py` | Petit outil pour vérifier qu'on arrive à lire la base. |

**Pourquoi tout mettre dans `config.py` ?** Si le client veut changer un seuil (par exemple acheter à 65 au lieu de 60), on change une seule ligne, sans toucher aux calculs.

**Les seuils de conseil** (60 / 40 dans la SPEC) peuvent être changés sans toucher au code ; le conseil est recalculé à chaque affichage à partir de la note enregistrée (`rederive_advice`), donc un nouveau seuil s'applique tout de suite, par les variables `SEUIL_ACHAT` et `SEUIL_VENTE` (dans `backend/.env` ou sur Render). Le site en ligne fait un essai à 55 / 45 (décision D-10). Un seuil invalide (par exemple un achat sous 50) empêche l'API de démarrer.

**Le contrôle RG-04.** Au chargement, `check_rg04` regarde les 4 poids. Si celui des Informations n'est pas strictement le plus grand, ou si les poids ne font pas 100 %, une erreur est levée et l'API ne démarre pas (cas V8).

## 3. Les calculs (`backend/services/`)

Chaque pilier donne une **note sur 100** (50 = neutre). Pour y arriver, chaque indicateur donne d'abord un **signal entre −1 et +1**, puis on applique toujours la même formule : `note = 50 + 50 × signal` (`services/common.py`).

### 3.1 Analyse graphique — `technical_scoring.py`

On part des cours de clôture et on calcule 5 indicateurs avec la bibliothèque `ta` :

| Indicateur | Question posée | Signal +1 | Signal −1 |
|---|---|---|---|
| Bollinger (importance 9) | Le cours est-il en bas ou en haut de son « couloir » habituel ? | en bas | en haut |
| RSI (7) | Le titre a-t-il trop baissé ou trop monté ces 14 jours ? | RSI ≤ 30 | RSI ≥ 70 |
| MACD (6) | La moyenne courte vient-elle de passer au-dessus de la longue ? | croisement à la hausse | croisement à la baisse |
| Moyennes mobiles (5) | Le cours est-il au-dessus de ses moyennes 20 / 50 / 200 jours ? | au-dessus | en dessous |
| Tendance (5) | Le cours monte-t-il depuis un mois ? | +3 %/semaine | −3 %/semaine |

La note du pilier est la moyenne des 5 signaux, pondérée par leur importance. Si un indicateur ne peut pas être calculé (pas assez d'historique), on l'ignore.

**Détail important :** le service ne regarde **jamais** un cours postérieur à la date de calcul (un test le vérifie en ajoutant de faux cours « futurs »).

### 3.2 Informations — `info_scoring.py` et `sentiment.py`

1. Chaque article reçoit une note d'impact quand il est collecté. **Un modèle de langue, Claude Haiku 5.5** (`news_nlp.py`), lit le titre et le résumé de chaque nouvel article et dit : quel est l'effet probable pour l'actionnaire (sentiment entre −1 et +1, en comprenant le contexte : « baisse des coûts » est une bonne nouvelle), est-ce une **annonce officielle** de l'entreprise (elle compte double), et l'article parle-t-il vraiment de l'entreprise (sinon il est écarté). Les articles d'une même action partent en un seul appel, avec une réponse au format JSON imposé. Si le modèle n'est pas disponible (pas de clé `ANTHROPIC_API_KEY`, coupure, refus), on revient à l'ancienne méthode, `sentiment.py`, qui compte des mots positifs et négatifs.
2. Un article **perd la moitié de son poids tous les 2 jours** et est ignoré après 7 jours.
3. La note du pilier est la moyenne des notes d'impact, pondérée par ces poids.
4. Les 3 articles qui pèsent le plus servent à expliquer le conseil.

Sans article récent, la note vaut 50 et l'application affiche « aucune actualité récente ».

### 3.3 Ratios financiers — `ratio_scoring.py`

Trois questions sur les deux derniers exercices : le chiffre d'affaires progresse-t-il ? le dividende augmente-t-il ? le rendement est-il meilleur que la moyenne des 5 titres ? Le module calcule aussi le **dividende estimé** : nombre d'actions × dividende par action (en `Decimal`, au centime près).

### 3.4 Hasard — `randomness_service.py`

Un nombre entre 0 et 100, tiré à partir d'une « graine » fabriquée avec le titre et la semaine (par exemple `DSY.PA2026-W48`). Même titre + même semaine = même nombre : le conseil ne change pas à chaque clic, et on peut rejouer n'importe quel conseil. Comme il pèse 10 %, il ne peut déplacer la note finale que de 5 points au plus.

### 3.5 Le moteur de décision — `decision_engine.py`

C'est le chef d'orchestre. Il ne lit pas la base : il reçoit des données et rend des résultats, ce qui le rend facile à tester.

| Fonction | Ce qu'elle fait |
|---|---|
| `final_score` | 0,40 × Infos + 0,25 × Graphique + 0,25 × Ratios + 0,10 × Hasard |
| `decide` | ≥ 60 → ACHAT ; ≤ 40 → VENTE ; sinon RIEN (la note est arrondie au dixième avant, pour que la note affichée et le conseil concordent) |
| `confidence` | « faible », « moyenne » ou « forte » selon l'écart à 50 |
| `build_reasons` | Écrit 2 à 4 phrases : alerte éventuelle, une phrase par pilier qui pousse dans le sens du conseil, un point de vigilance. Le hasard n'est jamais cité. |
| `forecast` | 3 scénarios pour la semaine à partir des 52 dernières semaines (moyenne μ et volatilité σ) |
| `simulate_operation` | Simulateur : nombre d'actions **entier** (`floor`), reste en cash, refus si le cash ou la position ne suffit pas, verdict |
| `verdict` | Croise ce que veut le client et le conseil (tableau SPEC §10.3), puis applique l'alerte de perte |
| `alert_level` | AUCUN, APPROCHE (−7 %) ou ATTEINT (−10 %) |
| `positions`, `portfolio_value`, `realized_gains` | Actions détenues, valeur du portefeuille, gains réalisés sur les ventes |

**Exemple suivi de bout en bout (SPEC §7.3) :** Infos 66,9, Graphique 60,1, Ratios 57,4, Hasard 37,2 → note finale 59,9 → conseil RIEN, avec la phrase « Note de 59,9, juste sous le seuil d'achat (60) : signaux plutôt favorables mais pas assez nets. »

### 3.6 Le test de l'alerte — `tools/stress_test.py`

Fait baisser tous les cours d'un même pourcentage, en mémoire, et regarde quand l'alerte passe à l'orange puis au rouge. Avec 400 000 € investis et 100 000 € de cash, le rouge arrive à −12,5 % (recette REC-4). Lancement : `python -m tools.stress_test`.

## 4. Les tests (`backend/tests/`)

| Fichier | Ce qu'il vérifie |
|---|---|
| `test_spec_cases.py` | Les exemples chiffrés de la SPEC (V1 à V16) : l'application doit retrouver exactement les mêmes résultats |
| `test_services.py` | Les autres règles des calculs : seuils, refus du simulateur, formats français, raisons… |
| `test_config.py` | Les réglages et RG-04 |
| `test_main.py` | L'API de base et la connexion |
| `test_refresh.py` | La collecte et l'actualisation, avec la fausse base de `fakes.py` |
| `test_routes.py` | Les routes de l'API et les recettes REC-1 à REC-4 |
| `test_cache.py` | La mémoire courte de l'API |

Lancement depuis `backend/` : `python -m pytest`. La couverture doit rester au-dessus de 70 %.

## 5. La collecte et l'actualisation

### 5.1 Qui fait quoi

| Fichier | Rôle |
|---|---|
| `db/repository.py` | **Le seul endroit qui parle à Supabase.** Il traduit « donne-moi les cours de DSY.PA » ou « enregistre ces notes » en requêtes. Le reste du code ne connaît pas Supabase. Chaque requête passe par `_run` : en cas de coupure réseau, elle est réessayée (3 fois au plus), et les écritures passent une par une. |
| `services/market_data.py` | Va chercher les données à l'extérieur : cours et dividendes (yfinance), chiffre d'affaires (yfinance), actualités (Google News en RSS et NewsAPI). |
| `services/refresh_service.py` | Le chef d'orchestre de l'actualisation : collecter, enregistrer, recalculer, ouvrir la semaine. |
| `tools/refresh.py` | Lance une actualisation à la main : `python -m tools.refresh`. |

### 5.2 Une actualisation, pas à pas

Pour chacune des 5 actions :

1. **Cours** : la première fois, on charge 2 ans de cours (il en faut au moins 200 séances pour la moyenne sur 200 jours, et 52 semaines pour la prévision). Ensuite, on ne recharge que les 7 derniers jours. L'enregistrement remplace une séance déjà connue au lieu de la dupliquer.
2. **Ratios** : chiffre d'affaires des deux derniers exercices et dividende par action de chaque année. Un exercice déjà en base est mis à jour, pas dupliqué.
3. **Actualités** : celles des 7 derniers jours. On ne garde que les articles qui **citent vraiment l'entreprise** (son nom dans le titre ou le résumé) et qui ne sont pas de simples pages de cotation. Chaque article reçoit sa note d'impact tout de suite. Un article déjà connu (même lien ou même titre) n'est pas ajouté une deuxième fois.
4. **Calcul** : les 4 notes, la note finale, le conseil, les raisons et la prévision (fonction `score_stock`). Une nouvelle ligne est ajoutée dans `scores_actions` : on garde ainsi l'historique de tous les conseils.
5. **Mise à jour** du dernier cours et du dividende attendu dans `actions`.

Enfin, la première actualisation de la semaine **ouvre la semaine** (`open_week_if_needed`) : la valeur du portefeuille au dernier cours de la semaine précédente devient la référence de l'alerte de perte.

**Si une source est en panne**, l'actualisation continue avec ce qui est déjà en base, et l'erreur est notée dans le compte rendu.

**Plus rapide** : les 5 actions sont collectées **en même temps** (`collect_stock` lancée en parallèle), ce qui ramène l'actualisation d'environ 40 à 20 secondes, car l'essentiel du temps est de l'attente réseau.

**En arrière-plan** : le bouton « Actualiser » reçoit tout de suite la réponse « lancée » (code 202) ; l'interface demande toutes les 2 secondes où en est le travail (`GET /api/market/refresh/status`), puis recharge l'écran. Une actualisation au plus toutes les 2 minutes ; NewsAPI au plus toutes les 15 minutes, pour rester dans son quota gratuit.

### 5.2 bis Quand l'application s'actualise-t-elle ?

Trois mécanismes, du plus fiable au renfort :

1. **À la consultation** : quand quelqu'un ouvre le site et que les données ont plus d'une heure, l'API (`routers/dashboard.py`) lance elle-même l'actualisation en arrière-plan. L'écran s'affiche tout de suite avec les données actuelles, puis se recharge une vingtaine de secondes plus tard (le badge de l'accueil indique « Actualisation en cours… »).
2. **Page ouverte** : l'interface relit le tableau de bord toutes les 5 minutes, et quand on revient sur l'onglet.
3. **Tâche planifiée GitHub Actions** (`.github/workflows/refresh.yml`) : chaque heure en séance et à 18 h. GitHub peut la retarder de plusieurs heures, c'est pourquoi elle n'est qu'un renfort.

Et à tout moment, le bouton « Actualiser les données » (une fois toutes les 2 minutes au plus). Le code commun est dans `routers/refresh_control.py` : il garantit qu'une seule actualisation tourne à la fois.

### 5.3 bis Les cours intrajournaliers (graphiques 1 jour / 1 semaine)

La table `historique_cours` ne garde qu'un cours par jour. Pour les vues **1J** et **1S** de la fiche action, chaque actualisation récupère aussi des **bougies de 5 minutes** (`fetch_intraday`) et les range dans la table `cours_intraday` (créée par la migration 004) : un mois au premier chargement, puis les 5 dernières séances. Les bougies de plus de 35 jours sont supprimées. Si une actualisation a été interrompue et qu'il manque des bougies sur les 20 derniers jours, la suivante recharge le mois entier et comble les trous. L'API en fabrique deux vues : la dernière séance en bougies de 5 minutes, et la semaine en bougies de 30 minutes, à l'heure de Paris.

**Pourquoi garder un mois ?** Une moyenne sur 200 bougies a besoin de 200 bougies *avant* la première qu'on affiche. Les indicateurs sont donc calculés sur tout le mois, puis on ne garde que la période affichée : toutes les courbes commencent avec la première bougie. Le conseil, lui, reste calculé sur les cours de clôture.

### 5.3 Deux précisions de calcul

- **Dividende annuel** : certaines entreprises versent 4 fois par an (TotalEnergies). Si on additionne simplement les versements d'une année civile, un versement daté du 2 janvier ou du 31 décembre fausse tout (+35 % au lieu de +8 %). On prend donc le versement moyen de l'année × le nombre habituel de versements.
- **Dividende attendu** (pour le dividende estimé) : la somme des dividendes versés sur les 12 derniers mois.

### 5.4 Les tests sans base ni réseau

`tests/fakes.py` contient une **fausse base en mémoire** (`FakeRepository`) et un **faux collecteur** (`FakeCollector`) qui fabrique 2 ans de cours réalistes. Les tests de `test_refresh.py` vérifient l'actualisation complète sans jamais toucher Supabase ni Internet : 5 conseils enregistrés, pas de doublon quand on relance, survie aux pannes, ouverture de la semaine.

## 6. L'API (`backend/routers/`)

### 6.1 Les routes

| Route | Fichier | Ce qu'elle renvoie | Écrit en base ? |
|---|---|---|---|
| `GET /api/dashboard` | `dashboard.py` | Valeur du portefeuille, cash, part investie, performance de la semaine, niveau d'alerte, et pour les 5 actions : cours, variation du jour, actions détenues, conseil, prévision, dividende | Non |
| `POST /api/simulate` | `simulator.py` | Pour chaque titre coché : nombre d'actions entier, reste en cash, conseil, verdict, 3 scénarios (% et €), dividende, raisons | **Non** |
| `POST /api/transactions` | `transactions.py` | L'opération enregistrée et le nouveau cash, ou une erreur 400 | Oui, par `executer_transaction` uniquement |
| `GET /api/stocks/{ticker}` | `stocks.py` | Tout pour la fiche action, ses deux onglets en un seul appel : un an de cours avec indicateurs, conseil, prévision, dividende, actualités, ratios, poids des piliers | Non |
| `GET /api/portfolio/history` | `transactions.py` | Journal paginé, courbe de valeur jour par jour, bilan (plus-values, dividendes) | Non |
| `POST /api/market/refresh` | `stocks.py` | « lancée » (202), ou le compte rendu avec `?attendre=true` | Oui (données de marché) |
| `GET /api/market/refresh/status` | `stocks.py` | Où en est l'actualisation, et son compte rendu | Non |
| `GET /api/health` | `main.py` | « l'API tourne » | Non |

La documentation interactive de toutes les routes est sur http://localhost:8000/docs quand l'API tourne.

### 6.2 Le parcours « simuler puis enregistrer »

1. **Simuler** (`POST /api/simulate`) : l'API relit le dernier conseil du titre, le cours, le cash et les actions détenues, puis appelle `simulate_operation`. Rien n'est écrit. Si l'opération est impossible (cash insuffisant, titre non détenu), le verdict est REFUSE et la raison est la première phrase affichée.
2. **Confirmer** (`POST /api/transactions`) : l'interface renvoie le titre, l'opération, le nombre d'actions, le cours simulé et l'heure du conseil. L'API refuse (400) si le conseil a plus de 5 minutes ou si le cours a changé. Sinon, elle appelle **une seule fois** la fonction SQL `executer_transaction`, qui revérifie le cash (ou les actions détenues), enregistre l'opération et met à jour le cash d'un seul bloc. Le conseil donné à ce moment (note, raisons, graine du hasard) est enregistré avec l'opération, pour pouvoir le rejouer.

### 6.3 Codes de réponse

| Code | Quand |
|---|---|
| 200 | Tout va bien |
| 400 | Règle de gestion non respectée : cash insuffisant, vente supérieure à la position, conseil de plus de 5 minutes, cours changé |
| 404 | Code d'action inconnu |
| 422 | Saisie invalide : montant négatif ou nul, opération inconnue, aucune action cochée |
| 202 | Actualisation lancée en arrière-plan |
| 429 | Actualisation demandée moins de 2 minutes après la précédente |

### 6.4 Répondre en moins de 2 secondes

Chaque lecture de Supabase prend entre 0,3 et 1 seconde. Deux astuces :

- **Lectures en parallèle** : `load_state` (`services/portfolio_service.py`) lance en même temps la lecture des actions, des conseils et du portefeuille.
- **Mémoire courte** (`db/cached_repository.py`) : les données de marché sont gardées 10 minutes (elles ne changent qu'à l'actualisation, qui efface la mémoire), le portefeuille 30 secondes (effacé à chaque opération).

Résultat mesuré : environ 1 seconde au premier affichage, quelques millisecondes ensuite.

### 6.5 Les tests de recette

`tests/test_routes.py` fait tourner l'API sur la fausse base et vérifie les 4 scénarios du cahier des charges :

| Test | Vérifie |
|---|---|
| `test_rec1_…` | Les 5 actions ont un conseil, une prévision et un dividende |
| `test_rec2_…` | Simuler puis enregistrer, en moins de 2 secondes ; la simulation seule n'écrit rien |
| `test_rec3_…` | Chaque fiche a ses raisons (2 à 4) et son onglet Infos |
| `test_rec4_…` | L'alerte passe au rouge à −10 % et plus aucun achat n'est conseillé |
| `test_v14_…` | Si le cash ne suffit plus au moment de valider : erreur 400 et rien n'est écrit |

## 7. L'interface (`frontend/`)

### 7.1 Les outils

React 19 (le squelette de l'équipe), Vite 8 pour lancer et construire, Tailwind CSS 4 pour la mise en forme, React Router pour la navigation, TradingView Lightweight Charts pour les cours, Recharts pour la courbe de l'historique, Lucide pour les icônes.

### 7.2 Comment c'est rangé

```
frontend/src/
├── main.jsx              point de départ : routeur, messages (Toast), données du tableau de bord
├── App.jsx               les routes : /, /tableau-de-bord, /simulateur, /action/:ticker, /historique
├── index.css             Tailwind + branchement des couleurs de la charte
├── styles/tokens.css     copie de docs/charte/tokens.css (couleurs, espacements, polices)
├── api/client.js         SEUL fichier qui appelle l'API
├── lib/                  formats français (format.js), les 5 actions et leurs couleurs (stocks.js), verdicts
├── context/              données partagées : tableau de bord (DashboardContext), messages (ToastContext)
├── components/ui/        les 8 composants de la charte (Button, DecisionBadge, KpiCard, AlertBanner,
│                         AmountInput, StockCheckbox, ForecastBar, AdviceCard)
├── components/layout/    cadre commun : AppLayout, NavBar, Toast, LoadingState, ErrorState, Disclaimer
├── components/           blocs d'écran : StocksTable, RiskIndicator, SimulatorPanel, ConfirmDialog, stock/…
└── pages/                AccueilPage, DashboardPage, SimulatorPage, StockDetailPage, HistoryPage
```

### 7.3 Les règles suivies

- **L'interface ne parle qu'à l'API**, par `api/client.js` ; son adresse vient de `VITE_API_URL`. Aucune clé n'est dans le frontend.
- **Aucune couleur en dur** : toutes viennent des variables de `tokens.css`, reliées à Tailwind dans `index.css` (`bg-buy-soft`, `text-sell`…). Les graphiques lisent ces variables avec `cssVar()`.
- **Formats français** (`lib/format.js`) : `49 972,80 €`, `+3,2 %`, `−1,8 %` avec le vrai signe moins, `25 nov. 2026, 18:02`. Les petites variations gardent 2 décimales (`−0,01 %`) et une variation négligeable s'affiche `0,00 %`, sans signe ni couleur ; la performance s'affiche aussi en euros (`−40 €`).
- **Un conseil a toujours son signe et son mot** : ▲ ACHAT, ▼ VENTE, ■ RIEN (`DecisionBadge`).
- **La mention « outil d'aide à la décision… »** (`Disclaimer`) est sur chaque écran qui affiche un conseil, une prévision ou un dividende.

### 7.4 Comment les données circulent

- **Tableau de bord partagé** : `DashboardContext` appelle `GET /api/dashboard` une fois à l'ouverture. La même réponse sert à l'accueil, au tableau de bord, à l'en-tête du simulateur, à la date de la NavBar et au bandeau d'alerte. Elle est redemandée après une opération ou une actualisation.
- **Bandeau d'alerte** : `AppLayout` l'affiche sous la NavBar, sur toutes les pages, dès que le niveau n'est pas AUCUN.
- **Fiche action** : un seul appel `GET /api/stocks/{ticker}` ; les onglets, les périodes (1J, 1S, 1M à 1A) et les cases des indicateurs ne changent que l'affichage. 1J et 1S utilisent les bougies intrajournalières (`graphique.intraday`). Le simulateur de dividende calcule dans le navigateur.
- **Historique** : chaque changement de période, de titre ou de page rappelle `GET /api/portfolio/history`.

### 7.5 Le seul chemin qui enregistre : le simulateur

1. `SimulatorPanel` (le formulaire) : Achat / Vente, puis une ligne par action avec sa case à cocher et, à côté, **son propre montant** (saisir un montant coche l'action). En bas, le **total** comparé au cash disponible. Un montant vide ou nul est refusé dans le navigateur.
2. « Simuler » → `POST /api/simulate` (une ligne `{ticker, montant_eur}` par action) → une `AdviceCard` par titre (conseil, verdict, chiffres, 3 scénarios, raisons) et un **récapitulatif** (montant réellement investi, reste en cash, dividendes, cash après toutes les opérations). Pour un achat, le cash est décompté ligne après ligne : si le total dépasse le cash, les dernières lignes sont refusées avec leur raison. Rien n'est enregistré.
3. « Valider l'achat » (désactivé si l'opération est refusée) → `ConfirmDialog` avec le récapitulatif et le cash après l'opération.
4. « Valider » dans la fenêtre → `POST /api/transactions`. Succès : message, rechargement des données ; la carte affiche « Opération enregistrée » et on reste sur le simulateur tant que d'autres actions restent à valider, sinon retour au tableau de bord. Refus (400) : message rouge, la fenêtre reste ouverte, rien n'est écrit.

### 7.6 Vérifié

`npm run build` et `npm run lint` passent. Le parcours a été joué automatiquement dans un vrai navigateur (Chromium piloté par Playwright) : simulation, opération refusée avec bouton désactivé, fenêtre de confirmation puis annulation (sans rien enregistrer), montant vide, onglets de la fiche, action inconnue.

## 8. La mise en ligne

Tout est décrit pas à pas dans `docs/06_deploiement.md`. En résumé :

| Fichier | Rôle |
|---|---|
| `render.yaml` | Décrit l'API pour Render : dossier `backend`, Python 3.11, commande de lancement, route de santé `/api/health`, variables secrètes à saisir dans Render |
| `frontend/vercel.json` | Permet à Vercel d'ouvrir directement n'importe quelle adresse de l'application |
| `.github/workflows/refresh.yml` | Actualisation planifiée : appelle `POST /api/market/refresh` à 18 h et chaque heure en séance |
| `.github/workflows/ci.yml` | Sur chaque Pull Request : tests du backend et construction du frontend |

## 9. Le profil de risque et le thème (D-17)

### 9.1 Le profil de risque

Dans l'onglet **Profil**, le client choisit à partir de quelle note on lui conseille d'acheter ou de vendre :

| Profil | Achat si note ≥ | Vente si note ≤ | En pratique |
|---|---|---|---|
| Prudent | 60 | 40 | Réglage du cahier des charges : conseils rares mais nets |
| Équilibré | 55 | 45 | Plus de conseils |
| Dynamique | 50 | 40 | Achat dès que les signaux sont favorables ; vente seulement s'ils sont nettement défavorables |

Les profils sont définis dans `config.py` (`PROFILS_RISQUE`). Le choix est enregistré dans la colonne `portefeuille.profil_risque` (migration 005) par `PUT /api/profil` (`routers/profile.py`). À chaque affichage, `load_state` lit ce profil et **relit chaque conseil avec ses seuils** (`rederive_advice`) : changer de profil change immédiatement les conseils de tous les écrans, sans recalculer les notes. Le garde-fou de perte (−10 % par semaine) ne dépend pas du profil.

La page montre, pour chaque profil, combien des 5 actions seraient à l'achat, en attente ou à la vente avec les notes du moment : le client voit l'effet avant d'enregistrer.

### 9.2 Le thème clair ou sombre

`context/ThemeContext.jsx` garde le choix (clair, sombre ou « comme l'ordinateur ») dans le navigateur et pose `data-theme="dark"` sur la page ; les couleurs sombres de la charte (`tokens.css`) prennent alors le relais, sans changer une ligne des composants. Un petit script dans `index.html` applique le thème avant l'affichage (pas de flash blanc). Les graphiques des cours sont redessinés quand le thème change, car ils lisent les couleurs au moment du dessin.
