# Backup Phi-3 + OpenWebUI

## Déploiement rapide
```bash
./deploy.sh
```

## Déploiement manuel
```bash
kubectl create namespace vllm-chat
kubectl apply -f hf-secret.yaml
kubectl apply -f pvcs.yaml
kubectl apply -f phi3-service.yaml
kubectl apply -f phi3-deployment.yaml
kubectl apply -f openwebui-service.yaml
kubectl apply -f openwebui-deployment.yaml
```

## Vérification
```bash
kubectl get pods -n vllm-chat
kubectl logs -f deployment/phi3-mini -n vllm-chat
```

## URLs

- OpenWebUI: http://192.168.1.230:30183
- API Phi-3: http://192.168.1.230:30185
