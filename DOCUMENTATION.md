# Documentation Élaborée - Plateforme ANSTAT AI

## Vue d'ensemble

La plateforme ANSTAT AI est une solution complète de chat IA auto-hébergée développée pour l'Agence Nationale de la Statistique de Côte d'Ivoire. Elle combine un modèle de langage avancé (Qwen2.5-7B) avec un système de Retrieval-Augmented Generation (RAG) spécialisé dans les documents statistiques de l'ANSTAT.

### Objectifs principaux
- Fournir une interface de chat intuitive pour les utilisateurs
- Permettre des recherches documentaires précises sur les données statistiques
- Assurer une confidentialité totale des données (hébergement local)
- Offrir des réponses fiables basées sur des sources vérifiées

---

## Architecture détaillée

### Architecture générale

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
│  │  │   (Frontend)    │    │   (LLM API)     │  ┌─────────────┐  │  │
│  │  │   Port: 8080    │    │   Port: 8000    │  │  RAG Pipe   │  │  │
│  │  │   + RAG Pipe    │    └─────────────────┘  │ (orchestration│  │  │
│  │  └────────┬────────┘                        └─────────────┘  │  │
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
│  │  │  - openwebui-data (10Gi) - Données utilisateurs         │  │  │
│  │  │  - qwen25-cache (30Gi) - Cache modèles LLM              │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Flux de données RAG

1. **Requête utilisateur** : Question posée dans OpenWebUI
2. **Recherche documentaire** : Le pipe RAG interroge le service de recherche FAISS
3. **Récupération des chunks** : Les 10 chunks les plus pertinents sont récupérés
4. **Reranking** : Les chunks sont réordonnés par pertinence sémantique
5. **Construction du prompt** : Les 5 meilleurs chunks sont intégrés au prompt
6. **Génération de réponse** : Qwen2.5 génère la réponse en streaming
7. **Affichage** : Réponse avec citations des sources

---

## Composants détaillés

### 1. OpenWebUI (Interface utilisateur)

**Rôle** : Interface web moderne pour l'interaction avec les modèles IA.

**Technologies** :
- Framework : SvelteKit
- Base de données : SQLite (données utilisateurs, conversations)
- Authentification : Comptes locaux
- Thème personnalisé : ANSTAT (CSS custom)

**Fonctionnalités** :
- Chat en temps réel avec streaming
- Gestion des utilisateurs et permissions
- Administration des modèles et pipes
- Interface responsive

**Configuration** :
- Port interne : 8080
- Volume persistant : 10 Gi (données utilisateurs)
- Image Docker : `openwebui-anstat:latest`

### 2. Qwen2.5-7B-Instruct (Modèle de langage)

**Rôle** : Génération de réponses intelligentes et contextuelles.

**Spécifications** :
- Modèle : Qwen2.5-7B-Instruct-AWQ
- Quantization : 4-bit AWQ (optimisé pour GPU)
- Framework : vLLM (inférence optimisée)
- GPU requis : NVIDIA avec 16+ Go VRAM

**Configuration vLLM** :
- Port : 8000
- API : OpenAI-compatible (/v1/chat/completions)
- Cache : 30 Gi persistent volume
- Paramètres : temperature=0.05, max_tokens=800

### 3. RAG Search Service (Recherche documentaire)

**Rôle** : Service de recherche sémantique dans les documents ANSTAT.

**Technologies** :
- Framework : FastAPI
- Base de données vectorielle : FAISS
- Modèle d'embedding : paraphrase-multilingual-MiniLM-L12-v2
- Reranker : cross-encoder/ms-marco-MiniLM-L-2-v2

**Données indexées** :
- 38 documents statistiques (EHCVM, EDS, ENV, etc.)
- 9 234 chunks textuels
- Dimensions : 384 (embeddings multilingues)

**API Endpoints** :
- `GET /health` : État du service
- `POST /search` : Recherche sémantique

### 4. RAG Pipe (Orchestration)

**Rôle** : Pipeline d'orchestration entre recherche et génération.

**Fonctionnement** :
1. Reçoit la requête utilisateur
2. Interroge le service de recherche
3. Filtre les résultats (score > 0.35)
4. Construit le prompt avec contexte
5. Streame la réponse depuis le LLM

**Configuration** :
- URL recherche : `http://rag-search-service:8084/search`
- URL LLM : `http://qwen25-service:8000/v1`
- Timeout : 60 secondes
- Température : 0.05

---

## Système RAG (Retrieval-Augmented Generation)

### Préparation des données

#### 1. Chunking des documents

**Script** : `rag/scripts/anstat_preparation_fast.py`

**Processus** :
- Lecture des PDF/DOCX/TXT
- Extraction du texte brut
- Découpage en chunks (512 tokens max)
- Métadonnées : titre, page, source
- Sauvegarde : JSON par document

**Paramètres** :
- Taille chunk : 512 tokens
- Overlap : 50 tokens
- Langage : Français/Anglais

#### 2. Génération des embeddings

**Script** : `rag/scripts/anstat_embedding_and_faiss.py`

**Modèle** : sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

**Sorties** :
- `faiss_index.bin` : Index FAISS (9 234 vecteurs × 384 dim)
- `chunk_map.json` : Mapping chunk_id → contenu + métadonnées
- `embeddings.npz` : Embeddings compressés
- `metadata.json` : Statistiques globales

#### 3. Recherche et reranking

**Algorithme** :
1. Embedding de la requête
2. Recherche FAISS : top-10 similaires (cosine)
3. Reranking : cross-encoder pour top-5
4. Filtrage : score > 0.35

**Optimisations** :
- Cache des embeddings (LRU 256)
- Threads FAISS : 4
- Normalisation des embeddings

### Limites et recommandations

#### Limites du système
- **Couverture** : Uniquement les documents indexés
- **Langage** : Principalement français
- **Contexte** : Maximum 5 chunks par réponse
- **Hallucinations** : Possibles malgré le RAG

#### Recommandations d'usage
- Questions précises pour meilleurs résultats
- Vérification des sources citées
- Reformulation si réponse incomplète
- Usage comme outil d'aide, pas source ultime

---

## Fine-tuning LoRA

### Objectif

Adapter le modèle Phi-3.5-mini aux méthodologies statistiques ANSTAT.

### Pipeline de fine-tuning

#### 1. Collecte des données

**Sources** : Documents méthodologiques ANSTAT (PDF, DOCX)

**Script de parsing** : `parse_methodologies.py`

**Format de sortie** : JSONL avec instruction/output

#### 2. Configuration d'entraînement

**Fichier** : `config/training_config.yaml`

**Paramètres clés** :
- Modèle base : Phi-3.5-mini
- Technique : LoRA (QLoRA pour GPU limités)
- Epochs : 3
- Batch size : 4
- Learning rate : 2e-4

#### 3. Entraînement

**Script** : `train_lora.py`

**Sorties** :
- Adaptateurs LoRA
- Logs d'entraînement
- Métriques de performance

#### 4. Fusion des poids

**Script** : `merge_lora.py`

**Résultat** : Modèle complet fine-tuné

### Déploiement du modèle fine-tuné

**Manifest K8s** : `k8s/phi3-anstat-deployment.yaml`

**Configuration** :
- GPU requis
- vLLM pour inférence
- Cache modèle

---

## Déploiement Kubernetes

### Prérequis infrastructure

#### Matériel minimum
- CPU : 8 cores
- RAM : 32 Go
- GPU : NVIDIA 16 Go VRAM
- Stockage : 100 Go SSD

#### Logiciels
- Kubernetes 1.25+
- Docker 20+
- NVIDIA Container Toolkit
- Cert-Manager (pour TLS)

### Manifests principaux

#### Services
- `qwen25-deployment.yaml` : Déploiement Qwen2.5
- `rag-search-deployment.yaml` : Service de recherche
- `openwebui-deployment.yaml` : Interface web
- `ingress.yaml` : Routage HTTPS

#### Stockage
- `pvcs.yaml` : Volumes persistants
- `openwebui-pvc.yaml` : Données utilisateurs

#### Sécurité
- `hf-secret.yaml` : Token HuggingFace

### Procédure de déploiement

1. **Préparation du cluster**
   ```bash
   kubectl create namespace vllm-chat
   kubectl apply -f k8s/hf-secret.yaml
   kubectl apply -f k8s/pvcs.yaml
   ```

2. **Déploiement des services**
   ```bash
   kubectl apply -f k8s/qwen25-deployment.yaml
   kubectl apply -f k8s/rag-search-deployment.yaml
   kubectl apply -f k8s/openwebui-deployment.yaml
   kubectl apply -f k8s/ingress.yaml
   ```

3. **Vérification**
   ```bash
   kubectl get pods -n vllm-chat
   kubectl get svc -n vllm-chat
   ```

### Configuration TLS

**Cert-Manager** : Génère automatiquement les certificats Let's Encrypt

**Domaine** : chat.anstat.ci

**Challenge** : HTTP-01

---

## Personnalisation OpenWebUI

### Thème ANSTAT

**Fichiers** :
- `custom-anstat.css` : Styles CSS
- `favicon.ico` : Icône personnalisée

**Build** :
```bash
cd openwebui-custom
docker build -t openwebui-anstat:latest .
```

### Pipe RAG

**Fichier** : `rag/pipe/openwebui_pipe.py`

**Installation** :
1. Interface admin OpenWebUI
2. Créer nouvelle fonction
3. Coller le code du pipe
4. Configurer les valves

---

## Maintenance et monitoring

### Surveillance des pods

```bash
# État des pods
kubectl get pods -n vllm-chat

# Logs en temps réel
kubectl logs -f deployment/openwebui -n vllm-chat
kubectl logs -f deployment/qwen25 -n vllm-chat
kubectl logs -f deployment/rag-search -n vllm-chat
```

### Tests de santé

```bash
# API Qwen2.5
curl http://qwen25-service:8000/v1/models

# Service RAG
curl http://rag-search-service:8084/health

# OpenWebUI
curl -I https://chat.anstat.ci
```

### Mises à jour

#### Modèle RAG
1. Ajouter nouveaux documents
2. Régénérer chunks et embeddings
3. Rebuild image Docker
4. Redémarrer pod

#### OpenWebUI
```bash
cd openwebui-custom
docker build -t openwebui-anstat:latest .
kubectl rollout restart deployment/openwebui -n vllm-chat
```

### Sauvegarde

**Données à sauvegarder** :
- Volume OpenWebUI (conversations utilisateurs)
- Cache modèles Qwen2.5
- Index FAISS et métadonnées RAG

---

## Évolutions planifiées

### Améliorations RAG (février 2026)

#### Techniques avancées
- **HyDE** : Hypothetical Document Embeddings
- **BM25** : Recherche hybride sparse/dense
- **CLaRa** : Contextual Late Retrieval-Augmentation

#### Architecture
- Base de données vectorielle (Pinecone/Chroma)
- Cache Redis pour les embeddings
- API asynchrone pour meilleure scalabilité

### Migration potentielle
- Modèle plus grand (Qwen2.5-14B/72B)
- GPU additionnel pour parallélisation
- Load balancing multi-pods

---

## Annexes

### Glossaire

- **AWQ** : Activation-aware Weight Quantization
- **Chunk** : Segment de texte extrait d'un document
- **Embedding** : Représentation vectorielle du texte
- **FAISS** : Facebook AI Similarity Search
- **LoRA** : Low-Rank Adaptation
- **RAG** : Retrieval-Augmented Generation
- **vLLM** : Framework d'inférence LLM optimisé

### Références

- [Documentation vLLM](https://vllm.readthedocs.io/)
- [OpenWebUI](https://openwebui.com/)
- [Qwen2.5](https://qwenlm.github.io/)
- [Sentence Transformers](https://sbert.net/)

### Contacts

- **Équipe technique** : Support ANSTAT
- **Administration** : admin@anstat.ci

---

*Documentation générée le 17 février 2026*</content>
<parameter name="filePath">c:\Users\f.migone\Desktop\projects\vLLM_Deploy\DOCUMENTATION.md