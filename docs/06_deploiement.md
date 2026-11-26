# Mettre l'application en ligne

L'application devient un **site web** accessible depuis n'importe quel appareil (D-04). Trois hébergeurs gratuits, déjà prévus par le dossier de conception :

| Partie | Hébergeur | Ce qu'il faut |
|---|---|---|
| Base de données | **Supabase** | Déjà en ligne |
| API (backend) | **Render** | Un compte Render relié au GitHub de l'équipe |
| Interface (frontend) | **Vercel** | Un compte Vercel relié au GitHub de l'équipe |
| Actualisation planifiée | **GitHub Actions** | Un secret et une variable dans le dépôt |

Comptez une trentaine de minutes la première fois. L'ordre compte : l'API d'abord (Vercel a besoin de son adresse), puis l'interface, puis on revient sur Render pour autoriser l'adresse de l'interface.

## 1. L'API sur Render

1. Sur https://render.com, connectez-vous avec GitHub, puis **New → Blueprint** et choisissez le dépôt `LucieEsigelec/Finance`. Render lit le fichier `render.yaml` à la racine.
2. Render demande 4 valeurs (elles ne sont jamais dans git) :

   | Variable | Valeur |
   |---|---|
   | `SUPABASE_URL` | la même que dans `backend/.env` |
   | `SUPABASE_KEY` | la clé secrète (`service_role` / `sb_secret_…`) |
   | `NEWS_API_KEY` | la clé NewsAPI |
   | `CORS_ORIGINS` | laissez `http://localhost:5173` pour l'instant (étape 3) |

3. Lancez le déploiement. Au bout de quelques minutes, l'adresse ressemble à `https://portefeuille-500k-api.onrender.com`. Vérifiez : `https://…onrender.com/api/health` doit répondre `{"status":"ok", …}`.

> **Offre gratuite** : l'API s'endort après 15 minutes sans visite et met 30 à 60 secondes à se réveiller. Avant une démonstration, ouvrez `/api/health` une minute avant. Pour la supprimer : offre payante (environ 7 $ par mois).

## 2. L'interface sur Vercel

1. Sur https://vercel.com, connectez-vous avec GitHub, puis **Add New → Project** et choisissez le dépôt.
2. **Root Directory** : `frontend`. Vercel reconnaît Vite tout seul (commande `npm run build`, dossier `dist`).
3. **Environment Variables** : `VITE_API_URL` = l'adresse Render de l'étape 1 (sans `/` à la fin).
4. Déployez. L'adresse ressemble à `https://portefeuille-500k.vercel.app`.

Le fichier `frontend/vercel.json` permet d'ouvrir directement une adresse comme `/simulateur` ou `/action/DSY.PA`.

## 3. Autoriser l'interface à appeler l'API

Sur Render, dans les variables du service, remplacez `CORS_ORIGINS` par :

```
https://portefeuille-500k.vercel.app,http://localhost:5173
```

(votre adresse Vercel exacte, puis l'adresse locale, séparées par une virgule). Render redémarre l'API. Ouvrez le site : le tableau de bord doit s'afficher.

## 4. L'actualisation planifiée (GitHub Actions)

Le fichier `.github/workflows/refresh.yml` appelle `POST /api/market/refresh` à 18 h et chaque heure en séance, du lundi au vendredi. Pour l'activer, dans GitHub → **Settings → Secrets and variables → Actions** :

- onglet **Secrets** : `API_URL` = l'adresse Render ;
- onglet **Variables** : `REFRESH_ENABLED` = `true`.

Pour tester tout de suite : onglet **Actions → Actualisation des données → Run workflow**.

> GitHub peut retarder ces tâches de plusieurs heures. Ce n'est pas grave : l'API relance aussi l'actualisation toute seule dès que quelqu'un ouvre le site et que les données ont plus d'une heure (D-13).

## 5. Les vérifications automatiques

Le fichier `.github/workflows/ci.yml` lance, sur chaque Pull Request, les tests du backend (`pytest`) et la construction du frontend (`npm run build`). Le résultat apparaît en bas de la Pull Request. Rien à configurer.

## 6. Ensuite

Chaque fusion sur `main` redéploie automatiquement l'API (Render) et l'interface (Vercel).

## En cas de problème

| Symptôme | Cause probable | Solution |
|---|---|---|
| Le site affiche « L'application ne parvient pas à joindre le serveur » | API endormie ou `VITE_API_URL` faux | Ouvrir `/api/health`, vérifier la variable Vercel puis redéployer |
| Erreur CORS dans la console du navigateur | Adresse Vercel absente de `CORS_ORIGINS` | Étape 3 |
| L'API ne démarre pas sur Render | Variable manquante | Les journaux Render indiquent `Variable(s) manquante(s)` |
| « Données actualisées il y a moins de 2 minutes » | Protection du bouton Actualiser | Attendre 2 minutes |
| Les seuils de `render.yaml` ne s'appliquent pas | Render ne synchronise pas toujours les variables d'un Blueprint | Les ajouter à la main dans l'onglet **Environment** du service |
