# Frontend — Portefeuille 500k

Interface React 19 + Vite 8 + Tailwind CSS 4. Elle ne parle qu'à l'API FastAPI (`VITE_API_URL`).

```bash
npm install
cp .env.example .env.local      # Windows : Copy-Item .env.example .env.local
npm run dev                     # http://localhost:5173 (l'API doit tourner sur :8000)
npm run build                   # vérification avant commit
npm run lint
```

Organisation : voir `docs/05_guide_du_code.md` §7.
