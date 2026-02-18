# ANSTAT AI - Plateforme de Chat IA

**Agence Nationale de la Statistique - Cote d'Ivoire**

Plateforme de chat IA auto-hebergee avec support RAG (Retrieval-Augmented Generation) pour les documents statistiques.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INTERNET                                     │
│                            │                                         │
│                     chat.anstat.ci                                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                                │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                 NGINX Ingress Controller                       │  │
│  │                 (TLS/SSL + CORS + Load Balancing)              │  │
│  └───────────────────────────┬───────────────────────────────────┘  │
│                              │                                       │
│  ┌───────────────────────────▼───────────────────────────────────┐  │
│  │                      NAMESPACE: vllm-chat                      │  │
│  │                                                                │  │
│  │  ┌─────────────────┐    ┌─────────────────┐                   │  │
│  │  │   OpenWebUI     │───▶│  Qwen2.5 (vLLM) │                   │  │
│  │  │   (Frontend)    │    │   (LLM API)     │                   │  │
│  │  │   Port: 8080    │    │   Port: 8000    │                   │  │
│  │  │   + RAG Pipe    │    └─────────────────┘                   │  │
│  │  └────────┬────────┘                                          │  │
│  │           │                                                    │  │
│  │           ▼                                                    │  │
│  │  ┌─────────────────┐                                          │  │
│  │  │  RAG Search     │                                          │  │
│  │  │  (FastAPI)      │                                          │  │
│  │  │  Port: 8084     │                                          │  │
│  │  │  FAISS+reranker │                                          │  │
│  │  └─────────────────┘                                          │  │
│  │                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │                 Persistent Volumes                       │  │  │
│  │  │  - openwebui-data (10Gi) - Donnees utilisateurs         │  │  │
│  │  │  - qwen25-cache (30Gi) - Cache modeles LLM              │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Composants

| Composant | Image | Port | Role |
|-----------|-------|------|------|
| **OpenWebUI** | `openwebui-anstat:latest` | 8080 | Interface web + Pipe RAG |
| **Qwen2.5** | `vllm/vllm-openai:v0.10.0` | 8000 | LLM (GPU, AWQ 4-bit) |
| **RAG Search** | `rag-search-anstat:latest` | 8084 | Recherche FAISS + reranking (CPU) |
| **NGINX Ingress** | - | 80, 443 | Reverse proxy, TLS, CORS |

---

## Prerequis

### Materiel minimum

| Ressource | Minimum | Recommande |
|-----------|---------|------------|
| CPU | 8 cores | 16 cores |
| RAM | 32 Go | 64 Go |
| GPU | 1x NVIDIA (16 Go VRAM) | 1x NVIDIA (24 Go VRAM) |
| Stockage | 100 Go SSD | 200 Go NVMe |

### Logiciels requis

```bash
kubectl version --client    # Kubernetes v1.25+
docker --version            # Docker v20+
nvidia-smi                  # GPU Driver NVIDIA + nvidia-container-toolkit
```

### Acces reseau

- Port 80 (HTTP) - pour la redirection et Let's Encrypt
- Port 443 (HTTPS) - pour le trafic principal
- Domaine configure : `chat.anstat.ci`

---

## Structure du projet

```
vLLM_Deploy/
├── README.md                          # Ce fichier
│
├── docs/                              # Documentation
│   ├── DEPLOY_RAG.md                  # Guide de deploiement RAG complet
│   ├── MIGRATION_QWEN.md             # Migration Phi3 → Qwen2.5
│   ├── COPIER_COLLER_MODELE.md        # Copie du modele vers le cluster
│   ├── README_RELANCE_20260124.md     # Notes relance janvier 2026
│   └── improvements_18-02-2026.md     # Ameliorations RAG planifiees
│
├── k8s/                               # Manifests Kubernetes
│   ├── qwen25-deployment.yaml         # Deploiement Qwen2.5 (GPU)
│   ├── rag-search-deployment.yaml     # Deploiement RAG Search (CPU)
│   ├── openwebui-deployment.yaml      # Deploiement OpenWebUI
│   ├── openwebui-pvc.yaml             # PVC OpenWebUI
│   ├── openwebui-service.yaml         # Service OpenWebUI
│   ├── ingress.yaml                   # Ingress TLS (chat.anstat.ci)
│   ├── pvcs.yaml                      # Persistent Volume Claims
│   └── hf-secret.yaml                # Secret HuggingFace
│
├── openwebui-custom/                  # Image Docker OpenWebUI personnalisee
│   ├── Dockerfile                     # Image avec theme ANSTAT
│   ├── build-and-deploy.sh            # Script de build automatise
│   ├── custom-anstat.css              # Theme CSS ANSTAT
│   └── favicon.ico                    # Favicon ANSTAT
│
├── rag/                               # Systeme RAG
│   ├── src/rag_api.py                 # API de recherche (FAISS + reranker)
│   ├── pipe/openwebui_pipe.py         # Pipe OpenWebUI (colle dans l'UI)
│   ├── scripts/                       # Preparation des donnees
│   │   ├── anstat_preparation_fast.py # Chunking des documents
│   │   └── anstat_embedding_and_faiss.py  # Generation embeddings + index
│   ├── data/
│   │   ├── chunks/                    # 38 fichiers JSON (chunks par document)
│   │   └── embeddings/                # Index FAISS + chunk_map + metadata
│   ├── Dockerfile                     # Image Docker RAG Search
│   └── requirements.txt              # Dependances Python
│
├── finetuning/                        # Fine-tuning LoRA
│   ├── train_lora.py                  # Script d'entrainement
│   ├── merge_lora.py                  # Fusion des poids LoRA
│   ├── parse_methodologies.py         # Parsing des fiches methodologiques
│   ├── config/                        # Configuration d'entrainement
│   ├── data/                          # Donnees d'entrainement
│   ├── k8s/                           # Jobs K8s de fine-tuning
│   ├── Dockerfile                     # Image Docker fine-tuning
│   └── requirements.txt              # Dependances
│
├── presentation/                      # Fichiers de presentation
│   ├── presentation_anstat_ai.md/pdf/html
│   └── chat_anstat_ci.pptx
│
├── assets/                            # Images et logos
│   └── logo ANSTAT_PRINCIPAL.png
│
└── archive/                           # Anciennes configs (reference)
    ├── phi3/                          # Anciens deploiements Phi-3
    ├── rag-service-v1/                # Ancien service RAG (bge-large)
    └── old-docs/                      # Documentation obsolete
```

