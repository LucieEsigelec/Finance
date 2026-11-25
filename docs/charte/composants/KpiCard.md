# KpiCard

Carte chiffrée du tableau de bord : un libellé, une valeur, et éventuellement une variation.

- 4 cartes sur une ligne : Capital total, Cash disponible, Performance de la semaine, Part investie.
- La valeur utilise le style `kpi` (28 px, chiffres tabulaires). Le libellé est en `label`, en majuscules.
- La variation porte son signe et sa flèche ; elle est verte si positive, rouge si négative.
- Le composant reçoit une valeur **déjà formatée** (`Pf500.format.eur`) : il ne calcule rien.
