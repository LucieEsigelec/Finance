"""Test de résistance du garde-fou RG-01 (recette REC-4) — SPEC §11.2.

En bref : on prend un portefeuille, on fait baisser **tous les cours** d'un même
pourcentage, et on regarde à partir de quelle baisse l'alerte passe à l'orange
(APPROCHE, −7 %) puis au rouge (ATTEINT, −10 %). Tout se passe en mémoire : rien n'est
écrit dans la base.

Exemple de la SPEC : 400 000 € investis et 100 000 € de cash. Pour perdre 50 000 €
(10 % de 500 000 €), il faut que les actions perdent 12,5 %.

Lancement depuis ``backend/`` : ``python -m tools.stress_test``
"""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from services.decision_engine import alert_level, portfolio_value, weekly_variation_pct


def shocked_level(
    cash: Decimal,
    held: Mapping[str, int],
    prices: Mapping[str, Decimal],
    reference: Decimal,
    drop_pct: float,
) -> tuple[float, str]:
    """Variation de la semaine et niveau d'alerte après une baisse de tous les cours."""
    factor = Decimal(1) - Decimal(str(drop_pct)) / 100
    shocked = {t: Decimal(str(p)) * factor for t, p in prices.items()}
    variation = weekly_variation_pct(portfolio_value(cash, held, shocked), reference)
    return variation, alert_level(variation)


def first_drop_reaching(cash, held, prices, reference, level: str, step: float = 0.1) -> float:
    drop = 0.0
    while drop <= 100:
        if shocked_level(cash, held, prices, reference, drop)[1] == level:
            return round(drop, 1)
        drop += step
    raise ValueError(f"niveau {level} jamais atteint")


def main() -> None:
    cash = Decimal("100000")
    held = {"DSY.PA": 10000}
    prices = {"DSY.PA": Decimal("40")}  # 400 000 € investis
    reference = Decimal("500000")
    print("Portefeuille : 400 000 € investis, 100 000 € de cash (exemple SPEC §11.2)\n")
    for drop in (5.0, 8.75, 10.0, 12.5, 15.0):
        variation, level = shocked_level(cash, held, prices, reference, drop)
        print(f"  baisse des cours de {drop:5.2f} % → semaine {variation:+6.2f} % → {level}")
    print(
        f"\nAlerte orange dès {first_drop_reaching(cash, held, prices, reference, 'APPROCHE')} % de baisse, "
        f"rouge dès {first_drop_reaching(cash, held, prices, reference, 'ATTEINT')} %."
    )


if __name__ == "__main__":
    main()
