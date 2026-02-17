# Relance ANSTAT AI - 24 janvier 2026

## Modifications effectuées

### 1. Favicon OpenWebUI
- Le `favicon.ico` fourni est maintenant utilisé directement (plus généré depuis le logo)
- Le `favicon.png` pour le chat est généré à partir de `favicon.ico`

**Fichiers modifiés :**
- `openwebui-custom/build-and-deploy.sh`
- `openwebui-custom/Dockerfile`

### 2. Optimisation RAG (latence 5min → ~30s)
- Reranker plus léger : `cross-encoder/ms-marco-MiniLM-L-2-v2` (10x plus rapide)
- Candidats réduits : 5 au lieu de 8
- Ressources augmentées : 20 CPU, 32Gi RAM, 16 threads

**Fichiers modifiés :**
- `rag/src/rag_api.py`
- `k8s/rag-search-deployment.yaml`

---

## Étapes de déploiement

### 1. Copier les fichiers vers le serveur

```bash
# Depuis le poste local
scp openwebui-custom/build-and-deploy.sh openwebui-custom/Dockerfile openwebui-custom/favicon.ico  migone@192.168.1.230:home/migone/vLLM_Deploy/openwebui-custom/

scp rag/src/rag_api.py k8s/rag-search-deployment.yaml migone@192.168.1.230:home/migone/vLLM_Deploy/rag/
```

### 2. Se connecter au serveur

```bash
ssh user@serveur
```

### 3. Déployer OpenWebUI (favicon)

```bash
cd ~/vLLM_Deploy/openwebui-custom

# Se connecter à ghcr.io (nécessaire pour pull l'image de base)
docker login ghcr.io

# Lancer le build et déploiement
./build-and-deploy.sh
```

### 4. Déployer RAG (optimisation performance)

```bash
cd ~/vLLM_Deploy/rag

# Rebuild l'image
docker build -t rag-api-phi3:latest .

# Appliquer la config et redémarrer
kubectl apply -f rag-deployment.yaml
kubectl rollout restart deployment/rag-api -n vllm-chat

# Vérifier le déploiement
kubectl get pods -n vllm-chat -l app=rag-api
kubectl logs -f deployment/rag-api -n vllm-chat
```

### 5. Vider le cache navigateur

Utilisez `Ctrl+Shift+R` pour voir le nouveau favicon.

---

## Vérification

```bash
# Statut des pods
kubectl get pods -n vllm-chat

# Test RAG
curl -X POST http://localhost:30184/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Quel est le PIB de la Côte d Ivoire ?"}'

# Stats RAG (cache, config)
curl http://localhost:30184/stats
```

---

## Rollback si problème

```bash
# RAG
kubectl rollout undo deployment/rag-api -n vllm-chat

# OpenWebUI
kubectl rollout undo deployment/openwebui -n vllm-chat
```
