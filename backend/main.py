"""Point d'entrée de l'API FastAPI.

En bref :
- ``create_app()`` fabrique l'application : contrôle des réglages (RG-04), CORS,
  puis les routes ;
- CORS : seules les adresses listées dans ``CORS_ORIGINS`` (le site Vercel et
  ``http://localhost:5173`` en local) peuvent appeler l'API depuis un navigateur ;
- ``GET /api/health`` répond « l'API tourne ». Elle ne lit pas la base : Render s'en
  sert pour surveiller le service, et on peut l'appeler pour réveiller l'API.

Les 6 routes métier du DCT §6 sont dans ``routers/`` :
- ``dashboard.py`` : GET /api/dashboard
- ``simulator.py`` : POST /api/simulate
- ``transactions.py`` : POST /api/transactions, GET /api/portfolio/history
- ``stocks.py`` : GET /api/stocks/{ticker}, POST /api/market/refresh
- ``profile.py`` : GET / PUT /api/profil (profil de risque, D-17)

Lancement : ``python -m uvicorn main:app --reload --port 8000`` depuis ``backend/``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from routers import dashboard, profile, simulator, stocks, transactions

API_VERSION = "0.2.0"


def create_app(settings: config.Settings | None = None) -> FastAPI:
    config.check_config()  # RG-04 : refuse de démarrer si les poids sont invalides (V8)
    settings = settings or config.load_settings()

    app = FastAPI(
        title="PrimeInvest — API",
        version=API_VERSION,
        description=(
            "Outil d'aide à la décision sur un portefeuille virtuel : "
            "il ne garantit pas les performances futures."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT"],  # PUT : profil de risque (D-17)
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health", tags=["technique"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": API_VERSION,
            "heure_serveur": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    for module in (dashboard, simulator, transactions, stocks, profile):
        app.include_router(module.router)
    return app


app = create_app()
