# Guide du code — Portefeuille 500k

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

1. Chaque article reçoit une note d'impact quand il est collecté. `sentiment.py` cherche des mots positifs (« hausse », « contrat », « record »…) et négatifs (« baisse », « avertissement »…), en français et en anglais, et en tire un sentiment entre −1 et +1. Une **annonce officielle** (résultats, contrat, fusion, dirigeant) compte double.
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

Lancement depuis `backend/` : `python -m pytest`. La couverture doit rester au-dessus de 70 %.

## 5. La collecte et l'actualisation

### 5.1 Qui fait quoi

| Fichier | Rôle |
|---|---|
| `db/repository.py` | **Le seul endroit qui parle à Supabase.** Il traduit « donne-moi les cours de DSY.PA » ou « enregistre ces notes » en requêtes. Le reste du code ne connaît pas Supabase. |
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

### 5.3 Deux précisions de calcul

- **Dividende annuel** : certaines entreprises versent 4 fois par an (TotalEnergies). Si on additionne simplement les versements d'une année civile, un versement daté du 2 janvier ou du 31 décembre fausse tout (+35 % au lieu de +8 %). On prend donc le versement moyen de l'année × le nombre habituel de versements.
- **Dividende attendu** (pour le dividende estimé) : la somme des dividendes versés sur les 12 derniers mois.

### 5.4 Les tests sans base ni réseau

`tests/fakes.py` contient une **fausse base en mémoire** (`FakeRepository`) et un **faux collecteur** (`FakeCollector`) qui fabrique 2 ans de cours réalistes. Les tests de `test_refresh.py` vérifient l'actualisation complète sans jamais toucher Supabase ni Internet : 5 conseils enregistrés, pas de doublon quand on relance, survie aux pannes, ouverture de la semaine.
