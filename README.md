# Portefeuille 500k — application d'aide à la décision

Projet de groupe : application web qui conseille Achat, Vente ou Rien sur 5 actions du CAC 40 (Dassault Systèmes, TotalEnergies, Capgemini, Hermès, Air Liquide) pour un portefeuille virtuel de 500 000 €.

- **Frontend** : React 18 + Vite, Tailwind, shadcn/ui (`frontend/`)
- **Backend** : FastAPI, Python 3.11 (`backend/`)
- **Base** : Supabase PostgreSQL (`supabase/migrations/`)
- **Documentation** : `docs/` (cahier des charges, conception, spécification, interface, charte, maquettes)

Règles de développement, commandes et méthode : voir [`CLAUDE.md`](CLAUDE.md).

L'application se déploie comme un site web (Vercel pour l'interface, Render pour l'API) : rien à installer pour l'utiliser. Le développement fonctionne sous Windows, Linux et macOS.

## Démarrer en local

Prérequis : Python 3.11 (conseillé : [`uv`](https://docs.astral.sh/uv/)), Node 20 LTS.

```bash
# Backend (terminal 1)
cd backend
uv venv --python 3.11
uv pip install -r requirements.txt
cp .env.example .env            # Windows : Copy-Item .env.example .env — puis remplir les valeurs
# activer l'environnement : .venv\Scripts\Activate.ps1 (Windows) · source .venv/bin/activate (Linux, macOS)
python -m tools.check_supabase  # vérifie la connexion à la base (lecture seule)
python -m uvicorn main:app --reload --port 8000  # puis http://localhost:8000/api/health

# Frontend (terminal 2)
cd frontend
npm install
cp .env.example .env.local      # Windows : Copy-Item .env.example .env.local
npm run dev
```

Outil d'aide à la décision sur un portefeuille virtuel : il ne garantit pas les performances futures.
