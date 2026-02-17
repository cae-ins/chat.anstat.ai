# Copier le modèle Qwen2.5-7B-Instruct-AWQ vers le cluster

Le modèle est déjà téléchargé dans : `C:\Users\f.migone\Qwen2.5-7B-Instruct-AWQ` (5.58 Go)

---

## Étape 1 : Copier vers srv-datalab (depuis Windows)

```bash
scp -r C:\Users\f.migone\Qwen2.5-7B-Instruct-AWQ migone@srv-datalab:/tmp/
```

---

## Étape 2 : Sur srv-datalab, copier dans le pod

```bash
# Supprimer le cache partiel existant
kubectl exec deployment/qwen25 -n vllm-chat -- rm -rf /root/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct-AWQ

# Créer le dossier de destination
kubectl exec deployment/qwen25 -n vllm-chat -- mkdir -p /root/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct-AWQ/snapshots/main

# Récupérer le nom du pod
POD_NAME=$(kubectl get pod -n vllm-chat -l app=qwen25 -o jsonpath='{.items[0].metadata.name}')

# Copier les fichiers
kubectl cp /tmp/Qwen2.5-7B-Instruct-AWQ/. vllm-chat/$POD_NAME:/root/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct-AWQ/snapshots/main/
```

---

## Étape 3 : Redémarrer le pod

```bash
kubectl cp /tmp/Qwen2.5-7B-Instruct-AWQ/. vllm-chat/$POD_NAME:/root/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct-AWQ/snapshots/main/
```

---

## Étape 4 : Vérifier le démarrage

```bash
kubectl logs -f deployment/qwen25 -n vllm-chat
```

Vous devriez voir :
```
INFO [...] Model loading took ~4.XX GiB
INFO [...] Uvicorn running on http://0.0.0.0:8000
```

---

## Étape 5 : Tester le modèle

```bash
curl http://localhost:30179/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "Bonjour, qui es-tu ?"}],
    "max_tokens": 100
  }'
```

---

## Étape 6 : Basculer OpenWebUI et RAG (si test OK)

Voir le fichier `MIGRATION.md` pour les instructions complètes.

---

## Nettoyage (après validation)

```bash
# Sur srv-datalab
rm -rf /tmp/Qwen2.5-7B-Instruct-AWQ

# Sur Windows (optionnel)
rmdir /s C:\Users\f.migone\Qwen2.5-7B-Instruct-AWQ
```
