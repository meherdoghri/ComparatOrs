# Deploiement gratuit du portail CACID

Ce projet peut etre publie gratuitement sur GitHub Pages.

## Resultat

- URL publique de base: `https://<votre-utilisateur>.github.io/<nom-du-repo>/`
- La page d accueil publiee est `index.html` (portail unique).

## 1) Preparer le depot GitHub

1. Creer un repository GitHub (public ou prive).
2. Pousser ce dossier CACID dans la branche `main`.

Exemple de commandes:

```bash
git init
git add .
git commit -m "Portail CACID unifie"
git branch -M main
git remote add origin https://github.com/<votre-utilisateur>/<nom-du-repo>.git
git push -u origin main
```

## 2) Activer GitHub Pages

Le workflow est deja ajoute dans:

- `.github/workflows/deploy-pages.yml`

Ensuite, dans GitHub:

1. Ouvrir le repo > `Settings` > `Pages`.
2. Dans `Build and deployment`, choisir `Source: GitHub Actions`.
3. Aller dans `Actions` et lancer (ou relancer) le workflow `Deploy CACID Portal to GitHub Pages`.

## 3) Recuperer l URL publique

Quand le workflow est termine, GitHub affiche l URL de deploiement.

## Notes importantes

- Votre portail [index.html](index.html) est statique et compatible hebergement gratuit.
- Les liens internes vers les comparateurs sont relatifs et fonctionnent une fois publies.
- Les boutons "Ouvrir localhost" dans le portail ne fonctionneront que si un serveur local est lance sur votre machine (utile en local, pas pour tous les visiteurs).

## Alternative gratuite

- Netlify Drop (drag-and-drop du dossier) est aussi gratuit et rapide.
- Vercel (import GitHub) fonctionne egalement tres bien pour un site statique.
