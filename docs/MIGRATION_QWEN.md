# Migration Phi3 → Qwen2.5-7B-Instruct-AWQ

## Étape 1 : Déployer Qwen2.5

```bash
kubectl apply -f k8s/qwen25-deployment.yaml
```

Attendre que le pod soit ready (peut prendre 5-10 min pour télécharger le modèle) :
```bash
kubectl get pods -n vllm-chat -w
kubectl logs -f deployment/qwen25 -n vllm-chat
```

## Étape 2 : Tester Qwen2.5

Test direct via curl :
```bash
curl http://<NODE_IP>:30179/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "Bonjour, qui es-tu ?"}],
    "max_tokens": 100
  }'
```

## Étape 3 : Basculer OpenWebUI vers Qwen2.5

Modifier `k8s/openwebui-deployment.yaml` :

```yaml
# Changer ces lignes :
- name: OPENAI_API_BASE_URLS
  value: "http://qwen25-service:8000/v1;http://rag-api-service:8084/v1"
- name: DEFAULT_MODELS
  value: "Qwen/Qwen2.5-7B-Instruct-AWQ"
- name: MODEL_FILTER_LIST
  value: "Qwen/Qwen2.5-7B-Instruct-AWQ;rag-anstat"
```

Puis rollout :
```bash
kubectl apply -f k8s/openwebui-deployment.yaml
kubectl rollout restart deployment/openwebui -n vllm-chat
```

## Étape 4 : Basculer le RAG vers Qwen2.5

Modifier `k8s/rag-search-deployment.yaml` :

```yaml
# Changer cette ligne :
- name: PHI3_API_URL
  value: "http://qwen25-service:8000/v1"
```

Puis rollout :
```bash
kubectl apply -f k8s/rag-search-deployment.yaml
kubectl rollout restart deployment/rag-api -n vllm-chat
```

## Étape 5 : Supprimer Phi3 (optionnel)

Une fois tout validé :
```bash
kubectl delete deployment phi3-mini -n vllm-chat
kubectl delete service phi3-service -n vllm-chat
```

## Rollback si problème

Remettre les anciennes valeurs dans les fichiers et réappliquer :
```bash
kubectl apply -f k8s/openwebui-deployment.yaml
kubectl apply -f k8s/rag-search-deployment.yaml
kubectl rollout restart deployment/openwebui -n vllm-chat
kubectl rollout restart deployment/rag-api -n vllm-chat
```
