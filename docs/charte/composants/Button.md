# Button

Bouton d'action, toujours avec un verbe en tête (« Simuler », « Valider l'achat », « Actualiser les données »).

| Variante | Quand |
| --- | --- |
| `primary` | L'action principale de l'écran, **une seule** : « Simuler » dans le simulateur. |
| `secondary` | Par défaut : « Actualiser les données », « Annuler ». |
| `ghost` | Action discrète dans un tableau ou une carte : « Voir la fiche ». |
| `buy` / `sell` | Uniquement dans la fenêtre de confirmation : « Valider l'achat » ou « Valider la vente ». |

- Hauteur 40 px (32 px pour `size="sm"` dans les tableaux), rayon `radius-md`, police 15 px semi-grasse.
- Désactivé quand le verdict est « Refusé » ou pendant l'envoi ; le libellé devient alors « Envoi… ».
- Ne jamais mettre deux boutons `primary` côte à côte.
