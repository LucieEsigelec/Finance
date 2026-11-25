"""Vérifie la connexion à Supabase, en LECTURE SEULE.

En bref : se connecte avec les valeurs de ``backend/.env``, compte les lignes des
7 tables du DCT et affiche les 5 actions. N'écrit rien dans la base.

Lancement depuis ``backend/`` : ``python -m tools.check_supabase``
"""

from __future__ import annotations

import sys

from config import TICKERS
from db.supabase_client import get_client

TABLES = (
    "actions",
    "historique_cours",
    "ratios_financiers",
    "actualites",
    "scores_actions",
    "portefeuille",
    "transactions",
)


def main() -> int:
    client = get_client()

    print("Tables (nombre de lignes) :")
    for table in TABLES:
        result = client.table(table).select("*", count="exact", head=True).execute()
        print(f"  {table:<18} {result.count}")

    actions = client.table("actions").select("ticker, nom, dernier_cours").order("ticker").execute().data
    print("\nActions :")
    for row in actions:
        print(f"  {row['ticker']:<7} {row['nom']:<20} {row['dernier_cours']}")

    missing = sorted(set(TICKERS) - {row["ticker"] for row in actions})
    if missing:
        print(f"\nATTENTION : actions absentes de la base : {', '.join(missing)}")
        return 1
    print("\nConnexion OK : les 5 actions du périmètre sont présentes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
