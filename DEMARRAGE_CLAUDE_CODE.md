# Démarrer avec Claude Code

Fichier pour le groupe (on peut le supprimer une fois le projet lancé).

## Avant la première session

1. Copier tout le contenu de ce dossier à la racine du dépôt GitHub, puis committer sur une branche `docs/setup` et ouvrir une Pull Request.
2. Récupérer auprès de la cheffe de groupe l'URL du projet Supabase et la clé `service_role` (Project Settings > API).
3. Créer `backend\.env` à partir de `backend\.env.example` et y coller ces valeurs. **Ne jamais committer ce fichier.**
4. Ouvrir un terminal PowerShell à la racine du dépôt et lancer `claude`.

## Premier message à envoyer

> Lis CLAUDE.md, puis docs/README.md et tous les documents de docs/ dans l'ordre indiqué (regarde aussi les captures de docs/maquettes/captures/). Propose-moi un plan de développement par étapes, en suivant l'ordre du §11 de CLAUDE.md : pour chaque étape, la branche, les fichiers créés, les tests et ce que je devrai vérifier. Ne code rien et n'exécute rien sur Supabase avant que je valide.

## Ensuite, pour chaque étape

> On attaque l'étape N. Crée la branche, code l'étape, lance les tests, puis explique-moi ce que tu as fait et ce que je dois relire avant de committer.

- Toujours lire le SQL avant d'accepter qu'il soit exécuté sur Supabase (base partagée).
- Committer et ouvrir une Pull Request à la fin de chaque étape.
- Demander à Claude Code d'expliquer les parties clés (moteur de décision, simulateur) : il faudra les présenter.
