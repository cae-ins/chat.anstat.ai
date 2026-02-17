#!/bin/bash
# ============================================================================
#  ANSTAT AI - Script de déploiement complet
#  Agence Nationale de la Statistique - Côte d'Ivoire
#
#  Usage: ./deploy.sh [OPTIONS]
#
#  Options:
#    --skip-ingress-install   Ne pas installer NGINX Ingress Controller
#    --skip-certmanager       Ne pas installer cert-manager
#    --skip-build             Ne pas rebuild les images Docker
#    --only-restart           Redémarrer tous les services uniquement
#    --help                   Afficher cette aide
# ============================================================================

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================
NAMESPACE="vllm-chat"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Options par défaut
SKIP_INGRESS_INSTALL=false
SKIP_CERTMANAGER=false
SKIP_BUILD=false
ONLY_RESTART=false

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║     █████╗ ███╗   ██╗███████╗████████╗ █████╗ ████████╗          ║"
    echo "║    ██╔══██╗████╗  ██║██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝          ║"
    echo "║    ███████║██╔██╗ ██║███████╗   ██║   ███████║   ██║             ║"
    echo "║    ██╔══██║██║╚██╗██║╚════██║   ██║   ██╔══██║   ██║             ║"
    echo "║    ██║  ██║██║ ╚████║███████║   ██║   ██║  ██║   ██║             ║"
    echo "║    ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝             ║"
    echo "║                                                                   ║"
    echo "║              Plateforme de Chat IA - Déploiement                  ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 n'est pas installé. Veuillez l'installer et réessayer."
        exit 1
    fi
}

wait_for_pods() {
    local label=$1
    local timeout=${2:-300}
    log_info "Attente des pods ($label)..."
    kubectl wait --for=condition=ready pod -l $label -n $NAMESPACE --timeout=${timeout}s || {
        log_warning "Timeout atteint, vérification du statut..."
        kubectl get pods -n $NAMESPACE -l $label
    }
}

# ============================================================================
# PARSING DES ARGUMENTS
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-ingress-install)
            SKIP_INGRESS_INSTALL=true
            shift
            ;;
        --skip-certmanager)
            SKIP_CERTMANAGER=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --only-restart)
            ONLY_RESTART=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-ingress-install   Ne pas installer NGINX Ingress Controller"
            echo "  --skip-certmanager       Ne pas installer cert-manager"
            echo "  --skip-build             Ne pas rebuild les images Docker"
            echo "  --only-restart           Redémarrer tous les services uniquement"
            echo "  --help                   Afficher cette aide"
            exit 0
            ;;
        *)
            log_error "Option inconnue: $1"
            exit 1
            ;;
    esac
done

# ============================================================================
# DÉBUT DU SCRIPT
# ============================================================================

print_banner

# Mode restart uniquement
if [ "$ONLY_RESTART" = true ]; then
    log_step "REDÉMARRAGE DE TOUS LES SERVICES"
    kubectl rollout restart deployment/phi3 -n $NAMESPACE 2>/dev/null || true
    kubectl rollout restart deployment/rag-api -n $NAMESPACE 2>/dev/null || true
    kubectl rollout restart deployment/openwebui -n $NAMESPACE 2>/dev/null || true
    log_success "Services redémarrés"
    kubectl get pods -n $NAMESPACE
    exit 0
fi

# ============================================================================
# ÉTAPE 1: VÉRIFICATION DES PRÉREQUIS
# ============================================================================

log_step "ÉTAPE 1/8 - Vérification des prérequis"

check_command kubectl
check_command docker
log_success "kubectl et docker disponibles"

# Vérifier la connexion au cluster
if ! kubectl cluster-info &> /dev/null; then
    log_error "Impossible de se connecter au cluster Kubernetes"
    exit 1
fi
log_success "Connexion au cluster Kubernetes OK"

# Vérifier GPU (optionnel)
if kubectl get nodes -o yaml | grep -q "nvidia.com/gpu"; then
    log_success "GPU NVIDIA détecté dans le cluster"
else
    log_warning "Pas de GPU NVIDIA détecté - le modèle sera lent"
fi

# ============================================================================
# ÉTAPE 2: INSTALLATION NGINX INGRESS CONTROLLER
# ============================================================================

log_step "ÉTAPE 2/8 - NGINX Ingress Controller"

