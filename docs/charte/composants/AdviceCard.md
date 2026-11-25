# AdviceCard

Résultat du simulateur pour une action : conseil, verdict, chiffres de l'opération, prévision et raisons.

- Ordre fixe : nom et conseil, verdict, chiffres (actions, montant investi, reste en cash, dividende), prévision, raisons.
- Le verdict reprend la réponse de `POST /api/simulate` : « Vous pouvez valider » (`buy`), « Ne rien faire pour l'instant » (`hold`), « Privilégier la vente » ou « Opération refusée » (`sell`).
- 2 à 4 raisons, en phrases simples (RG-03).
- Les boutons « Annuler » et « Valider l'achat » se placent en bas de la carte ; « Valider » est désactivé si le verdict est « Refusé ».
