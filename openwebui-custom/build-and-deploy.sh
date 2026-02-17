#!/bin/bash
# ============================================
# ANSTAT AI - Script de build et déploiement
# OpenWebUI personnalisé pour l'Agence Nationale de la Statistique
# ============================================

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           ANSTAT AI - Build & Deploy Script               ║"
echo "║     Agence Nationale de la Statistique - Côte d'Ivoire    ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Configuration
NAMESPACE="vllm-chat"
IMAGE_NAME="openwebui-anstat"
IMAGE_TAG="${1:-latest}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================
# ÉTAPE 1: Vérification des prérequis
# ============================================
echo -e "${YELLOW}[1/5] Vérification des prérequis...${NC}"

# Vérifier si Docker est disponible
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Erreur: Docker n'est pas installé.${NC}"
    exit 1
fi

# Vérifier si kubectl est disponible
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Erreur: kubectl n'est pas installé.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker et kubectl disponibles${NC}"

# ============================================
# ÉTAPE 2: Préparation des assets
# ============================================
echo -e "${YELLOW}[2/5] Préparation des assets...${NC}"

cd "$SCRIPT_DIR"

# Vérifier/créer le logo
if [ ! -f "logo-anstat.png" ]; then
    if [ -f "../../../logo ANSTAT_PRINCIPAL.png" ]; then
        cp "../../../logo ANSTAT_PRINCIPAL.png" logo-anstat.png
        echo -e "${GREEN}✓ Logo copié${NC}"
    else
        echo -e "${RED}Erreur: Logo ANSTAT non trouvé. Placez 'logo-anstat.png' dans ce dossier.${NC}"
        exit 1
    fi
fi

# Vérifier que favicon.ico est présent (doit être fourni dans le dossier)
if [ ! -f "favicon.ico" ]; then
    echo -e "${RED}Erreur: favicon.ico non trouvé. Placez le fichier favicon.ico dans ce dossier.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ favicon.ico trouvé${NC}"

# Créer favicon.png à partir de favicon.ico (pour le logo du chat et Apple touch icon)
echo -e "${YELLOW}Création de favicon.png à partir de favicon.ico...${NC}"
if command -v convert &> /dev/null; then
    convert favicon.ico -resize 180x180 favicon.png
    echo -e "${GREEN}✓ favicon.png créé avec ImageMagick${NC}"
else
    echo -e "${YELLOW}⚠ ImageMagick non installé. Copie de favicon.ico comme favicon.png...${NC}"
    cp favicon.ico favicon.png
fi

echo -e "${GREEN}✓ Assets prêts${NC}"

# ============================================
# ÉTAPE 3: Build de l'image Docker
# ============================================
echo -e "${YELLOW}[3/5] Build de l'image Docker...${NC}"

docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .

echo -e "${GREEN}✓ Image ${IMAGE_NAME}:${IMAGE_TAG} construite${NC}"

# ============================================
# ÉTAPE 4: Push vers le registry (optionnel)
# ============================================
if [ -n "$REGISTRY" ]; then
    echo -e "${YELLOW}[4/5] Push vers le registry ${REGISTRY}...${NC}"
    docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    docker push "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    echo -e "${GREEN}✓ Image pushée vers ${REGISTRY}${NC}"
else
    echo -e "${YELLOW}[4/5] Pas de registry configuré, skip du push...${NC}"
    echo -e "       Pour pusher: REGISTRY=registry.anstat.ci $0${NC}"
fi

# ============================================
# ÉTAPE 5: Déploiement Kubernetes
# ============================================
echo -e "${YELLOW}[5/5] Déploiement sur Kubernetes...${NC}"

# Vérifier le namespace
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${YELLOW}Création du namespace ${NAMESPACE}...${NC}"
    kubectl create namespace "$NAMESPACE"
fi

# Appliquer le deployment
kubectl apply -f ../openwebui-deployment.yaml

# Appliquer l'Ingress
kubectl apply -f ../ingress.yaml

# Redémarrer le deployment pour prendre la nouvelle image
kubectl rollout restart deployment/openwebui -n "$NAMESPACE"

# Attendre que le rollout soit terminé
echo -e "${YELLOW}Attente du déploiement...${NC}"
kubectl rollout status deployment/openwebui -n "$NAMESPACE" --timeout=300s

echo -e "${GREEN}✓ Déploiement terminé${NC}"

# ============================================
# RÉSUMÉ
# ============================================
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗"
echo -e "║                    DÉPLOIEMENT RÉUSSI                      ║"
echo -e "╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Image:${NC} ${IMAGE_NAME}:${IMAGE_TAG}"
echo -e "${GREEN}Namespace:${NC} ${NAMESPACE}"
echo -e "${GREEN}URL:${NC} https://chat.anstat.ci"
echo ""
echo -e "${YELLOW}Vérification du statut:${NC}"
kubectl get pods -n "$NAMESPACE" -l app=openwebui
echo ""
echo -e "${YELLOW}Pour voir les logs:${NC}"
echo "  kubectl logs -f deployment/openwebui -n ${NAMESPACE}"
