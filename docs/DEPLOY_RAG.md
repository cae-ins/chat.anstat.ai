# Deploiement RAG ANSTAT v2 (Pipeline OpenWebUI)

## Architecture

```
                    OpenWebUI (chat.anstat.ci)
                    │
        ┌───────────┼───────────────┐
        │           │               │
        ▼           ▼               ▼
   Qwen2.5      RAG Pipe       RAG Pipe
   (chat)      (recherche)    (generation)
                    │               │
                    ▼               ▼
             rag-search-service   qwen25-service
             (FAISS + reranker)   (vLLM GPU)
             port 8084            port 8000
```

Le Pipe OpenWebUI orchestre tout :
1. Appelle `rag-search-service` pour trouver les documents pertinents
2. Construit le prompt avec le contexte
3. Streame la reponse depuis Qwen2.5 directement dans l'interface

---

## Prerequis

- Cluster Kubernetes avec le namespace `vllm-chat` existant
- Qwen2.5 deja deploye (`qwen25-service:8000`)
- OpenWebUI deja deploye (`openwebui-service:8080`)
- Acces `kubectl` et `docker` depuis `srv-datalab`

---

## Etape 1 : Construire l'image Docker

### Depuis Windows (si Docker Desktop disponible)

```bash
cd C:\Users\f.migone\Desktop\projects\vLLM_Deploy\rag
docker build -t rag-search-anstat:latest .
```

### Depuis srv-datalab

```bash
# 1. Copier le dossier rag vers srv-datalab
scp -r C:\Users\f.migone\Desktop\projects\vLLM_Deploy\rag migone@srv-datalab:/tmp/rag

# 2. Sur srv-datalab, construire l'image
ssh migone@srv-datalab
cd /tmp/rag
docker build -t rag-search-anstat:latest .
```

> Le build telecharge PyTorch CPU (~800 Mo) + sentence-transformers + FAISS.
> Premiere fois : ~10 min. Rebuilds suivants : ~1 min (grace au cache Docker).

---

## Etape 2 : Deployer le service de recherche

```bash
kubectl apply -f /tmp/rag/k8s/rag-search-deployment.yaml
```

Verifier le demarrage :

```bash
# Suivre les logs (chargement modeles ~60s)
kubectl logs -f deployment/rag-search -n vllm-chat

# Attendre que le pod soit Ready
kubectl get pods -n vllm-chat -l app=rag-search -w
```

Vous devriez voir dans les logs :

```
============================================================
RAG SEARCH API - ANSTAT
============================================================
Loading FAISS index...
  FAISS: 9234 vecteurs, 384 dimensions
Loading chunk_map...
  9234 chunks charges
Loading embedding model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2...
  Modele charge: 384 dimensions
Loading reranker: cross-encoder/ms-marco-MiniLM-L-2-v2...
  Reranker charge (max_length=512)

Search API pret: 9234 chunks, 9234 vecteurs
============================================================
```

---

## Etape 3 : Tester le service de recherche

```bash
# Health check
curl http://<NODE_IP>:$(kubectl get svc rag-search-service -n vllm-chat -o jsonpath='{.spec.ports[0].nodePort}')/health

# Ou depuis un pod du cluster
kubectl exec -it deployment/openwebui -n vllm-chat -- \
  curl -s http://rag-search-service:8084/health | python3 -m json.tool
```

Resultat attendu :

```json
{
  "status": "ok",
  "chunks": 9234,
  "vectors": 9234,
  "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
  "reranker": "cross-encoder/ms-marco-MiniLM-L-2-v2"
}
```

Test de recherche :

```bash
kubectl exec -it deployment/openwebui -n vllm-chat -- \
  curl -s -X POST http://rag-search-service:8084/search \
  -H "Content-Type: application/json" \
  -d '{"query": "taux de pauvrete en Cote d Ivoire"}' | python3 -m json.tool
```

---

## Etape 4 : Installer le Pipe dans OpenWebUI

