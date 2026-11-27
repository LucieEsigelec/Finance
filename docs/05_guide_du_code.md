# Guide du code — PrimeInvest

Ce document explique **tout le code** de l'application, en français simple, pour que chaque membre du groupe puisse le comprendre, le modifier et le présenter. Il décrit le code tel qu'il est sur `main` (fin novembre 2026).

- Les **formules** viennent de la spécification (`docs/03_specification.md`, notée SPEC).
- Les **choix faits pendant le développement** sont dans `docs/decisions.md` (notés D-01 à D-20).
- Les **règles de travail** (Git, base partagée, style) sont dans `CLAUDE.md`.
- La **mise en ligne** est détaillée dans `docs/06_deploiement.md`.

Chaque fichier de code commence par un paragraphe **« En bref »** qui résume son rôle : c'est le meilleur point d'entrée quand on ouvre un fichier.

---

## Sommaire

1. [L'application en une page](#1-lapplication-en-une-page)
2. [Le trajet d'une donnée, de Yahoo à l'écran](#2-le-trajet-dune-donnée-de-yahoo-à-lécran)
3. [Où se trouve quoi](#3-où-se-trouve-quoi)
4. [La base de données](#4-la-base-de-données)
5. [Le backend (API Python)](#5-le-backend-api-python)
6. [Le frontend (interface React)](#6-le-frontend-interface-react)
7. [Les grands parcours, pas à pas](#7-les-grands-parcours-pas-à-pas)
8. [Les tests](#8-les-tests)
9. [Mise en ligne et exploitation](#9-mise-en-ligne-et-exploitation)
10. [Limites connues et pistes](#10-limites-connues-et-pistes)
11. [Questions fréquentes : « comment je change… »](#11-questions-fréquentes--comment-je-change-)
12. [Glossaire](#12-glossaire)

---

## 1. L'application en une page

**PrimeInvest** aide un client (M. Dupont) à gérer un **portefeuille virtuel de 500 000 €** sur **5 actions** de la Bourse de Paris : Dassault Systèmes (DSY.PA), TotalEnergies (TTE.PA), Capgemini (CAP.PA), Hermès (RMS.PA) et Air Liquide (AI.PA).

Pour chaque action, l'application donne un **conseil** : **▲ ACHAT**, **▼ VENTE** ou **■ RIEN**, toujours accompagné de **2 à 4 raisons** en phrases simples, d'une **prévision** pour la semaine (3 scénarios) et du **dividende** estimé. Le client peut **simuler** un achat ou une vente, puis l'**enregistrer**. Un **garde-fou** l'alerte si le portefeuille perd 7 % puis 10 % dans la semaine.

L'application est faite de **trois blocs** qui se parlent dans un seul sens :

```
 Navigateur du client                Serveur (Render)                   Base (Supabase)
┌──────────────────────┐   HTTPS   ┌──────────────────────────┐       ┌──────────────────┐
│ Interface React      │ ────────► │ API FastAPI (Python)     │ ────► │ PostgreSQL       │
│ (Vercel)             │   JSON    │ calculs, règles, conseils│       │ 8 tables         │
└──────────────────────┘           └────────────┬─────────────┘       └──────────────────┘
                                                │ seulement pendant une « actualisation »
                                                ▼
                         Yahoo Finance (cours, dividendes, CA) · Google News · NewsAPI
                         Claude Haiku 5.5 (lecture des actualités)
```

- **La base** garde tout : les actions, leurs cours, les actualités, les notes calculées, le portefeuille et les opérations.
- **L'API** fait tous les calculs et est **la seule** à lire ou écrire dans la base.
- **L'interface** affiche ce que l'API lui envoie ; elle ne contient aucune clé secrète et ne parle jamais directement à la base ou aux sources externes.

**L'idée centrale : tout est calculé à l'avance.** Une « actualisation » va chercher les données dehors et calcule les conseils ; quand le client clique, l'API ne fait que relire ces résultats. C'est ce qui permet de répondre en moins de 2 secondes (exigence ENF-02).

---

## 2. Le trajet d'une donnée, de Yahoo à l'écran

Suivons le conseil affiché pour TotalEnergies.

1. **L'actualisation démarre** (toutes les heures en séance, ou quand quelqu'un ouvre le site et que les données ont plus d'une heure, ou avec le bouton « Actualiser »).
2. **Collecte** (`services/market_data.py`) : on récupère les nouveaux cours de TotalEnergies sur Yahoo Finance, ses dividendes et son chiffre d'affaires, et les articles de presse des 7 derniers jours (Google News et NewsAPI).
3. **Lecture des articles** (`services/news_nlp.py`) : les nouveaux articles sont envoyés à **Claude Haiku 5.5**, qui dit pour chacun s'il est positif ou négatif pour l'actionnaire, s'il s'agit d'une annonce officielle et s'il parle vraiment de TotalEnergies.
4. **Enregistrement** (`db/repository.py`) : cours, ratios et articles notés sont rangés dans la base.
5. **Calcul des 4 notes sur 100** (`services/*_scoring.py`) : Informations, Analyse graphique, Ratios, Hasard.
6. **Décision** (`services/decision_engine.py`) : note finale = 40 % Infos + 25 % Graphique + 25 % Ratios + 10 % Hasard, puis conseil selon les seuils, raisons et prévision. Le tout est rangé dans la table `scores_actions`.
7. **Le client ouvre le tableau de bord** : l'interface appelle `GET /api/dashboard` (`routers/dashboard.py`). L'API relit la dernière note, **reprend le conseil avec les seuils du profil du client** (Prudent, Équilibré ou Dynamique), et renvoie tout en JSON.
8. **L'interface affiche** la ligne TotalEnergies avec son badge ▲ ACHAT (`components/StocksTable.jsx`, `components/ui/DecisionBadge.jsx`).

---

## 3. Où se trouve quoi

```
portefeuille-500k-depot/
├── backend/                 API Python (FastAPI)
│   ├── main.py              crée l'API, autorise le site à l'appeler (CORS), branche les routes
│   ├── config.py            TOUS les réglages (poids, seuils, durées, profils…) + contrôles au démarrage
│   ├── db/                  accès à la base
│   │   ├── supabase_client.py   connexion unique à Supabase
│   │   ├── repository.py        toutes les lectures/écritures (seul endroit qui parle à Supabase)
│   │   └── cached_repository.py mémoire courte devant la base (rapidité)
│   ├── models/schemas.py    vérification des requêtes envoyées par l'interface
│   ├── routers/             les « portes d'entrée » de l'API (une route = une adresse)
│   ├── services/            les calculs (piliers, décision, collecte, actualisation)
│   ├── tools/               petits programmes à lancer à la main
│   └── tests/               tests automatiques (181)
├── frontend/                interface React
│   └── src/
│       ├── main.jsx, App.jsx    démarrage et liste des pages
│       ├── api/client.js        SEUL fichier qui appelle l'API
│       ├── context/             données partagées (tableau de bord, thème, messages)
│       ├── components/          morceaux d'écran (dont les 8 composants de la charte dans ui/)
│       ├── pages/               les 6 pages
│       ├── lib/                 formats français, liste des actions
│       └── styles/tokens.css    couleurs et tailles de la charte graphique
├── supabase/                schéma de la base, données de départ, migrations
├── docs/                    cahier des charges, conception, spécification, interface, charte, guides
├── render.yaml              description de l'API pour l'hébergeur Render
└── .github/workflows/       tests automatiques et actualisation planifiée (GitHub Actions)
```

---

## 4. La base de données

La base est un **PostgreSQL** hébergé par **Supabase**, **partagée par tout le groupe**. Toute modification de structure passe par un fichier de **migration** numéroté, relu puis exécuté dans l'éditeur SQL de Supabase.

### 4.1 Les tables

| Table | Ce qu'elle contient | Écrite par |
|---|---|---|
| `actions` | Les 5 actions : code, nom, secteur, dernier cours, dividende attendu | l'actualisation |
| `historique_cours` | Un cours par jour et par action (ouverture, plus haut, plus bas, clôture, volume) sur 2 ans | l'actualisation |
| `cours_intraday` | Des bougies de 5 minutes sur environ un mois (graphiques 1 jour / 1 semaine) | l'actualisation |
| `ratios_financiers` | Chiffre d'affaires, dividende par action et rendement des deux derniers exercices | l'actualisation |
| `actualites` | Les articles des 7 derniers jours, avec leur note d'impact sur 100 | l'actualisation |
| `scores_actions` | Une ligne par action et par actualisation : note finale, conseil, prévision, et le détail des 4 piliers (en JSON) | l'actualisation |
| `portefeuille` | Le portefeuille unique : capital de départ, cash, valeur de référence du lundi, nom du client, profil de risque | opérations, profil, ouverture de la semaine |
| `transactions` | Le journal des achats et ventes, avec le conseil donné à ce moment | la fonction `executer_transaction` |

Il n'y a **pas de table des positions** : le nombre d'actions détenues se calcule à partir des transactions (achetées − vendues).

### 4.2 La fonction `executer_transaction`

Enregistrer une opération demande deux écritures : ajouter la transaction **et** mettre à jour le cash. Si l'une réussissait sans l'autre, le cash serait faux. La fonction SQL `executer_transaction` fait tout **d'un seul bloc** : elle verrouille le portefeuille, revérifie que le cash suffit (achat) ou que les actions sont détenues (vente), enregistre l'opération au dernier cours connu et met à jour le cash. Si une vérification échoue, **rien n'est écrit** (règle RG-05). Son code est dans `supabase/schema.sql`.

### 4.3 Les fichiers SQL

| Fichier | Rôle |
|---|---|
| `supabase/schema.sql` | Le script d'origine de la base (7 tables, index, fonction `executer_transaction`) |
| `supabase/seed.sql` | Les données de départ : les 5 actions et le portefeuille de 500 000 € (rejouable sans doublon) |
| `supabase/migrations/003_ajustements.sql` | Colonne `nom_client`, cours toujours positif, anti-doublons, fonction réservée au serveur, sécurité par ligne |
| `supabase/migrations/004_cours_intraday.sql` | Table `cours_intraday` (graphiques 1 jour / 1 semaine) |
| `supabase/migrations/005_profil_risque.sql` | Colonne `profil_risque` du portefeuille |
| `supabase/verifier_schema.sql` | Requête en lecture seule pour contrôler la structure de la base |

**Sécurité** : la « sécurité par ligne » (RLS) est activée sur toutes les tables, sans aucune règle d'accès public. Seul le serveur, avec la clé secrète `service_role`, peut lire ou écrire.

---

## 5. Le backend (API Python)

Le backend est écrit en **Python 3.11** avec **FastAPI**. On le lance depuis `backend/` avec `python -m uvicorn main:app --reload --port 8000`. La documentation interactive de toutes les routes est alors sur http://localhost:8000/docs.

### 5.1 `config.py` — tous les réglages au même endroit

Aucun nombre du moteur n'est écrit ailleurs. Pour changer un comportement, on change une ligne ici, sans toucher aux calculs. Les principaux réglages :

| Réglage | Valeur | Rôle |
|---|---|---|
| `POIDS` | Infos 0,40 · Graphique 0,25 · Ratios 0,25 · Hasard 0,10 | Poids des 4 piliers dans la note finale |
| `SEUIL_ACHAT` / `SEUIL_VENTE` | 60 / 40 (modifiables par variable d'environnement) | Seuils par défaut, quand aucun profil n'est choisi |
| `PROFILS_RISQUE` | Prudent 60/40 · Équilibré 55/45 · Dynamique 50/40 | Seuils selon le profil du client |
| `IMPORTANCES_TECH` | Bollinger 9 · RSI 7 · MACD 6 · Moyennes 5 · Tendance 5 | Poids des 5 indicateurs graphiques |
| `INFO_DEMI_VIE_JOURS` / `INFO_FENETRE_JOURS` | 2 jours / 7 jours | Vieillissement des articles |
| `ALERTE_APPROCHE_PCT` / `ALERTE_ATTEINT_PCT` | −7 % / −10 % | Garde-fou de perte de la semaine |
| `NLP_MODELE` | `claude-haiku-5-5` | Modèle qui lit les actualités |
| `REFRESH_INTERVALLE_MIN_SECONDES` | 120 | Au plus une actualisation toutes les 2 minutes |
| `DONNEES_AGE_MAX_SECONDES` | 3 600 | Au-delà d'une heure, la consultation relance l'actualisation |

**Contrôles au démarrage** (`check_config`) : si un réglage est incohérent, l'API **refuse de démarrer**. Le plus important est **RG-04** : le poids des Informations doit être strictement le plus grand des quatre (cas de test V8). Les poids doivent aussi faire 100 %, et chaque profil doit respecter « seuil de vente ≤ 50 ≤ seuil d'achat ».

`load_settings()` lit les **secrets** dans `backend/.env` (en local) ou dans les variables de Render (en ligne) : adresse et clé Supabase, clé NewsAPI, clé Anthropic, adresses autorisées. Ces valeurs ne sont jamais affichées, même dans un message d'erreur.

### 5.2 L'accès à la base (`db/`)

| Fichier | Rôle |
|---|---|
| `supabase_client.py` | Ouvre **une seule** connexion à Supabase, au premier besoin (pas au démarrage : les tests tournent sans fichier `.env`). |
| `repository.py` | **Le seul endroit qui parle à Supabase.** Il traduit des demandes simples (« donne-moi les cours de DSY.PA », « enregistre ces notes ») en requêtes. Les montants sont relus en `Decimal` (jamais en nombre à virgule flottante). Chaque requête passe par `_run`, qui **réessaie 3 fois** après une coupure réseau et fait passer **les écritures une par une**. |
| `cached_repository.py` | Une **mémoire courte** devant la base : chaque lecture de Supabase coûte entre 0,3 et 1 seconde. Les données de marché sont gardées **10 minutes** (elles ne changent qu'à l'actualisation, qui efface cette mémoire) ; le portefeuille **30 secondes** (effacé à chaque opération). |

Grâce à cette organisation, les tests remplacent la vraie base par une **fausse base en mémoire** (`tests/fakes.py`) qui a exactement les mêmes méthodes : ils ne touchent jamais la base partagée.

### 5.3 La collecte des données (`services/market_data.py`, `services/news_nlp.py`)

**Cours et chiffres** (Yahoo Finance, par la bibliothèque `yfinance`) :

- `fetch_history` : cours quotidiens, 2 ans au premier passage (il faut au moins 200 séances pour la moyenne sur 200 jours), ensuite seulement les 7 derniers jours.
- `fetch_intraday` : bougies de 5 minutes, un mois au premier passage, ensuite 5 séances. S'il manque des bougies (actualisation interrompue), le mois est rechargé.
- `fetch_fundamentals` : chiffre d'affaires des deux derniers exercices et dividendes. Le **dividende annuel** = versement moyen de l'année × nombre habituel de versements (sinon un versement trimestriel daté du 2 janvier fausse tout). Le **dividende attendu** = dividendes des 12 derniers mois.

**Actualités** (`fetch_news`) : Google News (flux RSS, en français) et NewsAPI (au plus une fois toutes les 15 minutes, pour rester dans son quota gratuit de 100 requêtes par jour). On ne garde que les articles des 7 derniers jours **qui citent l'entreprise** et qui ne sont pas de simples pages de cotation (`is_relevant`).

**Lecture des articles par un modèle de langue** (`news_nlp.py`) : pour chaque action, les **nouveaux** articles (titre + résumé) partent en **un seul appel** à **Claude Haiku 5.5** (au plus 40 articles par appel). La réponse est imposée au format JSON. Pour chaque article, le modèle donne :

- le **sentiment** pour l'actionnaire, de −1 (très défavorable) à +1 (très favorable), en comprenant le contexte (« baisse des coûts » est une bonne nouvelle) ;
- s'il s'agit d'une **annonce officielle** de l'entreprise (résultats, contrat, acquisition, dividende, dirigeant, avertissement) ;
- s'il **concerne vraiment l'entreprise** (sinon il est écarté, par exemple « Hermès » le dieu grec).

La note d'impact garde la formule de la SPEC : **50 + 50 × sentiment × importance** (importance 1 pour une annonce officielle, 0,5 sinon). **Secours** : sans clé `ANTHROPIC_API_KEY`, ou si l'appel échoue ou est refusé, on revient à l'ancienne méthode, `services/sentiment.py`, qui compte des mots positifs et négatifs en français et en anglais. L'actualisation ne s'arrête jamais à cause du modèle.

### 5.4 Les quatre piliers : quatre notes sur 100

Chaque pilier donne une **note sur 100** (50 = neutre). Pour y arriver, chaque indicateur donne d'abord un **signal entre −1 et +1**, puis on applique toujours la même formule : **note = 50 + 50 × signal** (`services/common.py`). Un indicateur qu'on ne peut pas calculer est simplement ignoré.

#### Analyse graphique — `technical_scoring.py` (25 %)

Calculée par nous, avec la bibliothèque `ta`, à partir des cours de clôture :

| Indicateur (importance) | Question | Signal +1 | Signal −1 |
|---|---|---|---|
| Bollinger (9) | Le cours est-il en bas ou en haut de son couloir habituel de 20 jours ? | en bas | en haut |
| RSI (7) | A-t-il trop baissé ou trop monté sur 14 jours ? | RSI ≤ 30 | RSI ≥ 70 |
| MACD (6) | La moyenne courte vient-elle de croiser la longue (5 dernières séances) ? | croisement à la hausse | à la baisse |
| Moyennes mobiles (5) | Le cours est-il au-dessus de ses moyennes 20 / 50 / 200 jours ? | au-dessus | en dessous |
| Tendance (5) | Le cours monte-t-il depuis un mois (+3 % par semaine) ? | hausse | baisse |

Note = moyenne des 5 signaux pondérée par leur importance. **Aucun cours postérieur à la date du calcul n'est utilisé** (un test le vérifie avec de faux cours « futurs »).

#### Lecture détaillée du graphique — `chart_analysis.py` (explication, hors note)

En plus de la note, l'application **explique** le graphique en phrases simples (D-24). Rien ici ne change la note ni le conseil.

- **Moyennes mobiles** : le cours est-il au-dessus ou en dessous des moyennes 20, 50 et 200 jours, et de combien ? Les moyennes sont-elles « rangées » (20 > 50 > 200 = hausse installée) ?
- **Croisements récents** (sur un mois) : la moyenne 50 jours passe au-dessus de la 200 jours (« croisement doré ») ou en dessous (« croisement de la mort ») ; idem 20 / 50 jours pour le court terme.
- **Supports et résistances** : sur 6 mois, on repère les sommets et les creux (plus haut / plus bas sur ±5 séances), on regroupe ceux qui sont à moins de 1,5 % les uns des autres ; un niveau touché au moins 2 fois compte. Sous le cours = support, au-dessus = résistance. À défaut, le plus bas / plus haut de 6 mois.
- **Où ça s'affiche** : carte « Analyse graphique » et lignes pointillées sur le graphique de la fiche action (calcul à la lecture) ; bloc dépliable sous chaque conseil du simulateur (calcul à l'actualisation, rangé dans `details_piliers`).

Les réglages (6 mois, ±5 séances, 1,5 %, 2 contacts) sont dans `config.py` (`SR_…`).

#### Informations — `info_scoring.py` (40 %, pilier majoritaire)

1. Chaque article a sa note d'impact (paragraphe 5.3).
2. Un article **perd la moitié de son poids tous les 2 jours** et est ignoré après 7 jours.
3. Note = moyenne des notes d'impact pondérée par ces poids. Sans article récent : 50 et « aucune actualité récente ».
4. Les 3 articles qui pèsent le plus deviennent les « faits marquants » cités dans les raisons.

Exemple de la SPEC (cas V4) : un article d'hier noté 80 et un de 4 jours noté 30 donnent **66,9**.

#### Ratios financiers — `ratio_scoring.py` (25 %)

Trois questions sur les deux derniers exercices : le **chiffre d'affaires** progresse-t-il (+10 % → +1, +5 % → 0, baisse → −1) ? le **dividende** augmente-t-il ? le **rendement** est-il meilleur que la moyenne des 5 titres ? Le module calcule aussi le **dividende estimé** : nombre d'actions × dividende par action, au centime.

#### Hasard — `randomness_service.py` (10 %)

Un nombre entre 0 et 100 tiré à partir d'une « graine » fabriquée avec le titre et la semaine (par exemple `DSY.PA2026-W48`). Même titre et même semaine donnent toujours le même nombre : le conseil ne change pas à chaque clic et on peut le rejouer. Comme il pèse 10 %, il ne déplace la note finale que de 5 points au plus : il ne peut jamais décider seul. Il n'est jamais cité dans les raisons.

### 5.5 Le moteur de décision — `services/decision_engine.py`

C'est le chef d'orchestre des calculs. Il ne lit pas la base : il reçoit des données et rend des résultats, ce qui le rend facile à tester.

| Fonction | Ce qu'elle fait |
|---|---|
| `final_score` | Note finale = 0,40 × Infos + 0,25 × Graphique + 0,25 × Ratios + 0,10 × Hasard |
| `decide` | Note ≥ seuil d'achat → ACHAT ; ≤ seuil de vente → VENTE ; sinon RIEN. La note est d'abord arrondie au dixième, pour que la note affichée et le conseil concordent. Les seuils sont ceux du profil du client. |
| `confidence` | « faible » (moins de 15 points d'écart à 50), « moyenne » (15 à 25), « forte » |
| `build_reasons` | 2 à 4 phrases : l'alerte de perte en premier si elle est active, une phrase par pilier qui pousse dans le sens du conseil, un point de vigilance. Les indicateurs sont traduits en français courant : on n'écrit jamais « RSI = 35 » mais « le titre a beaucoup baissé récemment, un rebond est fréquent » (RG-03). |
| `rederive_advice` | Reprend le conseil et ses raisons à partir de la note enregistrée, avec les seuils du profil : changer de profil change les conseils **tout de suite**, sans recalculer les notes |
| `forecast` | 3 scénarios pour la semaine à partir des 52 dernières semaines : central = moyenne + (note − 50) / 50 × volatilité ; favorable et défavorable = central ± volatilité. Rien si moins de 6 mois d'historique. |
| `simulate_operation` | Simulateur : nombre d'actions **entier** (partie entière de montant / cours), reste en cash, refus si le cash ou la position ne suffit pas |
| `verdict` | Croise ce que veut le client et le conseil (« Vous pouvez valider », « Ne rien faire pour l'instant », « Privilégier la vente », « Conserver la position », « Opération refusée »), puis applique l'alerte : à −7 %, plus aucun achat n'est conseillé ; à −10 %, la vente est conseillée |
| `alert_level` | AUCUN, APPROCHE (−7 %) ou ATTEINT (−10 %) — règle RG-01 |
| `positions`, `portfolio_value`, `realized_gains` | Actions détenues, valeur du portefeuille (cash + actions × dernier cours), gain réalisé sur chaque vente (méthode du prix moyen) |

**Exemple complet (SPEC §7.3)** : Infos 66,9, Graphique 60,1, Ratios 57,4, Hasard 37,2 → note finale **59,9** → avec le profil Prudent (achat ≥ 60), conseil **RIEN**, et première raison : « Note de 59,9, juste sous le seuil d'achat (60) : signaux plutôt favorables mais pas assez nets. »

### 5.6 L'actualisation — `services/refresh_service.py` et `routers/refresh_control.py`

`refresh()` fait, pour les 5 actions **en même temps** (environ 20 à 30 secondes au total, surtout de l'attente réseau) :

1. collecter et enregistrer les cours, les bougies de 5 minutes, les ratios et les nouveaux articles (`collect_stock`) ;
2. calculer les 4 notes, la note finale, le conseil, les raisons et la prévision (`score_stock`), et ajouter une ligne dans `scores_actions` ;
3. mettre à jour le dernier cours et le dividende attendu dans `actions` ;
4. au premier passage de la semaine, **ouvrir la semaine** : la valeur du portefeuille au dernier cours avant lundi devient la référence du garde-fou de perte (`open_week_if_needed`).

Une source en panne n'arrête pas l'actualisation : l'erreur est notée dans le compte rendu et les données déjà en base servent.

**Quand l'actualisation se lance-t-elle ?** `refresh_control.py` garantit **qu'une seule tourne à la fois** et **au plus toutes les 2 minutes**, quelle que soit la demande :

| Déclencheur | Comment |
|---|---|
| Consultation du site | Si les données ont plus d'une heure, `GET /api/dashboard` la lance en arrière-plan ; l'écran s'affiche tout de suite puis se met à jour |
| Bouton « Actualiser » | `POST /api/market/refresh` répond aussitôt « lancée » ; l'interface suit l'avancement avec `GET /api/market/refresh/status` |
| Tâche planifiée | GitHub Actions appelle l'API chaque heure en séance et à 18 h (en renfort : GitHub peut la retarder) |
| À la main | `python -m tools.refresh` depuis `backend/` |

### 5.7 L'état du portefeuille — `services/portfolio_service.py`

`load_state()` lit en une fois (et en parallèle) les actions, les derniers conseils, le portefeuille et les opérations, puis en déduit : actions détenues, prix, valeur du portefeuille, performance de la semaine, niveau d'alerte, **profil de risque et seuils**, et chaque conseil relu avec ces seuils. Toutes les routes partent de cet état : elles voient donc toutes les mêmes chiffres. `with_alert` met la phrase d'alerte en tête des raisons quand le garde-fou est déclenché.

### 5.8 Les routes de l'API (`routers/`)

| Route | Fichier | Ce qu'elle renvoie | Écrit en base ? |
|---|---|---|---|
| `GET /api/dashboard` | `dashboard.py` | Valeur, cash, part investie, performance de la semaine (en % et en €), alerte, profil, et pour les 5 actions : cours, variation du jour, actions détenues, conseil, prévision, dividende | Non (peut lancer une actualisation) |
| `POST /api/simulate` | `simulator.py` | Pour chaque action et **son propre montant** : actions entières, reste en cash, conseil, verdict, 3 scénarios (% et €), dividende, raisons ; plus un total. Le cash est décompté ligne après ligne. | **Non** |
| `POST /api/transactions` | `transactions.py` | L'opération enregistrée et le nouveau cash, ou une erreur 400 | Oui, uniquement par `executer_transaction` |
| `GET /api/portfolio/history` | `transactions.py` | Journal paginé, courbe de valeur jour par jour, plus-values réalisées, dividendes | Non |
| `GET /api/stocks/{ticker}` | `stocks.py` | Tout pour la fiche action en un appel : un an de cours avec indicateurs, vues 1 jour et 1 semaine, conseil, prévision, dividende, actualités, ratios, poids des piliers | Non |
| `POST /api/market/refresh` et `GET …/status` | `stocks.py` | Lance l'actualisation / dit où elle en est | Oui (données de marché) |
| `GET` / `PUT` / `DELETE /api/profil` | `profile.py` | Lire le profil, l'enregistrer (avec le nom à la première connexion), ou « se déconnecter » (effacer nom et profil) | `PUT` et `DELETE` |
| `GET /api/health` | `main.py` | « L'API tourne » (sert à Render et à réveiller l'API) | Non |

**Codes de réponse** : 200 tout va bien · 202 actualisation lancée · 400 règle de gestion non respectée (cash insuffisant, vente plus grande que la position, conseil de plus de 5 minutes, cours changé) · 404 action inconnue · 409 base pas encore à jour (migration manquante) · 422 saisie invalide (montant nul ou négatif, profil inconnu, nom vide) · 429 actualisation demandée moins de 2 minutes après la précédente.

**`models/schemas.py`** vérifie chaque requête avant tout calcul (code 422 si invalide). **`routers/deps.py`** fournit aux routes la base, l'heure et l'analyseur d'actualités : les tests remplacent ces trois éléments par des versions factices.

### 5.9 Les outils (`tools/`)

À lancer depuis `backend/` avec `python -m tools.<nom>` :

| Outil | Rôle | Écrit en base ? |
|---|---|---|
| `check_supabase` | Vérifie la connexion et compte les lignes des tables | Non |
| `refresh` | Lance une actualisation complète et affiche le compte rendu | Oui |
| `rescore_news` | Renote avec Claude les articles des 7 derniers jours | Oui (notes des articles) |
| `stress_test` | Fait baisser tous les cours en mémoire pour vérifier que l'alerte passe au rouge à −10 % (recette REC-4) | Non |
| `reset_portfolio` | Après des tests : supprime toutes les opérations et remet le cash à 500 000 € (affiche le résumé et demande de taper RESET ; `--profil` efface aussi nom et profil) | **Oui, définitif** (opérations, cash) |

---

## 6. Le frontend (interface React)

### 6.1 Les outils

**React 19** pour les écrans, **Vite** pour lancer (`npm run dev`) et construire (`npm run build`), **Tailwind CSS** pour la mise en forme, **React Router** pour la navigation, **TradingView Lightweight Charts** pour les graphiques de cours, **Recharts** pour la courbe de l'historique, **Lucide** pour les icônes.

### 6.2 Démarrage et navigation

- `main.jsx` démarre l'application et l'entoure de trois « contextes » (données partagées) : le thème, les messages, le tableau de bord.
- `App.jsx` liste les pages : `/` (Accueil), `/tableau-de-bord`, `/ordres` (Acheter / vendre ; l'ancienne adresse `/simulateur` redirige), `/action/:ticker` (fiche d'une action), `/historique`, `/profil`. Les pages avec de gros graphiques ne sont chargées qu'à leur ouverture, pour un premier affichage rapide.
- `components/layout/AppLayout.jsx` est le cadre commun : barre de navigation, bandeau d'alerte (sur toutes les pages dès que le niveau n'est pas AUCUN), page, dialogue de bienvenue.

### 6.3 Les règles suivies

- **L'interface ne parle qu'à l'API**, et seulement par `api/client.js` ; son adresse vient de la variable `VITE_API_URL`. Aucune clé secrète n'est dans le frontend.
- **Aucune couleur en dur** : toutes viennent de `styles/tokens.css` (copie de la charte), branchées sur Tailwind dans `index.css` (`bg-buy-soft`, `text-sell`…). En thème sombre, ce sont les mêmes noms avec d'autres valeurs.
- **Formats français** (`lib/format.js`) : `49 972,80 €`, `+3,2 %`, `−1,8 %` avec le vrai signe moins, `−0,01 %` pour les petites variations, `25 nov. 2026, 18:02`.
- **Un conseil a toujours son signe et son mot** : ▲ ACHAT, ▼ VENTE, ■ RIEN (la couleur seule ne suffit pas pour les daltoniens).
- **L'avertissement « Les conseils sont une aide à la décision, ils ne garantissent pas le succès : vous restez seul décideur. »** est dans le pied de page (`AppLayout`), donc en bas de **toutes** les pages (ENF-03, D-25). L'API renvoie le même texte dans le champ `mention`.

### 6.4 Les données partagées (`context/`)

| Contexte | Rôle |
|---|---|
| `DashboardContext.jsx` | Appelle `GET /api/dashboard` à l'ouverture ; la même réponse sert à l'accueil, au tableau de bord, au simulateur, à la barre et au bandeau d'alerte. Relit toutes les 5 minutes et au retour sur l'onglet ; suit une actualisation lancée par le serveur puis recharge. Fournit aussi `refreshMarket` (bouton « Actualiser »). |
| `ThemeContext.jsx` | Thème clair, sombre ou « comme l'ordinateur », gardé dans le navigateur ; pose `data-theme="dark"` sur la page. |
| `ToastContext.jsx` | Petits messages de succès ou d'erreur en bas de l'écran. |

### 6.5 Les composants

**Les 8 composants de la charte** (`components/ui/`) : `Button`, `DecisionBadge` (▲ ACHAT…), `KpiCard` (carte chiffrée), `AlertBanner` (bandeau de perte), `AmountInput` (champ en euros), `StockCheckbox` (case d'une action avec sa pastille de couleur), `ForecastBar` (les 3 scénarios), `AdviceCard` (résultat d'une simulation, dans un ordre fixe, avec l'analyse graphique dépliable).

**Les autres** :

| Composant | Rôle |
|---|---|
| `layout/NavBar.jsx` | 6 onglets, date des données, thème, « Actualiser », « Se déconnecter » |
| `layout/Logo.jsx` | Le logo « Prisme » (5 facettes de bleu pétrole) et le nom PRIMEINVEST ; ses couleurs (`--logo-1` à `--logo-5`) changent avec le thème |
| `StocksTable.jsx` | Le tableau des 5 actions du tableau de bord (un clic ouvre la fiche) |
| `RiskIndicator.jsx` | La jauge de perte de la semaine avec les repères −7 % et −10 % |
| `SimulatorPanel.jsx` | Le formulaire de la page Acheter / vendre : Achat / Vente, saisie en euros ou en nombre d'actions, une case par action (avec sa conversion et la part du capital), total, actions détenues en vente |
| `ConfirmDialog.jsx` | La fenêtre de confirmation avant d'enregistrer une opération |
| `WelcomeDialog.jsx` | Le dialogue de bienvenue (nom + profil de risque) à la première connexion |
| `LogoutDialog.jsx` | La confirmation de déconnexion |
| `stock/PriceChart.jsx` | Le graphique de la fiche : bougies, moyennes mobiles, Bollinger, panneaux RSI et MACD qui défilent ensemble |
| `stock/StockCards.jsx` | Les cartes de la fiche : en-tête (avec le bouton « Acheter / vendre » qui ouvre le simulateur, action cochée), conseil, prévision, simulateur de dividende, actualités, ratios, poids des piliers |

### 6.6 Les pages

| Page | Ce qu'on y voit |
|---|---|
| **Accueil** (`AccueilPage.jsx`) | « Bonjour M. Dupont », valeur du portefeuille, performance de la semaine (en % et en €), cash, conseils de la semaine classés ACHAT / RIEN / VENTE, raccourcis |
| **Tableau de bord** (`DashboardPage.jsx`) | 4 cartes chiffrées, jauge de perte, tableau des 5 actions, profil en cours |
| **Acheter / vendre** (`SimulatorPage.jsx`, `/ordres`) | Formulaire à gauche ; à droite une carte de conseil par action (avec la part du capital sur l'action), un récapitulatif, puis la validation action par action. Saisie au choix en euros ou en nombre d'actions (changer d'unité convertit ce qui est saisi). En vente, une case trop grande passe en rouge ; à l'achat, dépasser la limite du profil aussi ; « Voir le conseil » se grise alors. Depuis une fiche action, `?action=…&operation=…` coche l'action et choisit le mode. |
| **Fiche action** (`StockDetailPage.jsx`) | Sélecteur des 5 actions par leur nom, en-tête, onglet **Graphique** (périodes 1J, 1S, 1M, 3M, 6M, 1A, indicateurs à cocher, conseil, prévision, dividende) et onglet **Infos** (actualités notées, ratios, poids des piliers) |
| **Historique** (`HistoryPage.jsx`) | Bilan, courbe de valeur (opérations d'un même jour regroupées sous un seul repère), journal paginé avec le conseil donné à ce moment |
| **Profil** (`ProfilePage.jsx`) | Choix du profil de risque, thème, déconnexion |

---

## 7. Les grands parcours, pas à pas

### 7.1 Simuler puis enregistrer une opération (le seul chemin qui écrit)

1. Sur la page Acheter / vendre, le client choisit **Achat** ou **Vente**, l'unité (**montant en euros** ou **nombre d'actions**), coche une ou plusieurs actions et saisit une valeur pour chacune. Le navigateur refuse une valeur vide ou nulle ; en vente, il bloque plus que ce que le client possède ; à l'achat, il bloque une position qui dépasserait la limite du profil (Prudent 10 %, Équilibré 20 % du capital par action ; Dynamique libre avec un avertissement au-delà de 35 %). L'API refait les mêmes contrôles, à la simulation et à l'enregistrement.
2. **« Simuler »** → `POST /api/simulate`. L'API relit les conseils, les cours, le cash et les positions, puis calcule pour chaque ligne le nombre d'actions entier, le reste, le verdict et les raisons. **Rien n'est enregistré.** Si le total dépasse le cash, les dernières lignes sont refusées avec leur raison.
3. **« Valider l'achat »** (désactivé si l'opération est refusée) ouvre la fenêtre de confirmation avec le récapitulatif et le cash après l'opération.
4. **« Valider »** → `POST /api/transactions`. L'API refuse si le conseil a plus de 5 minutes ou si le cours a changé ; sinon elle appelle **une seule fois** la fonction SQL `executer_transaction`, qui revérifie tout et écrit d'un bloc. Le conseil du moment (note, raisons, graine du hasard) est enregistré avec l'opération.
5. Succès : message, données rechargées ; on reste sur la page tant qu'il reste des actions à valider, sinon retour au tableau de bord.

### 7.2 La première connexion, le profil et la déconnexion

- Tant qu'aucun profil n'est choisi, le tableau de bord le signale (`profil.a_choisir`) et le **dialogue de bienvenue** demande le nom et le profil (Prudent, Équilibré, Dynamique). « Commencer » enregistre (`PUT /api/profil`) ; « Plus tard » le referme pour la session.
- Dans **Profil**, on peut changer de profil à tout moment : tous les conseils suivent immédiatement (les notes ne changent pas, seuls les seuils bougent).
- **« Se déconnecter »** (`DELETE /api/profil`) efface le nom et le profil ; l'application se recharge sur le dialogue de bienvenue. Le portefeuille et les opérations sont conservés.

### 7.3 Le garde-fou de perte (RG-01)

Chaque lundi (premier passage de la semaine), la valeur du portefeuille devient la **référence**. Ensuite, performance de la semaine = valeur actuelle / référence − 1. À **−7 %**, bandeau orange sur toutes les pages et plus aucun achat conseillé. À **−10 %**, bandeau rouge, phrase d'alerte en tête des raisons et vente conseillée. Le profil de risque ne change pas ce garde-fou.

---

## 8. Les tests

**181 tests automatiques** vérifient le backend. On les lance depuis `backend/` avec `python -m pytest` (environ 30 secondes). La couverture doit rester au-dessus de 70 % (elle est d'environ 88 %). Ils tournent aussi automatiquement sur chaque Pull Request (GitHub Actions), avec la construction et la vérification du frontend.

| Fichier | Ce qu'il vérifie |
|---|---|
| `test_spec_cases.py` | Les exemples chiffrés de la SPEC, **V1 à V16** : l'application retrouve exactement les mêmes résultats |
| `test_services.py` | Les règles de calcul : seuils, refus du simulateur, formats français, raisons… |
| `test_routes.py` | Les routes de l'API et la **recette REC-1 à REC-4**, le profil, la déconnexion, le simulateur par action |
| `test_refresh.py` | La collecte et l'actualisation (sans réseau) |
| `test_news_nlp.py` | La lecture des articles par Claude, avec un **faux** client (jamais d'appel réel) |
| `test_repository.py` | Les nouvelles tentatives après une coupure et les écritures une par une |
| `test_cache.py` | La mémoire courte de l'API |
| `test_config.py` | Les réglages, RG-04 et les profils |
| `test_main.py` | Le démarrage de l'API, CORS, la connexion |

**Comment tester sans la vraie base ?** `tests/fakes.py` contient une **fausse base en mémoire** (`FakeRepository`, mêmes méthodes que la vraie, mêmes contrôles que `executer_transaction`) et un **faux collecteur** (`FakeCollector`) qui fabrique 2 ans de cours réalistes et des bougies de 5 minutes. Les tests ne touchent jamais Supabase, Internet ou le modèle de langue.

| Recette du cahier des charges | Test |
|---|---|
| REC-1 : les 5 actions ont un conseil, une prévision et un dividende | `test_rec1_…` |
| REC-2 : simuler puis enregistrer en moins de 2 secondes | `test_rec2_…` |
| REC-3 : chaque fiche a ses raisons et son onglet Infos | `test_rec3_…` |
| REC-4 : le garde-fou se déclenche à −10 % | `test_rec4_…` et `test_v15_…` |

---

## 9. Mise en ligne et exploitation

| Partie | Hébergeur | Fichier de réglage |
|---|---|---|
| Interface | **Vercel** — https://finance-orcin-seven.vercel.app | `frontend/vercel.json` |
| API | **Render** — https://portefeuille-500k-api.onrender.com | `render.yaml` |
| Base | **Supabase** | `supabase/` |
| Tâches automatiques | **GitHub Actions** | `.github/workflows/ci.yml` (vérifications), `refresh.yml` (actualisation planifiée) |

**Chaque fusion sur `main` redéploie automatiquement** l'interface (Vercel, environ 1 minute) et l'API (Render, quelques minutes, parfois une dizaine).

**Secrets** : jamais dans Git. En local dans `backend/.env` (modèle : `backend/.env.example`), en ligne dans les variables de Render : `SUPABASE_URL`, `SUPABASE_KEY`, `NEWS_API_KEY`, `ANTHROPIC_API_KEY`, `CORS_ORIGINS` (adresses autorisées à appeler l'API), et éventuellement `SEUIL_ACHAT` / `SEUIL_VENTE`.

**Avant une démonstration** : l'offre gratuite de Render endort l'API après 15 minutes sans visite (30 à 60 secondes de réveil). Ouvrez https://portefeuille-500k-api.onrender.com/api/health une minute avant.

**Commandes utiles** (depuis `backend/`, environnement activé) :

```bash
python -m uvicorn main:app --reload --port 8000   # lancer l'API en local
python -m pytest                                  # lancer les tests
python -m tools.check_supabase                    # vérifier la connexion (lecture seule)
python -m tools.refresh                           # actualiser les données à la main
```

et depuis `frontend/` : `npm run dev` (lancer l'interface), `npm run build` et `npm run lint` (vérifier avant un commit).

---

## 10. Limites connues et pistes

- **Pas de pouvoir prédictif démontré.** Sur un essai d'un an (D-10), les conseils ne battent pas nettement le hasard. L'application est un **outil d'aide à la décision**, pas une promesse de gain ; l'objectif de +10 % par semaine est **visé**, jamais garanti.
- **Notes souvent proches de 50.** La moyenne de 4 piliers rapproche la note du neutre ; c'est pourquoi le choix du profil (seuils) compte beaucoup.
- **Pas de vrais comptes.** Un seul portefeuille partagé ; « se déconnecter » efface le nom et le profil pour tout le groupe. Un vrai système de comptes demanderait une authentification (par exemple Supabase Auth).
- **Données gratuites.** Yahoo Finance (via `yfinance`) n'est pas une API officielle et a environ 15 minutes de retard ; NewsAPI gratuit a environ 24 h de retard et 100 requêtes par jour.
- **Hébergement gratuit.** L'API s'endort après 15 minutes sans visite ; la tâche planifiée de GitHub peut être retardée (d'où l'actualisation à la consultation).
- **Lecture des articles par un modèle de langue.** Claude Haiku 5.5 coûte quelques centimes par jour ; sans clé, l'application revient au lexique de mots-clés, moins fin.

---

## 11. Questions fréquentes : « comment je change… »

| Je veux… | Où et comment |
|---|---|
| Changer le poids d'un pilier | `config.py`, `POIDS` (le total doit faire 1 et les Infos rester le plus fort, sinon l'API refuse de démarrer), puis lancer les tests |
| Changer les seuils d'un profil | `config.py`, `PROFILS_RISQUE` |
| Changer les seuils par défaut en ligne | Variables `SEUIL_ACHAT` / `SEUIL_VENTE` dans Render |
| Changer l'alerte de perte | `config.py`, `ALERTE_APPROCHE_PCT` / `ALERTE_ATTEINT_PCT` |
| Changer le modèle qui lit les actualités | `config.py`, `NLP_MODELE` ; les consignes données au modèle sont dans `services/news_nlp.py` (`SYSTEM_PROMPT`) |
| Ajouter une action au périmètre | Ajouter la ligne dans la table `actions` (comme dans `supabase/seed.sql`), puis dans `config.py` : `TICKERS`, `NEWS_QUERIES`, `NEWS_MOTS_CLES` ; côté interface : `frontend/src/lib/stocks.js` et une couleur dans la charte |
| Changer une phrase des raisons | `services/decision_engine.py`, `TECH_PHRASES` et `build_reasons` |
| Changer une couleur | `docs/charte/tokens.css`, puis la copier dans `frontend/src/styles/tokens.css` (jamais de couleur en dur dans un composant) |
| Ajouter une page | Un fichier dans `frontend/src/pages/`, une ligne dans `App.jsx`, un onglet dans `NavBar.jsx` si besoin |
| Modifier la structure de la base | Un nouveau fichier `supabase/migrations/00X_….sql`, relu par le groupe, exécuté dans l'éditeur SQL de Supabase |

Dans tous les cas : une branche, les tests (`python -m pytest`, `npm run build`), puis une Pull Request relue (jamais de commit direct sur `main`).

---

## 12. Glossaire

| Terme | Explication |
|---|---|
| **API** | Le programme serveur auquel l'interface pose ses questions (« donne-moi le tableau de bord ») et qui répond en JSON |
| **Route** | Une adresse de l'API, par exemple `GET /api/dashboard` |
| **JSON** | Un format de texte pour échanger des données structurées |
| **Actualisation** | Le passage qui va chercher les données dehors et recalcule les conseils |
| **Pilier** | L'un des 4 groupes de critères notés sur 100 : Informations, Graphique, Ratios, Hasard |
| **Signal** | La lecture d'un indicateur entre −1 (vendre) et +1 (acheter) |
| **Moyenne mobile (MM20, MM50, MM200)** | La moyenne des cours des 20, 50 ou 200 derniers jours ; montre la tendance de fond |
| **Bandes de Bollinger** | Un « couloir » autour de la moyenne sur 20 jours (± 2 écarts-types) ; un cours en bas du couloir est bas par rapport à son habitude |
| **RSI** | Indice de 0 à 100 qui compare les hausses et les baisses des 14 derniers jours ; ≤ 30 : a beaucoup baissé, ≥ 70 : a beaucoup monté |
| **MACD** | L'écart entre une moyenne courte (12 jours) et une longue (26 jours) ; son croisement avec sa propre moyenne (9 jours) signale un changement de dynamique |
| **Bougie** | La représentation d'une période de cotation (ouverture, plus haut, plus bas, clôture) ; verte si le cours a monté, rouge s'il a baissé |
| **Volatilité (σ)** | L'ampleur habituelle des variations d'une semaine à l'autre |
| **Rendement du dividende** | Dividende annuel / cours de l'action, en % |
| **Sentiment** | L'effet probable d'une nouvelle pour l'actionnaire, de −1 à +1 |
| **Modèle de langue** | Un programme d'intelligence artificielle qui lit et comprend du texte (ici Claude Haiku 5.5) |
| **Migration** | Un fichier SQL qui modifie la structure de la base, numéroté et relu avant exécution |
| **CORS** | La règle qui dit quels sites ont le droit d'appeler l'API depuis un navigateur |
| **Pull Request** | Une demande de fusion d'une branche dans `main`, relue avant d'être acceptée |
| **`Decimal`** | Un type de nombre exact, utilisé pour l'argent (les nombres à virgule flottante font des erreurs d'arrondi) |
