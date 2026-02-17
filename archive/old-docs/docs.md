# 🚀 Documentation Complète - Déploiement LLM Local avec Kubernetes

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Architecture](#architecture)
4. [Installation et Configuration](#installation-et-configuration)
5. [Démarrage Rapide](#démarrage-rapide)
6. [Gestion et Maintenance](#gestion-et-maintenance)
7. [Tests et Validation](#tests-et-validation)
8. [Dépannage](#dépannage)
9. [Optimisation](#optimisation)
10. [Sauvegarde et Restauration](#sauvegarde-et-restauration)

---

## 🎯 Vue d'ensemble

Cette documentation décrit le déploiement d'un LLM local (Gemma 3-1B) sur Kubernetes avec une interface web (OpenWebUI) pour interagir avec le modèle.

### Composants

- **Gemma 3-1B** : Modèle de langage Google de 1 milliard de paramètres
- **vLLM** : Moteur d'inférence haute performance
- **OpenWebUI** : Interface web pour interagir avec le modèle
- **Kubernetes** : Orchestration et gestion des conteneurs

### URLs d'accès

| Service | URL | Description |
|---------|-----|-------------|
| API Gemma3 | `http://192.168.1.230:30180` | API REST compatible OpenAI |
| OpenWebUI | `http://192.168.1.230:30183` | Interface web utilisateur |

---

## 🔧 Prérequis

### Matériel

- **GPU** : 1x NVIDIA GPU avec au moins 8Go VRAM
- **RAM** : Minimum 16Go (recommandé 32Go)
- **CPU** : Minimum 8 cores
- **Stockage** : Minimum 50Go disponible

### Logiciels

- **Kubernetes** : v1.20+
- **kubectl** : Installé et configuré
- **NVIDIA GPU Operator** : Pour le support GPU
- **StorageClass** : `local-path` ou équivalent

### Vérifications préalables

```bash
# Vérifier kubectl
kubectl version --client

# Vérifier l'accès au cluster
kubectl get nodes

# Vérifier le support GPU
kubectl get nodes -o json | jq '.items[].status.allocatable."nvidia.com/gpu"'

# Vérifier la StorageClass
kubectl get storageclass
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                  Utilisateur                    │
│              (Navigateur Web)                   │
└──────────────────┬──────────────────────────────┘
                   │
                   │ HTTP :30183
                   ▼
┌─────────────────────────────────────────────────┐
│            OpenWebUI Service                    │
│              (NodePort)                         │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│           OpenWebUI Pod                         │
│         (Interface Web)                         │
└──────────────────┬──────────────────────────────┘
                   │
                   │ HTTP :8000
                   ▼
┌─────────────────────────────────────────────────┐
│            Gemma3 Service                       │
│              (ClusterIP)                        │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│            Gemma3-1B Pod                        │
│         (vLLM + GPU)                            │
│                                                 │
│  ┌─────────────────────────────┐               │
│  │  PVC: gemma3-cache (30Gi)   │               │
│  │  /root/.cache/huggingface   │               │
│  └─────────────────────────────┘               │
└─────────────────────────────────────────────────┘
```

---

## 📦 Installation et Configuration

### Étape 1 : Créer le namespace

```bash
kubectl create namespace vllm-chat
```

### Étape 2 : Créer le secret HuggingFace (si nécessaire)

```bash
# Remplacer YOUR_HF_TOKEN par votre token HuggingFace
kubectl create secret generic hf-token-secret \
  --from-literal=token='YOUR_HF_TOKEN' \
  -n vllm-chat
```

### Étape 3 : Créer les fichiers de configuration

Créez les fichiers YAML suivants dans un dossier `~/vLLM_Deploy/` :

#### `gemma3-pvc.yaml`

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: gemma3-cache
  namespace: vllm-chat
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path
  resources:
    requests:
      storage: 30Gi
```

#### `gemma3-service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: gemma3-service
  namespace: vllm-chat
spec:
  selector:
    app: gemma3-1b
  ports:
  - name: http
    port: 8000
    targetPort: 8000
    nodePort: 30180
  type: NodePort
```

#### `gemma3-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gemma3-1b
  namespace: vllm-chat
  labels:
    app: gemma3-1b
spec:
  replicas: 1
  selector:
    matchLabels:
      app: gemma3-1b
  template:
    metadata:
      labels:
        app: gemma3-1b
    spec:
      volumes:
      - name: cache-volume
        persistentVolumeClaim:
          claimName: gemma3-cache
      - name: shm
        emptyDir:
          medium: Memory
          sizeLimit: "4Gi"
      containers:
      - name: gemma3-1b
        image: vllm/vllm-openai:v0.10.0
        command: ["/bin/sh", "-c"]
        args: [
          "vllm serve google/gemma-3-1b-it --dtype=float16 --tensor-parallel-size 1 --max-model-len 4096 --max-num-batched-tokens 4096 --trust-remote-code --gpu-memory-utilization 0.85"
        ]
        env:
        - name: HUGGING_FACE_HUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token-secret
              key: token
        ports:
        - containerPort: 8000
        resources:
          limits:
            cpu: "8"
            memory: 16G
            nvidia.com/gpu: "1"
          requests:
            cpu: "2"
            memory: 4G
            nvidia.com/gpu: "1"
        volumeMounts:
        - mountPath: /root/.cache/huggingface
          name: cache-volume
        - name: shm
          mountPath: /dev/shm
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 300
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 5
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 300
          periodSeconds: 10
          timeoutSeconds: 10
          failureThreshold: 3
```

#### `openwebui-pvc.yaml`

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: openwebui-data
  namespace: vllm-chat
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path
  resources:
    requests:
      storage: 10Gi
```

#### `openwebui-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openwebui
  namespace: vllm-chat
spec:
  replicas: 1
  selector:
    matchLabels:
      app: openwebui
  template:
    metadata:
      labels:
        app: openwebui
    spec:
      containers:
      - name: openwebui
        image: ghcr.io/open-webui/open-webui:main
        ports:
        - containerPort: 8080
        env:
        - name: OPENAI_API_BASE_URL
          value: "http://gemma3-service:8000/v1"
        - name: OPENAI_API_KEY
          value: "sk-dummy"
        - name: WEBUI_NAME
          value: "Gemma 3 Chat"
        volumeMounts:
        - name: webui-data
          mountPath: /app/backend/data
      volumes:
      - name: webui-data
        persistentVolumeClaim:
          claimName: openwebui-data
---
apiVersion: v1
kind: Service
metadata:
  name: openwebui-service
  namespace: vllm-chat
spec:
  selector:
    app: openwebui
  ports:
  - name: http
    port: 8080
    targetPort: 8080
    nodePort: 30183
  type: NodePort
```

---

## 🚀 Démarrage Rapide

### Déploiement complet depuis zéro

```bash
# 1. Créer le namespace
kubectl create namespace vllm-chat

# 2. Créer le secret HuggingFace
kubectl create secret generic hf-token-secret \
  --from-literal=token='YOUR_HF_TOKEN' \
  -n vllm-chat

# 3. Déployer dans l'ordre
cd ~/vLLM_Deploy

# PVC Gemma3
kubectl apply -f gemma3-pvc.yaml

# Attendre que le PVC soit Bound
kubectl get pvc gemma3-cache -n vllm-chat -w
# Appuyer sur Ctrl+C quand STATUS = Bound

# Service Gemma3
kubectl apply -f gemma3-service.yaml

# Déploiement Gemma3
kubectl apply -f gemma3-deployment.yaml

# PVC OpenWebUI
kubectl apply -f openwebui-pvc.yaml

# Attendre que le PVC soit Bound
kubectl get pvc openwebui-data -n vllm-chat -w
# Appuyer sur Ctrl+C quand STATUS = Bound

# OpenWebUI
kubectl apply -f openwebui-deployment.yaml

# 4. Surveiller le déploiement
kubectl get pods -n vllm-chat -w
```

### Temps de démarrage attendus

- **Gemma3** : ~5-7 minutes (téléchargement + chargement du modèle)
- **OpenWebUI** : ~30 secondes

### Vérification du déploiement

```bash
# Vérifier que tous les pods sont Running
kubectl get pods -n vllm-chat

# Résultat attendu :
# NAME                         READY   STATUS    RESTARTS   AGE
# gemma3-1b-xxxxx-xxxxx        1/1     Running   0          7m
# openwebui-xxxxx-xxxxx        1/1     Running   0          2m

# Vérifier les services
kubectl get svc -n vllm-chat

# Tester l'API Gemma3
curl http://192.168.1.230:30180/health

# Tester OpenWebUI
curl -I http://192.168.1.230:30183
```

---

## 🔄 Gestion et Maintenance

### Démarrer les services

```bash
# Si les déploiements existent mais sont à 0 replicas
kubectl scale deployment gemma3-1b -n vllm-chat --replicas=1
kubectl scale deployment openwebui -n vllm-chat --replicas=1
```

### Arrêter les services

```bash
# Mettre les replicas à 0 (conserve la configuration)
kubectl scale deployment gemma3-1b -n vllm-chat --replicas=0
kubectl scale deployment openwebui -n vllm-chat --replicas=0

# Vérifier que les pods sont arrêtés
kubectl get pods -n vllm-chat
```

### Redémarrer un service

```bash
# Redémarrer Gemma3
kubectl rollout restart deployment/gemma3-1b -n vllm-chat

# Redémarrer OpenWebUI
kubectl rollout restart deployment/openwebui -n vllm-chat

# Surveiller le redémarrage
kubectl rollout status deployment/gemma3-1b -n vllm-chat
```

### Voir les logs

```bash
# Logs Gemma3 en temps réel
kubectl logs -n vllm-chat -l app=gemma3-1b -f

# Logs OpenWebUI en temps réel
kubectl logs -n vllm-chat -l app=openwebui -f

# Derniers 100 logs
kubectl logs -n vllm-chat -l app=gemma3-1b --tail=100
```

### Surveiller les ressources

```bash
# Utilisation CPU/RAM des pods
kubectl top pods -n vllm-chat

# Détails d'un pod
kubectl describe pod -n vllm-chat <pod-name>

# Événements récents
kubectl get events -n vllm-chat --sort-by='.lastTimestamp' | tail -20
```

---

## 🧪 Tests et Validation

### Test de l'API Gemma3

```bash
# Test de santé
curl http://192.168.1.230:30180/health

# Lister les modèles
curl http://192.168.1.230:30180/v1/models

# Test de génération simple
curl http://192.168.1.230:30180/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-3-1b-it",
    "messages": [
      {"role": "user", "content": "Bonjour, présente-toi en une phrase."}
    ],
    "max_tokens": 50,
    "temperature": 0.7
  }'
```

### Test de génération avec streaming

```bash
curl http://192.168.1.230:30180/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-3-1b-it",
    "messages": [
      {"role": "user", "content": "Écris un court poème sur l'\''IA."}
    ],
    "max_tokens": 100,
    "stream": true
  }'
```

### Benchmark de performance

```bash
# Installation de l'outil de benchmark (si disponible)
pip install vllm

# Lancer un benchmark
python -m vllm.entrypoints.openai.api_server \
  --model google/gemma-3-1b-it \
  --benchmark
```

---

## 🔧 Dépannage

### Problème : Pod en CrashLoopBackOff

**Diagnostic :**
```bash
kubectl logs -n vllm-chat <pod-name> --previous
kubectl describe pod -n vllm-chat <pod-name>
```

**Solutions courantes :**
- Vérifier que le GPU est disponible : `kubectl get nodes -o json | jq '.items[].status.allocatable."nvidia.com/gpu"'`
- Vérifier l'espace disque du PVC
- Vérifier le token HuggingFace

### Problème : Pod en Pending

**Diagnostic :**
```bash
kubectl describe pod -n vllm-chat <pod-name>
```

**Solutions courantes :**
- PVC non Bound : `kubectl get pvc -n vllm-chat`
- Pas de GPU disponible : Réduire les replicas ou libérer un GPU
- Resources insuffisantes : Vérifier `kubectl describe nodes`

### Problème : Pod Running mais pas Ready (0/1)

**Diagnostic :**
```bash
kubectl logs -n vllm-chat <pod-name> -f
```

**Explication :**
- Pour Gemma3, c'est normal pendant 5-7 minutes (téléchargement + chargement)
- Les readiness probes ont un `initialDelaySeconds: 300`

### Problème : Connection refused sur NodePort

**Diagnostic :**
```bash
# Vérifier les endpoints
kubectl get endpoints -n vllm-chat

# Vérifier le service
kubectl get svc -n vllm-chat

# Tester depuis l'intérieur du cluster
kubectl run test --rm -it --image=curlimages/curl --restart=Never -n vllm-chat -- \
  curl http://gemma3-service:8000/health
```

**Solutions :**
- Vérifier que le pod est Ready (1/1)
- Vérifier le pare-feu : `sudo ufw allow 30180/tcp && sudo ufw allow 30183/tcp`
- Tester avec l'IP locale : `curl http://127.0.0.1:30180/health`

### Problème : Modèle ne se télécharge pas

**Diagnostic :**
```bash
kubectl logs -n vllm-chat -l app=gemma3-1b | grep -i "download\|error"
```

**Solutions :**
- Vérifier le token HuggingFace
- Vérifier la connectivité internet du pod
- Vérifier l'espace disque du PVC : `kubectl describe pvc gemma3-cache -n vllm-chat`

### Problème : Out of Memory (OOM)

**Symptômes :**
```bash
kubectl get pods -n vllm-chat
# Pod en état OOMKilled
```

**Solutions :**
```bash
# Réduire l'utilisation GPU
kubectl set env deployment/gemma3-1b -n vllm-chat \
  VLLM_GPU_MEMORY_UTILIZATION=0.7

# Ou éditer le déploiement
kubectl edit deployment gemma3-1b -n vllm-chat
# Modifier --gpu-memory-utilization 0.85 → 0.7
```

---

## ⚡ Optimisation

### Ajuster l'utilisation de la mémoire GPU

```bash
# Éditer le déploiement
kubectl edit deployment gemma3-1b -n vllm-chat

# Modifier la ligne dans args:
# --gpu-memory-utilization 0.85 → 0.9 (plus agressif)
# --gpu-memory-utilization 0.85 → 0.7 (plus conservateur)
```

### Augmenter la longueur de contexte

```bash
kubectl edit deployment gemma3-1b -n vllm-chat

# Modifier dans args:
# --max-model-len 4096 → 8192
# --max-num-batched-tokens 4096 → 8192
```

### Activer le multi-GPU (si disponible)

```bash
# Éditer le déploiement
kubectl edit deployment gemma3-1b -n vllm-chat

# Modifier:
# --tensor-parallel-size 1 → 2 (pour 2 GPUs)
# resources.limits.nvidia.com/gpu: "1" → "2"
# resources.requests.nvidia.com/gpu: "1" → "2"
```

### Scaler horizontalement (Load Balancing)

```bash
# Augmenter le nombre de replicas
kubectl scale deployment gemma3-1b -n vllm-chat --replicas=2

# Note: Nécessite 2 GPUs disponibles
```

---

## 💾 Sauvegarde et Restauration

### Sauvegarder la configuration

```bash
# Créer un dossier de sauvegarde
mkdir -p ~/vLLM_Deploy/backup_$(date +%Y%m%d)

# Exporter toutes les ressources
kubectl get all -n vllm-chat -o yaml > ~/vLLM_Deploy/backup_$(date +%Y%m%d)/all-resources.yaml
kubectl get pvc -n vllm-chat -o yaml > ~/vLLM_Deploy/backup_$(date +%Y%m%d)/pvcs.yaml
kubectl get secret hf-token-secret -n vllm-chat -o yaml > ~/vLLM_Deploy/backup_$(date +%Y%m%d)/secrets.yaml
kubectl get configmap -n vllm-chat -o yaml > ~/vLLM_Deploy/backup_$(date +%Y%m%d)/configmaps.yaml
```

### Sauvegarder les données

```bash
# Sauvegarder le cache du modèle (optionnel, peut être re-téléchargé)
# Note: Cela peut être volumineux (plusieurs Go)

# Créer un pod temporaire pour accéder au PVC
kubectl run backup-pod --rm -it --image=busybox -n vllm-chat \
  --overrides='
  {
    "spec": {
      "containers": [{
        "name": "backup",
        "image": "busybox",
        "command": ["sleep", "3600"],
        "volumeMounts": [{
          "name": "cache",
          "mountPath": "/cache"
        }]
      }],
      "volumes": [{
        "name": "cache",
        "persistentVolumeClaim": {
          "claimName": "gemma3-cache"
        }
      }]
    }
  }' -- sh

# Dans le pod, créer une archive
tar czf /cache/backup.tar.gz /cache/models
exit

# Copier l'archive hors du pod
kubectl cp vllm-chat/backup-pod:/cache/backup.tar.gz ~/vLLM_Deploy/backup_$(date +%Y%m%d)/model-cache.tar.gz
```

### Restaurer depuis une sauvegarde

```bash
# Restaurer les ressources
cd ~/vLLM_Deploy/backup_YYYYMMDD

kubectl apply -f secrets.yaml
kubectl apply -f pvcs.yaml
kubectl apply -f all-resources.yaml
```

---

## 📊 Monitoring et Métriques

### Métriques Prometheus (si installé)

```bash
# Accéder aux métriques vLLM
curl http://192.168.1.230:30180/metrics

# Métriques disponibles :
# - vllm_num_requests_running
# - vllm_num_requests_waiting
# - vllm_gpu_cache_usage_perc
# - vllm_time_to_first_token_seconds
# - vllm_time_per_output_token_seconds
```

### Dashboard Kubernetes

```bash
# Si Kubernetes Dashboard est installé
kubectl proxy
# Accéder via http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/
```

---

## 🔐 Sécurité

### Bonnes pratiques

1. **Ne pas exposer les NodePorts publiquement**
   - Utiliser un Ingress avec TLS
   - Configurer un VPN ou un bastion

2. **Changer le token API OpenWebUI**
   ```bash
   kubectl set env deployment/openwebui -n vllm-chat \
     OPENAI_API_KEY="votre-token-securise"
   ```

3. **Activer l'authentification OpenWebUI**
   - Premier utilisateur = admin
   - Configurer les rôles et permissions

4. **Limiter les ressources**
   - Les limits/requests empêchent l'épuisement des ressources

### Mise à jour des images

```bash
# Mettre à jour vLLM
kubectl set image deployment/gemma3-1b -n vllm-chat \
  gemma3-1b=vllm/vllm-openai:v0.11.0

# Mettre à jour OpenWebUI
kubectl set image deployment/openwebui -n vllm-chat \
  openwebui=ghcr.io/open-webui/open-webui:latest
```

---

## 📚 Ressources supplémentaires

### Documentation officielle

- **vLLM** : https://docs.vllm.ai/
- **OpenWebUI** : https://docs.openwebui.com/
- **Gemma** : https://ai.google.dev/gemma
- **Kubernetes** : https://kubernetes.io/docs/

### Communauté

- **vLLM GitHub** : https://github.com/vllm-project/vllm
- **OpenWebUI GitHub** : https://github.com/open-webui/open-webui

---

## 🆘 Support

En cas de problème :

1. Vérifier les logs : `kubectl logs -n vllm-chat -l app=gemma3-1b --tail=100`
2. Vérifier les événements : `kubectl get events -n vllm-chat`
3. Consulter la section Dépannage ci-dessus
4. Rechercher dans les issues GitHub des projets

---

## 📝 Changelog

### v1.0 (2026-01-04)
- Déploiement initial Gemma 3-1B
- Configuration OpenWebUI
- Documentation complète

---

**Auteur** : Documentation générée le 2026-01-04  
**Version** : 1.0  
**Dernière mise à jour** : 2026-01-04