1. Ouvrir https://chat.anstat.ci
2. Se connecter en tant qu'**administrateur**
3. Aller dans **Admin Panel** (icone engrenage en bas a gauche)
4. Cliquer sur **Functions** dans le menu
5. Cliquer sur **"+"** (Create a new function)
6. Remplir :
   - **Name** : `RAG ANSTAT`
   - **Description** : `Recherche documentaire ANSTAT`
7. Coller le contenu du fichier `rag/pipe/openwebui_pipe.py` dans l'editeur
8. Cliquer **Save**

### Configurer les Valves

Apres avoir sauvegarde la fonction :

1. Cliquer sur l'icone **engrenage** a cote de la fonction
2. Configurer les valeurs :

| Parametre | Valeur |
|-----------|--------|
| RAG_SEARCH_URL | `http://rag-search-service:8084/search` |
| LLM_API_URL | `http://qwen25-service:8000/v1` |
| LLM_MODEL | `Qwen/Qwen2.5-7B-Instruct-AWQ` |
| LLM_MAX_TOKENS | `800` |
| LLM_TEMPERATURE | `0.05` |
| MIN_RELEVANCE_SCORE | `0.35` |
| REQUEST_TIMEOUT | `60` |

3. Cliquer **Save**

### Activer le Pipe

1. Verifier que le toggle a cote de la fonction est **active** (vert)
2. Retourner sur la page de chat
3. Le modele **"RAG ANSTAT"** doit apparaitre dans la liste des modeles

---

## Etape 5 : Tester le RAG dans OpenWebUI

1. Creer un nouveau chat
2. Selectionner le modele **"RAG ANSTAT"**
3. Poser une question, par exemple :
   - "Quel est le taux de pauvrete en Cote d'Ivoire ?"
   - "Quels sont les resultats de l'enquete EHCVM 2021 ?"
   - "Quelle est la prevalence de la malnutrition chez les enfants ?"
4. La reponse doit :
   - Arriver en **streaming** (tokens visibles un par un)
   - Contenir des **sources** a la fin (document, page, score)
   - Refuser de repondre si aucune source pertinente

---

## Etape 6 (optionnel) : Supprimer l'ancien service RAG

Si l'ancien `rag-api` (celui qui faisait search + LLM) est encore deploye :

```bash
kubectl delete deployment rag-api -n vllm-chat
kubectl delete service rag-api-service -n vllm-chat
```

---

## Etape 7 (optionnel) : Mettre a jour OpenWebUI

Si OpenWebUI pointait encore vers l'ancien RAG comme "modele", retirer la reference :

Dans `k8s/openwebui-deployment.yaml`, changer :

```yaml
# AVANT
- name: OPENAI_API_BASE_URLS
  value: "http://qwen25-service:8000/v1;http://rag-api-service:8084/v1"
- name: MODEL_FILTER_LIST
  value: "Qwen/Qwen2.5-7B-Instruct-AWQ;rag-anstat"

# APRES (le RAG est gere par le Pipe, plus besoin de l'API comme "modele")
- name: OPENAI_API_BASE_URLS
  value: "http://qwen25-service:8000/v1"
- name: MODEL_FILTER_LIST
  value: "Qwen/Qwen2.5-7B-Instruct-AWQ"
```

Puis appliquer :

```bash
kubectl apply -f k8s/openwebui-deployment.yaml
kubectl rollout restart deployment/openwebui -n vllm-chat
```

---

## Depannage

### Le modele "RAG ANSTAT" n'apparait pas

- Verifier que la fonction est **activee** (toggle vert) dans Admin > Functions
- Verifier qu'il n'y a pas d'erreur de syntaxe dans le code du Pipe
- Rafraichir la page (Ctrl+F5)

### "Le service de recherche est indisponible"

```bash
# Verifier que le pod tourne
kubectl get pods -n vllm-chat -l app=rag-search

# Verifier les logs
kubectl logs -f deployment/rag-search -n vllm-chat

# Tester la connectivite depuis OpenWebUI
kubectl exec -it deployment/openwebui -n vllm-chat -- \
  curl -s http://rag-search-service:8084/health
```

### La reponse ne streame pas (attente longue)

- Verifier que Qwen2.5 repond :

