# Maquettes de l'interface

Maquettes validées des écrans de l'application. Elles utilisent la charte (`docs/charte/`) et des **données d'exemple** fictives mais cohérentes entre les écrans (sauf l'écran d'alerte, qui montre un autre portefeuille investi à 93 %).

Version en ligne, avec prototype cliquable : https://claude.ai/artifact/R6A3F9BZ2hN9YU8wG35xCC

## Captures (`captures/`)

| Fichier | Écran | Route |
| --- | --- | --- |
| `01_accueil.png` | Accueil « Bonjour M. X » | `/` |
| `02_tableau_de_bord.png` | Tableau de bord | `/tableau-de-bord` |
| `03_simulateur.png` | Simulateur (onglet séparé) | `/simulateur` |
| `04_confirmation.png` | Fenêtre de confirmation au-dessus du simulateur | — |
| `05_tableau_de_bord_alerte.png` | Tableau de bord quand la perte de la semaine atteint −10 % | `/tableau-de-bord` |
| `06_fiche_action_graphique.png` | Fiche action, onglet Graphique | `/action/:ticker` |
| `07_fiche_action_infos.png` | Fiche action, onglet Infos sur l'action | `/action/:ticker` |
| `08_historique.png` | Historique | `/historique` |

Captures en 1440 px de large. Sur mobile, tout passe en une colonne (voir la charte, section Mise en page).

## Sources (`sources/*.dc.html`)

Le balisage exact de chaque écran : HTML avec styles en ligne et variables CSS de la charte (`var(--brand)`, `var(--space-4)`…). À lire pour retrouver les tailles, espacements et textes exacts. Ce ne sont **pas** des fichiers à exécuter ni à copier tels quels dans le frontend.

Conventions du format :

- `<x-import component-from-global-scope="Pf500.KpiCard" label="…">` = un composant de la charte (ici `KpiCard`) avec ses props. À remplacer par le composant React correspondant (`docs/charte/composants/`).
- `<dc-import name="NavBar">` = la barre de navigation commune (`NavBar.dc.html`).
- `<sc-for list="{{rows}}" as="r">` = une boucle ; `{{r.name}}` = une valeur de la ligne.
- Le bloc `<script type="text/x-dc">` en bas contient les données d'exemple de l'écran (`renderVals()`).
- Les graphiques sont des SVG statiques dessinés pour la maquette ; dans l'application, ils seront faits avec TradingView Lightweight Charts (cours) et Recharts (performance).
