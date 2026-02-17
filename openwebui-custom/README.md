# OpenWebUI Personnalisé - ANSTAT

## Structure du dossier

```
openwebui-custom/
├── Dockerfile              # Image Docker personnalisée
├── custom-anstat.css       # Thème CSS aux couleurs ANSTAT
├── favicon.ico             # À créer depuis le logo (32x32)
├── favicon.png             # À créer depuis le logo (180x180)
├── logo-anstat.png         # Logo pour l'interface (copier depuis ../../../logo ANSTAT_PRINCIPAL.png)
└── README.md               # Ce fichier
```

## Préparation des assets

### 1. Préparer le logo et favicon

```bash
# Copier le logo principal
cp "../../../logo ANSTAT_PRINCIPAL.png" logo-anstat.png

# Créer le favicon avec ImageMagick (si installé)
convert logo-anstat.png -resize 32x32 favicon.ico
convert logo-anstat.png -resize 180x180 favicon.png

# OU utiliser un outil en ligne comme:
# - https://favicon.io/favicon-converter/
# - https://realfavicongenerator.net/
```

### 2. Build de l'image Docker

```bash
# Dans ce dossier
docker build -t openwebui-anstat:latest .

# Ou avec un registry privé
docker build -t registry.anstat.ci/openwebui-anstat:v1.0.0 .
docker push registry.anstat.ci/openwebui-anstat:v1.0.0
```

## Couleurs ANSTAT

| Couleur | Hex | Utilisation |
|---------|-----|-------------|
| Orange principal | `#E8923A` | Boutons, liens, accents |
| Orange clair | `#F5A855` | Hover states |
| Orange foncé | `#D4802E` | Pressed states |
| Vert principal | `#3D5A4C` | Headers, badges |
| Vert clair | `#4A6D5C` | Hover sur éléments verts |
| Vert foncé | `#2E4439` | Backgrounds foncés |

## Personnalisation supplémentaire

Le CSS peut être modifié dans `custom-anstat.css`. Après modification :

```bash
# Rebuild l'image
docker build -t openwebui-anstat:latest .

# Redéployer sur Kubernetes
kubectl rollout restart deployment/openwebui -n vllm-chat
```