```bash
kubectl exec -it deployment/openwebui -n vllm-chat -- \
  curl -s http://qwen25-service:8000/v1/models
```

- Verifier les logs du Pipe dans la console OpenWebUI (F12 > Console)

### Erreur "Connection refused" dans les Valves

Les URLs doivent utiliser les noms de **services Kubernetes** internes :
- `http://rag-search-service:8084/search` (pas localhost, pas IP)
- `http://qwen25-service:8000/v1` (pas localhost, pas IP)

---

## Resume des composants

| Composant | Image | Port | Role |
|-----------|-------|------|------|
| OpenWebUI | `openwebui-anstat:latest` | 8080 | Interface + Pipe RAG |
| Qwen2.5 | `vllm/vllm-openai:v0.10.0` | 8000 | LLM (GPU) |
| RAG Search | `rag-search-anstat:latest` | 8084 | Recherche FAISS + reranking (CPU) |

```bash
# Verifier tout
kubectl get pods -n vllm-chat
kubectl get svc -n vllm-chat
```

---

## Mise a jour des documents RAG

Pour ajouter de nouveaux documents :

1. Preparer les chunks (utiliser `rag/scripts/anstat_preparation_fast.py`)
2. Regenerer les embeddings (utiliser `rag/scripts/anstat_embedding_and_faiss.py`)
3. Les fichiers generes vont dans `rag/data/embeddings/` :
   - `faiss_index.bin`
   - `chunk_map.json`
   - `embeddings.npz`
   - `metadata.json`
4. Rebuild l'image Docker :

```bash
docker build -t rag-search-anstat:latest .
```

5. Redemarrer le pod :

```bash
kubectl rollout restart deployment/rag-search -n vllm-chat
```

---

## Limites connues et recommandations d'usage

### Limites du modele LLM (Qwen2.5-7B)

- **Extraction de donnees** : Le modele peut parfois ne pas detecter un chiffre present dans les extraits, notamment quand le texte est dense (tableaux, listes d'indicateurs). Il est recommande de reformuler la question de maniere plus precise si la reponse semble incomplete.
- **Contextualisation** : Le modele peut mal interpreter le contexte d'un chiffre (ex : confondre un taux annuel avec un taux trimestriel). Toujours verifier avec le document source cite.
- **Hallucinations** : Bien que le systeme soit concu pour limiter les reponses inventees, le modele peut dans de rares cas produire des informations non presentes dans les extraits. Les sources en fin de reponse permettent de verifier.
- **Concurrence** : Avec un seul GPU (NVIDIA T4), les temps de reponse augmentent si plusieurs utilisateurs interrogent le systeme simultanement.

### Recommandations pour les utilisateurs

1. **Outil d'aide, pas source de verite** : Les reponses du RAG ANSTAT sont generees par une intelligence artificielle. Elles doivent etre considerees comme un point de depart pour la recherche, pas comme une reference definitive.
2. **Toujours verifier les sources** : Chaque reponse cite le document et la page. Il est recommande de consulter le document original pour confirmer les chiffres.
3. **Questions precises = meilleures reponses** : Preferer "Quel est le taux de pauvrete en milieu rural en 2021 ?" a "Parle-moi de la pauvrete".
4. **Documents couverts** : Le systeme contient uniquement les publications indexees (enquetes EHCVM, EDS, ENV, RGPH, etc.). Il ne peut pas repondre sur des sujets non couverts par ces documents.

### Recommandations pour les administrateurs

1. **Surveiller les pods** : Verifier regulierement que les 3 pods (openwebui, qwen25, rag-search) sont en etat Running.
2. **Logs** : En cas de reponses anormales, consulter les logs du Pipe (F12 > Console dans le navigateur) et du service de recherche (`kubectl logs deployment/rag-search -n vllm-chat`).
3. **Mises a jour des documents** : Prevoir un processus regulier d'ajout de nouvelles publications dans l'index RAG (voir section precedente).
4. **Evolution hardware** : Un GPU plus puissant (ex : A100) ou un modele plus grand (Qwen2.5-14B, 72B) ameliorerait significativement la qualite des reponses.
