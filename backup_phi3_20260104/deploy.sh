#!/bin/bash
echo "🚀 Déploiement Phi-3 + OpenWebUI"

# Créer le namespace
kubectl create namespace vllm-chat 2>/dev/null || echo "Namespace existe déjà"

# Appliquer les secrets
kubectl apply -f hf-secret.yaml

# Appliquer les PVCs
kubectl apply -f pvcs.yaml

# Attendre que les PVCs soient Bound
echo "⏳ Attente des PVCs..."
sleep 5

# Déployer Phi-3
kubectl apply -f phi3-service.yaml
kubectl apply -f phi3-deployment.yaml

# Attendre que Phi-3 soit prêt
echo "⏳ Attente de Phi-3 (peut prendre 5-10 min)..."
kubectl wait --for=condition=ready pod -l app=phi3-mini -n vllm-chat --timeout=600s

# Déployer OpenWebUI
kubectl apply -f openwebui-service.yaml
kubectl apply -f openwebui-deployment.yaml

echo "✅ Déploiement terminé !"
echo "📊 État des pods :"
kubectl get pods -n vllm-chat

echo ""
echo "🌐 Accès OpenWebUI : http://$(hostname -I | awk '{print $1}'):30183"
echo "🤖 API Phi-3 : http://$(hostname -I | awk '{print $1}'):30185"
