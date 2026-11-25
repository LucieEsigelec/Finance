"""Fausse base de données en mémoire, avec la même interface que SupabaseRepository.

Les tests l'utilisent à la place de Supabase : ils ne touchent jamais la base partagée.
Elle reproduit les contrôles de la fonction SQL executer_transaction (RG-05).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

from db.repository import TransactionRefused
from services.market_data import Fundamentals

ACTIONS = [
    ("AI.PA", "Air Liquide", "Gaz industriels / Chimie", "162.00", "3.20"),
    ("CAP.PA", "Capgemini", "Services numériques / IT", "155.00", "3.40"),
    ("DSY.PA", "Dassault Systèmes", "Logiciels industriels", "34.80", "0.29"),
    ("RMS.PA", "Hermès", "Luxe", "2150.00", "15.00"),
    ("TTE.PA", "TotalEnergies", "Énergie / Pétrole & Gaz", "77.50", "3.80"),
]


def synthetic_history(ticker: str, end: date, n: int = 520) -> list[dict[str, Any]]:
    rng = np.random.default_rng(sum(map(ord, ticker)))
    base = {"AI.PA": 160, "CAP.PA": 150, "DSY.PA": 35, "RMS.PA": 2100, "TTE.PA": 60}[ticker]
    closes = base * np.cumprod(1 + rng.normal(0.0003, 0.012, n))
    days = pd.bdate_range(end=end, periods=n)
    return [
        {"date_seance": d.date().isoformat(), "open": f"{c:.2f}", "high": f"{c * 1.01:.2f}",
         "low": f"{c * 0.99:.2f}", "close": f"{c:.2f}", "volume": 1000}
        for d, c in zip(days, closes)
    ]


class FakeRepository:
    def __init__(self, cash: str = "500000.00", ref_day: date = date(2026, 11, 23)):
        self.actions = [
            {"id": str(uuid.uuid4()), "ticker": t, "nom": n, "secteur": s, "dernier_cours": Decimal(p),
             "dividende_estime": Decimal(d), "maj_le": "2026-11-25T10:00:00+00:00"}
            for t, n, s, p, d in ACTIONS
        ]
        self.history: dict[str, dict[str, dict[str, Any]]] = {a["id"]: {} for a in self.actions}
        self.ratios: list[dict[str, Any]] = []
        self.articles: list[dict[str, Any]] = []
        self.scores: list[dict[str, Any]] = []
        self.transactions: list[dict[str, Any]] = []
        self.portfolio = {
            "id": str(uuid.uuid4()), "capital_initial": Decimal("500000.00"), "cash_disponible": Decimal(cash),
            "val_semaine_prec": Decimal("500000.00"), "date_ref_semaine": ref_day, "nom_client": None,
        }

    # actions
    def get_actions(self):
        return [dict(a) for a in self.actions]

    def action_by_ticker(self, ticker):
        return next(a for a in self.actions if a["ticker"] == ticker)

    def update_action(self, action_id, **fields):
        action = next(a for a in self.actions if a["id"] == action_id)
        action.update(fields)

    # cours
    def get_history(self, action_id, since=None):
        rows = sorted(self.history[action_id].values(), key=lambda r: r["date_seance"])
        df = pd.DataFrame(rows, columns=["date_seance", "open", "high", "low", "close", "volume"])
        if not df.empty:
            df["date_seance"] = pd.to_datetime(df["date_seance"]).dt.date
            for col in ("open", "high", "low", "close"):
                df[col] = df[col].astype(float)
            if since:
                df = df[df["date_seance"] >= since]
        return df

    def last_history_date(self, action_id):
        dates = self.history[action_id]
        return date.fromisoformat(max(dates)) if dates else None

    def upsert_history(self, rows):
        for row in rows:
            self.history[row["action_id"]][row["date_seance"]] = row
        return len(rows)

    # ratios
    def get_ratios(self, action_id):
        rows = [r for r in self.ratios if r["action_id"] == action_id]
        return sorted(rows, key=lambda r: r["date_maj"], reverse=True)

    def save_ratios(self, action_id, rows):
        new = 0
        for row in rows:
            current = next((r for r in self.get_ratios(action_id) if r["date_maj"] == row["date_maj"]), None)
            if current:
                current.update(row)
            else:
                self.ratios.append(dict(row))
                new += 1
        return new

    # actualités
    def get_articles(self, action_id, since):
        rows = [a for a in self.articles if a["action_id"] == action_id and a["date_pub"] >= since]
        return sorted(rows, key=lambda a: a["date_pub"], reverse=True)

    def insert_missing_articles(self, action_id, articles, since):
        known = {a["titre"].lower() for a in self.articles if a["action_id"] == action_id}
        new = [{**a, "action_id": action_id, "id": str(uuid.uuid4())} for a in articles
               if a["titre"].lower() not in known]
        self.articles += new
        return len(new)

    # scores
    def insert_scores(self, rows):
        for row in rows:
            self.scores.append({**row, "id": str(uuid.uuid4())})

    def latest_scores(self):
        latest = {}
        for row in sorted(self.scores, key=lambda r: r["date_calcul"], reverse=True):
            latest.setdefault(row["action_id"], row)
        return latest

    # portefeuille
    def get_portfolio(self):
        return dict(self.portfolio)

    def update_portfolio_week(self, portfolio_id, value, monday):
        self.portfolio["val_semaine_prec"] = Decimal(str(value))
        self.portfolio["date_ref_semaine"] = monday

    def get_transactions(self, portfolio_id):
        return [dict(t) for t in sorted(self.transactions, key=lambda t: t["date_execution"])]

    def execute_transaction(self, portfolio_id, action_id, operation, quantity, conseil, when=None):
        """Mêmes contrôles et même atomicité que executer_transaction (SPEC A.3)."""
        action = next(a for a in self.actions if a["id"] == action_id)
        price = Decimal(str(action["dernier_cours"]))
        held = sum(
            (t["quantite_entiere"] if t["type_op"] == "ACHAT" else -t["quantite_entiere"])
            for t in self.transactions if t["action_id"] == action_id
        )
        if operation == "ACHAT" and quantity * price > self.portfolio["cash_disponible"]:
            raise TransactionRefused("RG05_CASH_INSUFFISANT")
        if operation == "VENTE" and quantity > held:
            raise TransactionRefused("VENTE_SUPERIEURE_A_LA_POSITION")
        tx = {
            "id": str(uuid.uuid4()), "portefeuille_id": portfolio_id, "action_id": action_id,
            "ticker": action["ticker"], "nom": action["nom"], "type_op": operation,
            "quantite_entiere": quantity, "prix_unitaire": price, "montant_total": quantity * price,
            "conseil_algo": conseil, "date_execution": when or datetime.now(timezone.utc),
        }
        self.transactions.append(tx)
        sign = -1 if operation == "ACHAT" else 1
        self.portfolio["cash_disponible"] += sign * quantity * price
        return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in tx.items() if k not in ("ticker", "nom")}


class FakeCollector:
    def __init__(self, end: date, fail: set[str] | None = None, articles=None):
        self.end = end
        self.fail = fail or set()
        self._articles = articles or {}
        self.calls: list[tuple[str, Any]] = []

    def history(self, ticker, since):
        self.calls.append((ticker, since))
        if "history" in self.fail:
            raise ConnectionError("yfinance indisponible")
        rows = synthetic_history(ticker, self.end)
        return [r for r in rows if since is None or r["date_seance"] >= since.isoformat()]

    def fundamentals(self, ticker, history, today):
        if "fundamentals" in self.fail:
            raise ConnectionError("ratios indisponibles")
        ca = {"DSY.PA": (6.2e9, 6.0e9), "TTE.PA": (2.0e11, 2.2e11)}.get(ticker, (1e10, 9.4e9))
        return Fundamentals(
            exercices=[
                {"date_maj": "2025-12-31", "chiffre_affaires": str(ca[0]), "dividende_par_action": "1.08",
                 "rendement_pct": "2.10"},
                {"date_maj": "2024-12-31", "chiffre_affaires": str(ca[1]), "dividende_par_action": "1.00",
                 "rendement_pct": "2.00"},
            ],
            dividende_12_mois=Decimal("0.29") if ticker == "DSY.PA" else Decimal("3.00"),
        )

    def news(self, ticker, now, api_key):
        if "news" in self.fail:
            return [], ["Google News : timeout"]
        return list(self._articles.get(ticker, [])), []
