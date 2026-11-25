# AmountInput

Champ du montant en euros dans le simulateur.

- Saisie alignée à droite, chiffres tabulaires, symbole « € » fixe à droite.
- Sous le champ : le cash disponible en aide ; en cas d'erreur, l'aide est remplacée par le message en `sell`.
- Messages d'erreur : « Saisissez un montant supérieur à 0 », « Vous disposez de 450 027,20 € ».
- La bordure est `line-strong` (contraste 3:1), rouge en cas d'erreur, avec l'anneau `focus` au clavier.
