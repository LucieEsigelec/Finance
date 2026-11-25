"""Point d'entrée de l'API FastAPI.

En bref :
- ``create_app()`` fabrique l'application : contrôle des réglages (RG-04), CORS,
  puis les routes ;
- CORS : seules les adresses listées dans ``CORS_ORIGINS`` (le site Vercel et
  ``http://localhost:5173`` en local) peuvent appeler l'API depuis un navigateur ;
- ``GET /api/health`` répond « l'API tourne ». Elle ne lit pas la base : Render s'en
  sert pour surveiller le service, et on peut l'appeler pour réveiller l'API.

Lancement : ``python -m uvicorn main:app --reload --port 8000`` depuis ``backend/``.
Les routes métier (DCT §6) sont ajoutées à l'étape API.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config

API_VERSION = "0.1.0"


def create_app(settings: config.Settings | None = None) -> FastAPI:
    config.check_config()  # RG-04 : refuse de démarrer si les poids sont invalides (V8)
    settings = settings or config.load_settings()

    app = FastAPI(
        title="Portefeuille 500k — API",
        version=API_VERSION,
        description=(
            "Outil d'aide à la décision sur un portefeuille virtuel : "
            "il ne garantit pas les performances futures."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health", tags=["technique"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": API_VERSION,
            "heure_serveur": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    return app


app = create_app()