---

## Installation rapide

```bash
# 1. Cloner le projet
git clone <repo-url> vLLM_Deploy
cd vLLM_Deploy

# 2. Creer le namespace
kubectl create namespace vllm-chat

# 3. Deployer les composants
kubectl apply -f k8s/hf-secret.yaml
kubectl apply -f k8s/pvcs.yaml
kubectl apply -f k8s/qwen25-deployment.yaml
kubectl apply -f k8s/rag-search-deployment.yaml
kubectl apply -f k8s/openwebui-deployment.yaml
kubectl apply -f k8s/openwebui-service.yaml
kubectl apply -f k8s/openwebui-pvc.yaml
kubectl apply -f k8s/ingress.yaml

# 4. Verifier le statut
kubectl get pods -n vllm-chat
```

Pour le deploiement detaille du RAG, voir `docs/DEPLOY_RAG.md`.

---

## Verification du deploiement

```bash
# Tous les pods
kubectl get pods -n vllm-chat

# Resultat attendu :
# NAME                        READY   STATUS    RESTARTS   AGE
# qwen25-xxxxx                1/1     Running   0          10m
# rag-search-xxxxx            1/1     Running   0          5m
# openwebui-xxxxx             1/1     Running   0          3m

# Tous les services
kubectl get svc -n vllm-chat
```

### Tester les endpoints

```bash
# Tester Qwen2.5
kubectl exec -it deployment/openwebui -n vllm-chat -- \
  curl -s http://qwen25-service:8000/v1/models

# Tester RAG Search
kubectl exec -it deployment/openwebui -n vllm-chat -- \
  curl -s http://rag-search-service:8084/health

# Tester OpenWebUI
curl -I https://chat.anstat.ci
```

---

## Utilisation

### Acces a l'interface

1. Ouvrir https://chat.anstat.ci
2. Creer un compte (premier compte = admin)
3. Se connecter

### Modeles disponibles

| Modele | Description | Usage |
|--------|-------------|-------|
| **Qwen2.5-7B-Instruct-AWQ** | Chat general | Questions generales, redaction, code |
| **RAG ANSTAT** | Questions sur documents | Statistiques, donnees ANSTAT |

---

## Maintenance

### Voir les logs

```bash
kubectl logs -f deployment/openwebui -n vllm-chat
kubectl logs -f deployment/qwen25 -n vllm-chat
kubectl logs -f deployment/rag-search -n vllm-chat
```

### Redemarrer un service

```bash
kubectl rollout restart deployment/openwebui -n vllm-chat
kubectl rollout restart deployment/qwen25 -n vllm-chat
kubectl rollout restart deployment/rag-search -n vllm-chat
```

### Mettre a jour OpenWebUI

```bash
cd openwebui-custom
docker build -t openwebui-anstat:latest .
kubectl rollout restart deployment/openwebui -n vllm-chat
```

### Mettre a jour les documents RAG

Voir la section dediee dans `docs/DEPLOY_RAG.md`.

---

## Troubleshooting

### Pod en CrashLoopBackOff

```bash
kubectl logs <pod-name> -n vllm-chat --previous
kubectl describe pod <pod-name> -n vllm-chat
```

### OpenWebUI ne se connecte pas aux APIs

```bash
kubectl exec -it deployment/openwebui -n vllm-chat -- bash
# Dans le pod :
curl http://qwen25-service:8000/v1/models
curl http://rag-search-service:8084/health
```

### Certificat TLS non genere

```bash
kubectl get certificate -n vllm-chat
kubectl get challenges -n vllm-chat
kubectl logs -n cert-manager deployment/cert-manager
```

---

## Documentation complementaire

| Document | Description |
|----------|-------------|
| `docs/DEPLOY_RAG.md` | Guide complet de deploiement du RAG |
| `docs/MIGRATION_QWEN.md` | Migration Phi3 vers Qwen2.5 |
| `docs/improvements_18-02-2026.md` | Ameliorations RAG planifiees (HyDE, BM25, CLaRa) |

---

## Contacts

- **Admin**: cae@stat.plan.gouv.ci

---

## Licence

Projet interne ANSTAT - Agence Nationale de la Statistique de Cote d'Ivoire.

---

*Derniere mise a jour : Fevrier 2026*