if [ "$SKIP_INGRESS_INSTALL" = true ]; then
    log_info "Installation Ingress ignorée (--skip-ingress-install)"
else
    if kubectl get namespace ingress-nginx &> /dev/null; then
        log_info "NGINX Ingress Controller déjà installé"
    else
        log_info "Installation de NGINX Ingress Controller..."
        kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.0/deploy/static/provider/cloud/deploy.yaml

        log_info "Attente du démarrage de l'Ingress Controller..."
        sleep 10
        kubectl wait --namespace ingress-nginx \
            --for=condition=ready pod \
            --selector=app.kubernetes.io/component=controller \
            --timeout=120s || log_warning "Timeout - vérifier manuellement"
    fi
fi
log_success "NGINX Ingress Controller OK"

# ============================================================================
# ÉTAPE 3: INSTALLATION CERT-MANAGER
# ============================================================================

log_step "ÉTAPE 3/8 - cert-manager (TLS automatique)"

if [ "$SKIP_CERTMANAGER" = true ]; then
    log_info "Installation cert-manager ignorée (--skip-certmanager)"
else
    if kubectl get namespace cert-manager &> /dev/null; then
        log_info "cert-manager déjà installé"
    else
        log_info "Installation de cert-manager..."
        kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml

        log_info "Attente du démarrage de cert-manager..."
        sleep 10
        kubectl wait --namespace cert-manager \
            --for=condition=ready pod \
            --selector=app.kubernetes.io/instance=cert-manager \
            --timeout=120s || log_warning "Timeout - vérifier manuellement"
    fi
fi
log_success "cert-manager OK"

# ============================================================================
# ÉTAPE 4: CRÉATION DU NAMESPACE ET SECRETS
# ============================================================================

log_step "ÉTAPE 4/8 - Namespace et Secrets"

# Créer le namespace
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    log_info "Création du namespace $NAMESPACE..."
    kubectl create namespace $NAMESPACE
else
    log_info "Namespace $NAMESPACE existe déjà"
fi

# Créer le secret HuggingFace
if [ -n "$HF_TOKEN" ]; then
    log_info "Création du secret HuggingFace..."
    kubectl create secret generic hf-token-secret \
        --from-literal=token=$HF_TOKEN \
        -n $NAMESPACE \
        --dry-run=client -o yaml | kubectl apply --force -f -
    log_success "Secret HuggingFace créé"
elif [ -f "$SCRIPT_DIR/hf-secret.yaml" ]; then
    log_info "Application du secret HuggingFace depuis fichier..."
    # Supprimer et recréer pour éviter les conflits de version
    kubectl delete secret hf-token-secret -n $NAMESPACE 2>/dev/null || true
    kubectl apply -f "$SCRIPT_DIR/hf-secret.yaml"
    log_success "Secret HuggingFace appliqué"
else
    log_warning "Pas de token HuggingFace configuré (HF_TOKEN ou hf-secret.yaml)"
fi

log_success "Namespace et secrets OK"

# ============================================================================
# ÉTAPE 5: PERSISTENT VOLUME CLAIMS
# ============================================================================

log_step "ÉTAPE 5/8 - Persistent Volume Claims"

