"""Formats des requêtes envoyées par l'interface (validation Pydantic) — DCT §6, SPEC A.

En bref : chaque requête est vérifiée avant tout calcul. Montant strictement positif,
opération ACHAT ou VENTE, quantité entière positive… Une saisie invalide est refusée
avec le code 422 (SPEC A.4). Un code d'action inconnu est traité dans la route (404).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Operation = Literal["ACHAT", "VENTE"]


class SimulateRequest(BaseModel):
    """POST /api/simulate. Plusieurs titres possibles : le montant s'applique à chacun (D-08).
    Le contrat du DCT (un seul « ticker ») est aussi accepté."""

    model_config = ConfigDict(extra="forbid")

    tickers: list[str] = Field(default_factory=list, max_length=5)
    ticker: str | None = None
    operation: Operation
    montant_eur: Decimal = Field(gt=0, max_digits=14, decimal_places=2)

    @model_validator(mode="after")
    def merge_tickers(self) -> "SimulateRequest":
        tickers = [t.strip().upper() for t in self.tickers]
        if self.ticker:
            tickers.append(self.ticker.strip().upper())
        tickers = list(dict.fromkeys(tickers))  # sans doublon, ordre conservé
        if not tickers:
            raise ValueError("Cochez au moins une action")
        self.tickers = tickers
        return self


class TransactionRequest(BaseModel):
    """POST /api/transactions : une opération validée dans la fenêtre de confirmation."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    operation: Operation
    quantite: int = Field(gt=0)
    cours_simule: Decimal = Field(gt=0)
    date_conseil: datetime

    @field_validator("ticker")
    @classmethod
    def upper(cls, value: str) -> str:
        return value.strip().upper()
