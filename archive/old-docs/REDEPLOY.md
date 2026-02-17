# Redéploiement ANSTAT AI

## 1. Rebuild des images Docker

```bash
# Image OpenWebUI personnalisée
docker build -t openwebui-anstat:latest ./backup_phi3_20260104/openwebui-custom/

# Image RAG API
docker build -t rag-api-phi3:latest ./rag-service/
```

## 2. Déploiement Kubernetes

```bash
# Namespace (si pas déjà créé)
kubectl create namespace vllm-chat --dry-run=client -o yaml | kubectl apply -f -

# Appliquer les configs
kubectl apply -f backup_phi3_20260104/openwebui-deployment.yaml
kubectl apply -f backup_phi3_20260104/phi3-deployment.yaml
kubectl apply -f rag-service/rag-deployment.yaml
kubectl apply -f backup_phi3_20260104/ingress.yaml
```

## 3. Redémarrer les pods (forcer le pull des nouvelles images)

```bash
kubectl rollout restart deployment/openwebui -n vllm-chat
kubectl rollout restart deployment/rag-api -n vllm-chat
```

## 4. Vérification

```bash
# Status des pods
kubectl get pods -n vllm-chat

# Logs en temps réel
kubectl logs -f deployment/openwebui -n vllm-chat
kubectl logs -f deployment/rag-api -n vllm-chat

# Health check RAG
curl http://<NODE_IP>:30184/health
```

## Modifications appliquées

| Changement | Détail |
|------------|--------|
| Logo filigrane | Désactivé dans le CSS |
| Modèles filtrés | Seuls Phi-3 et RAG visibles |
| RAM RAG | 8Gi → 12Gi |
| Reranker | bge-large → bge-base |
| Health checks | Ajoutés sur RAG API |
| Suggestions prompts | Format JSON corrigé (YAML littéral) |
