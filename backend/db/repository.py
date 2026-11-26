"""Accès aux données : toutes les lectures et écritures de la base passent par ici.

En bref : ``SupabaseRepository`` traduit des demandes simples (« donne-moi les cours de
DSY.PA », « enregistre ces notes ») en requêtes Supabase. Le reste du code ne connaît
pas Supabase : il parle à ce « dépôt ». Dans les tests, on le remplace par une fausse
base en mémoire (``tests/fakes.py``), pour ne jamais toucher la base partagée.

Règles respectées (CLAUDE.md §5, §6.2) :
- les montants sont relus en ``Decimal`` ;
- une opération du client s'enregistre **uniquement** par la fonction SQL
  ``executer_transaction`` (un seul appel, tout ou rien) ;
- aucune suppression : on ajoute ou on met à jour.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pandas as pd

PAGE = 1000  # nombre maximal de lignes renvoyées par Supabase en une fois


class TransactionRefused(Exception):
    """La fonction SQL a refusé l'opération (RG-05) : rien n'a été écrit."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _dec(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _ts(value: str | datetime) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))


class SupabaseRepository:
    def __init__(self, client):
        self.client = client

    def _all(self, query) -> list[dict[str, Any]]:
        rows, start = [], 0
        while True:
            batch = query.range(start, start + PAGE - 1).execute().data
            rows.extend(batch)
            if len(batch) < PAGE:
                return rows
            start += PAGE

    # --- actions -----------------------------------------------------------------

    def get_actions(self) -> list[dict[str, Any]]:
        rows = self.client.table("actions").select("*").order("ticker").execute().data
        for row in rows:
            row["dernier_cours"] = _dec(row["dernier_cours"])
            row["dividende_estime"] = _dec(row["dividende_estime"])
        return rows

    def update_action(self, action_id: str, **fields: Any) -> None:
        payload = {k: (str(v) if isinstance(v, Decimal) else v) for k, v in fields.items()}
        self.client.table("actions").update(payload).eq("id", action_id).execute()

    # --- cours -------------------------------------------------------------------

    def get_history(self, action_id: str, since: date | None = None) -> pd.DataFrame:
        query = self.client.table("historique_cours").select(
            "date_seance, open, high, low, close, volume"
        ).eq("action_id", action_id)
        if since:
            query = query.gte("date_seance", since.isoformat())
        rows = self._all(query.order("date_seance"))
        df = pd.DataFrame(rows, columns=["date_seance", "open", "high", "low", "close", "volume"])
        if not df.empty:
            df["date_seance"] = pd.to_datetime(df["date_seance"]).dt.date
            for col in ("open", "high", "low", "close"):
                df[col] = df[col].astype(float)
        return df

    def last_history_date(self, action_id: str) -> date | None:
        rows = (
            self.client.table("historique_cours").select("date_seance").eq("action_id", action_id)
            .order("date_seance", desc=True).limit(1).execute().data
        )
        return date.fromisoformat(rows[0]["date_seance"]) if rows else None

    def upsert_history(self, rows: list[dict[str, Any]]) -> int:
        for start in range(0, len(rows), 500):
            self.client.table("historique_cours").upsert(
                rows[start:start + 500], on_conflict="action_id,date_seance"
            ).execute()
        return len(rows)

    # --- cours intrajournaliers (migration 004, D-12) -------------------------------

    def upsert_intraday(self, rows: list[dict[str, Any]]) -> int:
        for start in range(0, len(rows), 500):
            self.client.table("cours_intraday").upsert(
                rows[start:start + 500], on_conflict="action_id,horodatage"
            ).execute()
        return len(rows)

    def purge_intraday(self, before: datetime) -> None:
        """Supprime les bougies plus anciennes que ``before`` (toujours avec une condition)."""
        self.client.table("cours_intraday").delete().lt("horodatage", before.isoformat()).execute()

    def oldest_intraday(self, action_id: str) -> datetime | None:
        rows = (
            self.client.table("cours_intraday").select("horodatage").eq("action_id", action_id)
            .order("horodatage").limit(1).execute().data
        )
        return _ts(rows[0]["horodatage"]) if rows else None

    def get_intraday(self, action_id: str, since: datetime | None = None) -> pd.DataFrame:
        query = self.client.table("cours_intraday").select("horodatage, open, high, low, close, volume")
        query = query.eq("action_id", action_id)
        if since:
            query = query.gte("horodatage", since.isoformat())
        rows = self._all(query.order("horodatage"))
        df = pd.DataFrame(rows, columns=["horodatage", "open", "high", "low", "close", "volume"])
        if not df.empty:
            df["horodatage"] = pd.to_datetime(df["horodatage"], utc=True)
            for col in ("open", "high", "low", "close"):
                df[col] = df[col].astype(float)
        return df

    # --- ratios ------------------------------------------------------------------

    def get_ratios(self, action_id: str) -> list[dict[str, Any]]:
        """Exercices du plus récent au plus ancien."""
        return (
            self.client.table("ratios_financiers").select("*").eq("action_id", action_id)
            .order("date_maj", desc=True).execute().data
        )

    def save_ratios(self, action_id: str, rows: list[dict[str, Any]]) -> int:
        """Ajoute les exercices absents et met à jour ceux déjà présents (même date)."""
        existing = {r["date_maj"]: r["id"] for r in self.get_ratios(action_id)}
        new = [r for r in rows if r["date_maj"] not in existing]
        for row in rows:
            if row["date_maj"] in existing:
                self.client.table("ratios_financiers").update(row).eq("id", existing[row["date_maj"]]).execute()
        if new:
            self.client.table("ratios_financiers").insert(new).execute()
        return len(new)

    # --- actualités --------------------------------------------------------------

    def get_articles(self, action_id: str, since: datetime) -> list[dict[str, Any]]:
        rows = (
            self.client.table("actualites").select("*").eq("action_id", action_id)
            .gte("date_pub", since.isoformat()).order("date_pub", desc=True).execute().data
        )
        for row in rows:
            row["date_pub"] = _ts(row["date_pub"])
        return rows

    def insert_missing_articles(self, action_id: str, articles: list[dict[str, Any]], since: datetime) -> int:
        known = self.get_articles(action_id, since)
        seen_urls = {a["url"] for a in known if a.get("url")}
        seen_titles = {a["titre"].strip().lower() for a in known}
        new = []
        for article in articles:
            key = article["titre"].strip().lower()
            if article.get("url") in seen_urls or key in seen_titles:
                continue
            seen_urls.add(article.get("url"))
            seen_titles.add(key)
            new.append({**article, "action_id": action_id, "date_pub": article["date_pub"].isoformat()})
        if new:
            self.client.table("actualites").insert(new).execute()
        return len(new)

    # --- scores ------------------------------------------------------------------

    def insert_scores(self, rows: list[dict[str, Any]]) -> None:
        self.client.table("scores_actions").insert(rows).execute()

    def latest_scores(self) -> dict[str, dict[str, Any]]:
        """Dernière ligne de scores_actions pour chaque action (clé : action_id).
        Une actualisation écrit les 5 lignes ensemble : les 10 plus récentes suffisent."""
        rows = (
            self.client.table("scores_actions").select("*").order("date_calcul", desc=True)
            .limit(10).execute().data
        )
        latest: dict[str, dict[str, Any]] = {}
        for row in rows:
            latest.setdefault(row["action_id"], row)
        return latest

    # --- portefeuille et opérations ---------------------------------------------

    def get_portfolio(self) -> dict[str, Any]:
        row = self.client.table("portefeuille").select("*").limit(1).execute().data[0]
        for key in ("capital_initial", "cash_disponible", "val_semaine_prec"):
            row[key] = _dec(row[key])
        row["date_ref_semaine"] = date.fromisoformat(row["date_ref_semaine"])
        return row

    def update_portfolio_week(self, portfolio_id: str, value: Decimal, monday: date) -> None:
        self.client.table("portefeuille").update(
            {"val_semaine_prec": str(value), "date_ref_semaine": monday.isoformat()}
        ).eq("id", portfolio_id).execute()

    def get_transactions(self, portfolio_id: str) -> list[dict[str, Any]]:
        rows = self._all(
            self.client.table("transactions").select("*, actions(ticker, nom)")
            .eq("portefeuille_id", portfolio_id).order("date_execution")
        )
        for row in rows:
            action = row.pop("actions") or {}
            row["ticker"], row["nom"] = action.get("ticker"), action.get("nom")
            row["prix_unitaire"] = _dec(row["prix_unitaire"])
            row["montant_total"] = _dec(row["montant_total"])
            row["date_execution"] = _ts(row["date_execution"])
        return rows

    def execute_transaction(
        self, portfolio_id: str, action_id: str, operation: str, quantity: int, conseil: dict[str, Any]
    ) -> dict[str, Any]:
        """Appelle executer_transaction (SPEC A.3) : vérifie, insère et met à jour le cash
        d'un seul bloc. Lève TransactionRefused si la base refuse."""
        from postgrest.exceptions import APIError

        try:
            return self.client.rpc(
                "executer_transaction",
                {
                    "p_portefeuille": portfolio_id,
                    "p_action": action_id,
                    "p_type": operation,
                    "p_qte": quantity,
                    "p_conseil": conseil,
                },
            ).execute().data
        except APIError as error:
            raise TransactionRefused(error.message or "ERREUR_BASE") from error

