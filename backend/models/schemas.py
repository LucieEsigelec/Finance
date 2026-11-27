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


class OperationLine(BaseModel):
    """Une ligne de la page Acheter / vendre : une action et SON montant en euros (D-14),
    OU son nombre d'actions (D-26). Exactement l'un des deux."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    montant_eur: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    quantite: int | None = Field(default=None, gt=0, le=10_000_000)

    @field_validator("ticker")
    @classmethod
    def upper(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def one_unit(self) -> "OperationLine":
        if (self.montant_eur is None) == (self.quantite is None):
            raise ValueError("Indiquez soit un montant en euros, soit un nombre d'actions")
        return self


class SimulateRequest(BaseModel):
    """POST /api/simulate.

    Format conseillé : ``operations`` = une ligne par action avec son propre montant (D-14).
    Anciens formats encore acceptés : ``tickers`` + ``montant_eur`` (même montant pour
    chacune, D-08) et ``ticker`` + ``montant_eur`` (contrat du DCT)."""

    model_config = ConfigDict(extra="forbid")

    operations: list[OperationLine] = Field(default_factory=list, max_length=5)
    tickers: list[str] = Field(default_factory=list, max_length=5)
    ticker: str | None = None
    operation: Operation
    montant_eur: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)

    @model_validator(mode="after")
    def build_lines(self) -> "SimulateRequest":
        lines = list(self.operations)
        legacy = [t.strip().upper() for t in self.tickers] + ([self.ticker.strip().upper()] if self.ticker else [])
        if legacy:
            if self.montant_eur is None:
                raise ValueError("Saisissez un montant")
            lines += [OperationLine(ticker=t, montant_eur=self.montant_eur) for t in legacy]
        unique: dict[str, OperationLine] = {}
        for line in lines:  # une seule ligne par action, la première l'emporte
            unique.setdefault(line.ticker, line)
        if not unique:
            raise ValueError("Cochez au moins une action")
        if len(unique) > 5:
            raise ValueError("5 actions au plus")
        self.operations = list(unique.values())
        return self

    @property
    def tickers_list(self) -> list[str]:
        return [line.ticker for line in self.operations]


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
