# AlertBanner

Bandeau de l'alerte de perte de la semaine (RG-01), affiché sous la barre de navigation, sur toute la largeur et sur toutes les pages.

| Niveau | Quand | Rendu |
| --- | --- | --- |
| `AUCUN` | perte inférieure à 7 % | rien n'est affiché |
| `APPROCHE` | perte entre 7 % et 10 % | fond `warn-soft`, icône `warn`, texte `ink` |
| `ATTEINT` | perte de 10 % ou plus | fond `sell` plein, texte `on-sell`, rôle ARIA `alert` |

- C'est le seul fond rouge plein de l'application.
- Le texte dit le chiffre et la conséquence pour le client ; il ne se ferme pas tant que le niveau reste actif.
