# Prochaines étapes - 19/02/2026

## Ce qui tourne en ce moment
- **Extraction Graph RAG** sur la machine secondaire (Ollama gpt-oss:20b)
  - Script : `rag/scripts/graph_extractor.py`
  - Résultat attendu : `rag/data/graph/graph_data.json`
  - Durée estimée : 10-15h

---

## À faire demain

### 1. Récupérer les résultats de l'extraction
- Copier `rag/data/graph/graph_data.json` depuis la machine secondaire
- Le placer dans `rag/data/graph/` sur la machine principale

### 2. Déployer Neo4j sur le serveur
```bash
scp -r k8s/ migone@192.168.1.230:/home/migone/vLLM_Deploy/
ssh migone@192.168.1.230
kubectl apply -f /home/migone/vLLM_Deploy/k8s/neo4j-pvc.yaml
kubectl apply -f /home/migone/vLLM_Deploy/k8s/neo4j-deployment.yaml
kubectl get pods -n vllm-chat | grep neo4j
```
- Navigateur Neo4j : `http://192.168.1.230:30474`
- Credentials : `neo4j / anstat2024`

### 3. Écrire le schéma Cypher + script d'import
- Définir les contraintes et index Neo4j
- Script `rag/scripts/graph_import.py` : lit `graph_data.json` → peuple Neo4j
- Nœuds : Domaine, Indicateur, Periodicite, Couverture, Document
- Relations : APPARTIENT_A, MESURE_A, COUVRE, ISSU_DE

### 4. Écrire `graph_api.py`
- FastAPI sur port 8085
- Endpoint `/graph-search` : requête Cypher depuis une question
- Même format de réponse que `rag_api.py` pour faciliter l'intégration

### 5. Écrire `openwebui_pipe_hybrid.py`
- Appels parallèles FAISS + Neo4j (ThreadPoolExecutor)
- Fusion des résultats
- Prompt unifié → Qwen2.5 streaming

### 6. Déployer le pipe hybride
- Docker build du graph_api
- kubectl apply
- Ajouter le pipe dans OpenWebUI

---

## Déjà fait aujourd'hui (18/02)
- Fix bug conversationnel (classifieur LLM)
- Fix streaming lent (with requests.post)
- Fix repetition_penalty: 1.15
- Pipe HyDE créé (`openwebui_pipe_hyde.py`)
- Logo A.png déployé (favicon)
- Build script k8s chemins corrigés
- Script graph_extractor.py créé et lancé
- YAML Neo4j prêts (`k8s/neo4j-deployment.yaml`, `k8s/neo4j-pvc.yaml`)
