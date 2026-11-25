# Portefeuille 500k — charte graphique

> **Version fichier de la charte**, pour le dépôt. Les aperçus en direct (thème clair et sombre) sont sur la charte en ligne : https://claude.ai/artifact/8DHsZrC4sVnTsV5pBYBNeG
>
> Fichiers de ce dossier : `tokens.json` (source des valeurs), `tokens.css` (les mêmes valeurs en variables CSS, à importer dans le frontend), `bundle.css` / `bundle.js` / `index.d.ts` (implémentation de référence des 8 composants, à **réécrire** en composants React + Tailwind dans `frontend/src/components/ui/`, pas à importer tel quel), `composants/*.md` (règles d'usage de chaque composant).

Cette charte définit l'apparence de l'application d'aide à la décision sur le portefeuille de 500 000 €. Elle couvre les couleurs, la typographie, la mise en page, les graphiques et les composants des écrans : accueil, tableau de bord, simulateur, fiche action et historique. Elle s'applique au frontend React 18 + Vite + Tailwind + shadcn/ui décrit dans le dossier de conception.

> L'application n'a pas encore de logo. En attendant, le nom « Portefeuille 500k » s'écrit en texte, police Inter 600, couleur `ink`.

## 1. Principes

1. **Le conseil d'abord.** Sur chaque écran, le client doit voir en moins de 3 secondes le conseil (Achat, Vente ou Rien), la valeur du portefeuille et l'état de l'alerte de perte. Le reste est secondaire.
2. **Sobre et sérieux.** C'est un outil de gestion d'argent, pas un jeu : fonds clairs, peu d'ombres, pas de dégradés, pas d'animations décoratives. La couleur sert à **signaler**, pas à décorer.
3. **Honnête sur le risque.** Les pertes et les alertes sont aussi visibles que les gains. Une prévision montre toujours ses trois scénarios, jamais le seul scénario favorable.
4. **Lisible par tous.** Tout texte atteint un contraste de 4.5:1 dans les deux thèmes. Une information n'est **jamais portée par la couleur seule** : un conseil a toujours son mot et son signe (▲ ACHAT, ▼ VENTE, ■ RIEN).

## 2. Ton et rédaction

- L'application vouvoie le client : « Vous disposez de 450 027,20 € ».
- Phrases courtes, verbe d'action en tête sur les boutons : « Simuler », « Valider l'achat », « Actualiser les données ».
- Pas de jargon non expliqué. On écrit « Le cours est proche du bas de sa fourchette habituelle » plutôt que « %B = 0,1 ».
- Pas de points d'exclamation, pas d'emoji, pas de promesses (« gain assuré »).
- Les conseils sont des **aides**, jamais des ordres : « Conseil : ACHAT », pas « Achetez ! ».

### Format des nombres (français)

| Donnée | Format | Exemple |
| --- | --- | --- |
| Montant | espace fine insécable pour les milliers, virgule, 2 décimales, symbole après | 49 972,80 € |
| Grand montant (KPI) | sans décimales au-delà de 100 000 € | 500 000 € |
| Pourcentage | signe toujours affiché, 1 décimale, espace avant % | +3,2 % · −1,8 % |
| Cours | 2 décimales | 34,80 € |
| Nombre d'actions | entier, séparateur de milliers | 1 436 actions |
| Date | jour mois année, heure 24 h | 24 nov. 2026, 18:02 |
| Code boursier | police mono, majuscules | DSY.PA |

Le signe moins est le vrai signe « − » (U+2212), pas un tiret. En code : `Intl.NumberFormat('fr-FR', …)` avec `signDisplay: 'always'` pour les variations.

## 3. Couleurs

Toutes les couleurs sont des tokens à deux valeurs (thème **Clair** et thème **Sombre**). Dans le code, on utilise toujours la variable CSS (`var(--buy)`), jamais la valeur en dur.

### Les familles

| Famille | Tokens | Rôle |
| --- | --- | --- |
| Surfaces | `surface-page`, `surface-card`, `surface-sunken`, `line`, `line-strong` | Fonds et bordures |
| Texte | `ink`, `ink-muted` | Texte principal et secondaire |
| Marque | `brand`, `on-brand`, `brand-soft`, `focus` | Actions principales, liens, sélection |
| Signaux de conseil | `buy`, `sell`, `hold` et leurs `-soft` / `on-` | Achat, Vente, Rien, hausse et baisse |
| Alerte | `warn`, `warn-soft` (APPROCHE) ; `sell`, `on-sell` (ATTEINTE) | Alerte de perte RG-01 |
| Graphiques | `chart-dsy` … `chart-ai`, `chart-ma20`, `chart-ma50`, `chart-ma200`, `chart-grid` | Une couleur fixe par titre et par indicateur |

### Règles

- **La couleur de marque n'est pas un conseil.** `brand` (bleu pétrole) sert aux boutons et aux liens ; il ne signifie jamais « acheter ».
- **Vert = Achat, rouge = Vente, gris = Rien**, et seulement pour cela (plus hausse, baisse et gain ou perte). Pas de vert décoratif.
- **Un seul fond plein de signal par écran** : le bandeau d'alerte rouge, ou le bouton « Valider la vente ». Ailleurs, on utilise les versions `-soft` (badges).
- **Vert et rouge ne se distinguent pas par la teinte seule** : `buy` et `sell` sont toujours accompagnés de ▲ / ▼ et du mot, pour les daltoniens.
- **Les 5 titres gardent la même couleur partout** (courbes comparées, légendes, historique) : DSY bleu, TTE ambre, CAP violet, RMS sarcelle, AI framboise.

### Contrastes vérifiés

| Texte | Sur | Clair | Sombre |
| --- | --- | --- | --- |
| `ink` | `surface-card` | 17.6:1 | 14.1:1 |
| `ink-muted` | `surface-sunken` (le pire cas) | 5.9:1 | 6.2:1 |
| `buy` | `buy-soft` | 5.3:1 | 6.9:1 |
| `sell` | `sell-soft` | 5.6:1 | 6.2:1 |
| `hold` | `hold-soft` | 5.5:1 | 6.4:1 |
| `warn` | `warn-soft` | 5.4:1 | 7.3:1 |
| `on-brand` | `brand` | 7.6:1 | 6.9:1 |
| `line-strong` (bordure de champ) | `surface-card` | 3.0:1 | 3.1:1 |

## 4. Typographie

- **Inter** (Google Fonts) pour toute l'interface, en 400, 500, 600 et 700. Repli : Segoe UI sous Windows.
- **IBM Plex Mono** 500 uniquement pour les codes boursiers (`DSY.PA`).
- **Chiffres tabulaires obligatoires** dans les tableaux et les KPI (`font-variant-numeric: tabular-nums`) : les colonnes de montants restent alignées.
- Montants et pourcentages **alignés à droite** dans les tableaux.
- 7 styles seulement (voir l'onglet Typographie) : `display`, `h1`, `h2`, `body`, `body-sm`, `label`, `kpi`, plus `number` et `ticker`. Pas d'autre taille.

## 5. Mise en page

- **Grille** de 12 colonnes, largeur maximale 1 280 px, gouttière `space-6` (24 px), marges latérales 24 px (16 px sous 768 px).
- **Espacements** sur une base de 4 px : `space-1` (4) à `space-12` (48). Aucune valeur hors de cette échelle.
- **Cartes** : fond `surface-card`, bordure 1 px `line`, rayon `radius-lg`, marge intérieure `space-4` à `space-6`, ombre `shadow-card`.
- **Barre de navigation** fixe en haut, 64 px, fond `surface-card`, bordure basse `line`. Le bandeau d'alerte se place juste dessous, sur toute la largeur.

### Disposition des écrans

| Écran | Disposition sur ordinateur (≥ 1 024 px) | Sur mobile |
| --- | --- | --- |
| Tableau de bord | Ligne de 4 cartes KPI (3 colonnes chacune) ; dessous, tableau des 5 actions (8 colonnes) et simulateur (4 colonnes) côte à côte | Tout en une colonne, simulateur après le tableau |
| Fiche action | En-tête ; graphique (8 colonnes) et colonne droite (4) avec conseil, prévision, dividende ; onglets en dessous | Une colonne, graphique pleine largeur |
| Historique | Filtres ; courbe de performance pleine largeur ; bilan (4 cartes) ; journal des opérations | Une colonne, tableau défilant horizontalement |

## 6. Graphiques

- **Graphique de cours** (TradingView Lightweight Charts) : bougies `buy` (hausse) et `sell` (baisse), quadrillage `chart-grid`, fond transparent.
- **Indicateurs** sur le graphique : MM20 `chart-ma20`, MM50 `chart-ma50`, MM200 `chart-ma200` (traits de 1,5 px) ; bandes de Bollinger en zone `brand-soft` bordée de `brand` à 1 px.
- **RSI et MACD** dans deux petits panneaux de 96 px sous le graphique : ligne `brand`, lignes repères 30 et 70 du RSI en pointillés `line-strong`, histogramme du MACD en `buy` / `sell`.
- **Courbe de performance** (Recharts) : ligne `brand` 2 px, ligne horizontale pointillée des 500 000 € de départ en `ink-muted`.
- **Comparaison de titres** : une couleur fixe par titre (section 3). Légende toujours visible, jamais seulement au survol.
- Pas de graphique en 3D, pas de camembert pour plus de 5 parts, pas de double axe vertical.

## 7. Iconographie

- Bibliothèque **Lucide** (fournie avec shadcn/ui), trait 1,75 px, taille 16 px dans le texte et 20 px dans les boutons. Les icônes prennent la couleur du texte (`currentColor`).
- Icônes fixes : `TrendingUp` (hausse), `TrendingDown` (baisse), `TriangleAlert` (alerte), `RefreshCw` (actualiser), `History` (historique), `Info` (aide).
- Une icône seule n'est jamais un bouton sans libellé accessible (`aria-label`).

## 8. États et interactions

| État | Rendu |
| --- | --- |
| Survol d'une ligne | fond `surface-sunken` |
| Focus clavier | anneau `focus` de 2 px, décalé de 2 px, sur tout élément interactif |
| Désactivé | opacité 0,5, curseur interdit, pas de survol |
| Chargement | squelette `surface-sunken` à la forme du contenu ; pas de spinner plein écran |
| Erreur | message `sell` sous le champ, ou `Toast` sur fond `sell-soft` |
| Données anciennes | badge `warn` « Données du 23 nov. » dans l'en-tête |

Les transitions durent 150 ms maximum (couleur de fond, opacité). Aucune animation quand l'utilisateur a choisi « réduire les animations ».

## 9. Utilisation avec Tailwind et shadcn/ui

Les tokens deviennent des variables CSS (fichier `tokens.css` généré par cette charte). Dans `tailwind.config.js`, on les branche par nom :

```js
theme: { extend: {
  colors: {
    page: 'var(--surface-page)', card: 'var(--surface-card)', sunken: 'var(--surface-sunken)',
    line: 'var(--line)', ink: 'var(--ink)', muted: 'var(--ink-muted)',
    brand: { DEFAULT: 'var(--brand)', soft: 'var(--brand-soft)', on: 'var(--on-brand)' },
    buy:  { DEFAULT: 'var(--buy)',  soft: 'var(--buy-soft)',  on: 'var(--on-buy)' },
    sell: { DEFAULT: 'var(--sell)', soft: 'var(--sell-soft)', on: 'var(--on-sell)' },
    hold: { DEFAULT: 'var(--hold)', soft: 'var(--hold-soft)' },
    warn: { DEFAULT: 'var(--warn)', soft: 'var(--warn-soft)' },
  },
  borderRadius: { sm: 'var(--radius-sm)', md: 'var(--radius-md)', lg: 'var(--radius-lg)' },
  fontFamily: { sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'], mono: ['IBM Plex Mono', 'Consolas', 'monospace'] },
}}
```

Le thème sombre s'active avec l'attribut `data-theme="dark"` sur `<html>`. Le thème clair est celui par défaut.

## 10. Composants

Les règles d'usage de chaque composant sont dans `composants/` ; les aperçus en direct sont sur la charte en ligne. Ils correspondent aux composants du DSL :

| Composant de la charte | Utilisé dans (voir `docs/04_dossier_interface.md`) |
| --- | --- |
| `Button` | `SimulateButton`, `NavBar` (Actualiser), `SimulateLink`, `ConfirmDialog`, `Pagination` |
| `DecisionBadge` | `StocksTable`, `WeeklyAdvice`, `StockHeader`, `RecommendationCard`, `TransactionsTable` |
| `KpiCard` | `SummaryCards`, `KpiCards`, `HistorySummary` |
| `AlertBanner` | `AlertBanner` (RG-01) |
| `AmountInput` | `AmountInput` du simulateur |
| `StockCheckbox` | `StockCheckboxes` du simulateur |
| `ForecastBar` | `ForecastCard`, `AdviceCard` |
| `AdviceCard` | Résultat du simulateur |
