# Portefeuille 500k — application d'aide à la décision

Projet de groupe : application web qui conseille Achat, Vente ou Rien sur 5 actions du CAC 40 (Dassault Systèmes, TotalEnergies, Capgemini, Hermès, Air Liquide) pour un portefeuille virtuel de 500 000 €.

- **Frontend** : React 18 + Vite, Tailwind, shadcn/ui (`frontend/`)
- **Backend** : FastAPI, Python 3.11 (`backend/`)
- **Base** : Supabase PostgreSQL (`supabase/migrations/`)
- **Documentation** : `docs/` (cahier des charges, conception, spécification, interface, charte, maquettes)

Règles de développement, commandes Windows et méthode : voir [`CLAUDE.md`](CLAUDE.md).

## Démarrer en local (PowerShell)

```powershell
# Backend
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env   # puis remplir les valeurs
python -m uvicorn main:app --reload --port 8000

# Frontend (autre terminal)
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Outil d'aide à la décision sur un portefeuille virtuel : il ne garantit pas les performances futures.
