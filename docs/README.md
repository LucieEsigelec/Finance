# Documentation du projet

## Ordre de lecture

| # | Fichier | Contenu | Fait foi pour |
| --- | --- | --- | --- |
| 1 | `01_cahier_des_charges.md` | Besoins du client, exigences EF / ENF, règles RG-01 à RG-06, recette | Le besoin |
| 2 | `02_dossier_conception.md` | Architecture, 7 tables (SQL), services, routes de l'API | Architecture, tables, routes |
| 3 | `03_specification.md` | Formules des 4 piliers, décision, prévision, simulateur, 16 cas de test, annexe JSON / SQL | Calculs et seuils |
| 4 | `04_dossier_interface.md` | Écrans, navigation, composants, connexions, interactions, charte | Pages, routes React, composants |
| 5 | `charte/` | Tokens (couleurs, typo, espacements) et règles des 8 composants | Apparence |
| 6 | `maquettes/` | Captures et balisage de chaque écran | Disposition des écrans |
| 7 | `05_guide_du_code.md` | Explication simple de tout le code, étape par étape | Comprendre et présenter le code |
| 8 | `06_deploiement.md` | Mise en ligne : Render, Vercel, GitHub Actions | Déploiement |
| — | `decisions.md` | Journal des décisions prises pendant le développement | Choix et écarts |

Le dossier interface (4) est le plus récent : il ajoute une **page d'accueil** et sépare le **simulateur** du tableau de bord. Là où le dossier de conception ou la spécification parlent d'un `SimulatorPanel` intégré au tableau de bord, c'est le dossier interface qui s'applique.

## Autres fichiers

- `sources/` : documents originaux (PDF du cahier des charges, Word du dossier de conception, PDF de la spécification et du dossier interface avec leurs schémas).
- `img/` : schémas extraits des documents (UML, algorigramme, architecture, navigation, séquence).

## Versions en ligne (lecture et commentaires)

- Spécification : https://claude.ai/artifact/7ynAqb5UjxCkAHykHiSmdC
- Dossier interface : https://claude.ai/artifact/2iwJp2gC11iZqSwPfwXCvG
- Charte graphique : https://claude.ai/artifact/8DHsZrC4sVnTsV5pBYBNeG
- Maquettes (prototype cliquable) : https://claude.ai/artifact/R6A3F9BZ2hN9YU8wG35xCC