# Les PVCs sont immutables - on ne peut que les créer, pas les modifier
# On vérifie s'ils existent déjà avant d'appliquer
EXISTING_PVCS=$(kubectl get pvc -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

if [ -n "$EXISTING_PVCS" ]; then
    log_info "PVCs existants détectés: $EXISTING_PVCS"
    log_info "Les PVCs sont immutables - on garde les existants"
else
    log_info "Création des PVCs..."
    kubectl apply -f "$SCRIPT_DIR/pvcs.yaml"
    log_info "Attente de la création des PVC..."
    sleep 5
fi

kubectl get pvc -n $NAMESPACE

log_success "PVCs OK"

# ============================================================================
# ÉTAPE 6: DÉPLOIEMENT PHI-3 (LLM)
# ============================================================================

log_step "ÉTAPE 6/8 - Déploiement Phi-3 (vLLM)"

# Utiliser replace --force pour éviter les erreurs de conflit (supprime et recrée)
kubectl replace --force -f "$SCRIPT_DIR/phi3-deployment.yaml" 2>/dev/null || kubectl apply -f "$SCRIPT_DIR/phi3-deployment.yaml"
kubectl replace --force -f "$SCRIPT_DIR/phi3-service.yaml" 2>/dev/null || kubectl apply -f "$SCRIPT_DIR/phi3-service.yaml"

log_info "Le modèle Phi-3 démarre (peut prendre 5-10 min pour le téléchargement initial)..."
log_info "Continuons avec les autres déploiements en parallèle..."

log_success "Phi-3 en cours de déploiement"

# ============================================================================
# ÉTAPE 7: DÉPLOIEMENT RAG API
# ============================================================================

log_step "ÉTAPE 7/8 - Déploiement RAG API"

cd "$PROJECT_ROOT/rag-service"

if [ "$SKIP_BUILD" = false ]; then
    log_info "Build de l'image RAG API..."
    docker build -t rag-api-phi3:latest .
fi

kubectl replace --force -f rag-deployment.yaml 2>/dev/null || kubectl apply -f rag-deployment.yaml

log_success "RAG API déployé"

# ============================================================================
# ÉTAPE 8: DÉPLOIEMENT OPENWEBUI + INGRESS
# ============================================================================

log_step "ÉTAPE 8/8 - Déploiement OpenWebUI et Ingress"

cd "$SCRIPT_DIR/openwebui-custom"

if [ "$SKIP_BUILD" = false ]; then
    # Préparer les assets
    if [ ! -f "logo-anstat.png" ]; then
        if [ -f "$PROJECT_ROOT/logo ANSTAT_PRINCIPAL.png" ]; then
            cp "$PROJECT_ROOT/logo ANSTAT_PRINCIPAL.png" logo-anstat.png
            log_info "Logo copié"
        fi
    fi

    # Créer des favicons par défaut si manquants
    if [ ! -f "favicon.png" ]; then
        if [ -f "logo-anstat.png" ]; then
            cp logo-anstat.png favicon.png
            cp logo-anstat.png favicon.ico
            log_warning "Favicons créés depuis le logo (utilisez ImageMagick pour redimensionner)"
        fi
    fi

    log_info "Build de l'image OpenWebUI personnalisée..."
    docker build -t openwebui-anstat:latest .
fi

cd "$SCRIPT_DIR"
kubectl replace --force -f openwebui-deployment.yaml 2>/dev/null || kubectl apply -f openwebui-deployment.yaml
kubectl replace --force -f ingress.yaml 2>/dev/null || kubectl apply -f ingress.yaml

log_success "OpenWebUI et Ingress déployés"

# ============================================================================
# VÉRIFICATION FINALE
# ============================================================================

log_step "VÉRIFICATION FINALE"

echo ""
log_info "Attente du démarrage des pods..."
sleep 10

echo ""
echo -e "${CYAN}État des pods :${NC}"
kubectl get pods -n $NAMESPACE

echo ""
echo -e "${CYAN}État des services :${NC}"
kubectl get svc -n $NAMESPACE

echo ""
echo -e "${CYAN}État de l'Ingress :${NC}"
kubectl get ingress -n $NAMESPACE

# ============================================================================
# RÉSUMÉ
# ============================================================================

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    DÉPLOIEMENT TERMINÉ                            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}URLs :${NC}"
echo -e "  • Interface Web : ${GREEN}https://chat.anstat.ci${NC}"
echo -e "  • API Phi-3     : ${GREEN}http://phi3-service:8000${NC} (interne)"
echo -e "  • API RAG       : ${GREEN}http://rag-api-service:8084${NC} (interne)"
echo ""
echo -e "${CYAN}Commandes utiles :${NC}"
echo -e "  • Voir les logs OpenWebUI : ${YELLOW}kubectl logs -f deployment/openwebui -n $NAMESPACE${NC}"
echo -e "  • Voir les logs Phi-3     : ${YELLOW}kubectl logs -f deployment/phi3 -n $NAMESPACE${NC}"
echo -e "  • Voir les logs RAG       : ${YELLOW}kubectl logs -f deployment/rag-api -n $NAMESPACE${NC}"
echo -e "  • Redémarrer tout         : ${YELLOW}$0 --only-restart${NC}"
echo ""
echo -e "${YELLOW}Note : Le premier démarrage de Phi-3 peut prendre 5-10 minutes${NC}"
echo -e "${YELLOW}       (téléchargement du modèle ~7 Go)${NC}"
echo ""
