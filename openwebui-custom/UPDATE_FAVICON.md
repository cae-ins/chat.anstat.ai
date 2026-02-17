# Mise à jour du Favicon

## Contexte
Le script `build-and-deploy.sh` a été modifié pour :
- Utiliser le `favicon.ico` fourni dans le dossier (ne plus le générer à partir du logo)
- Générer `favicon.png` à partir de `favicon.ico` (pour le logo du chat et Apple touch icon)

## Fichiers modifiés
- `build-and-deploy.sh` : utilise favicon.ico comme source unique
- `Dockerfile` : copie favicon.png aux emplacements du logo du chat

## Étapes de mise à jour

### 1. Copier les fichiers modifiés vers le serveur

```bash
scp build-and-deploy.sh Dockerfile favicon.ico migone@192.168.1.230:/home/migone/vLLM_Deploy/openwebui-custom/
```

### 2. Se connecter au serveur et lancer le déploiement

```bash
ssh user@serveur
cd /chemin/vers/vLLM_Deploy/openwebui-custom
./build-and-deploy.sh
```

### 3. Vider le cache du navigateur

Utilisez `Ctrl+Shift+R` pour voir le nouveau favicon et logo du chat.

## Notes
- Le fichier `favicon.ico` est la source unique pour tous les logos
- `favicon.png` est généré automatiquement à partir de `favicon.ico` lors du build
- ImageMagick est requis sur le serveur pour la conversion optimale
