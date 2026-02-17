# Fine-tuning LoRA de Phi-3.5-mini pour ANSTAT AI

Ce dossier contient tout le nécessaire pour fine-tuner le modèle Phi-3.5-mini avec les méthodologies statistiques de l'ANSTAT.

## Structure du dossier

```
finetuning/
├── train_lora.py               # Script principal de fine-tuning
├── merge_lora.py               # Script de fusion LoRA + modèle base
├── parse_methodologies.py      # Script de parsing des documents
├── Dockerfile                  # Image Docker pour le fine-tuning
├── requirements.txt            # Dépendances Python
├── config/
│   └── training_config.yaml    # Configuration des hyperparamètres
├── data/
│   └── methodologies_anstat.jsonl  # Données d'entraînement
├── methodologies_sources/      # ⬅️ PLACEZ VOS DOCUMENTS ICI
│   └── .gitkeep
└── k8s/
    ├── finetuning-job.yaml         # Job Kubernetes pour fine-tuning
    └── phi3-anstat-deployment.yaml # Déploiement du modèle fine-tuné
```

## Prérequis

- GPU NVIDIA avec au moins 16 Go VRAM (T4, A100, etc.)
- CUDA 12.1+
- Python 3.10+
- Token HuggingFace (pour télécharger Phi-3.5)

## Installation locale

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Installer PyTorch avec CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Installer les dépendances
pip install -r requirements.txt

# Installer flash-attention (optionnel mais recommandé)
pip install flash-attn --no-build-isolation
```

## Parsing automatique des documents

Placez vos documents (PDF, DOCX, TXT, MD) dans `methodologies_sources/` puis lancez :

```bash
pip install pymupdf python-docx
python parse_methodologies.py
```

Le script extrait automatiquement les sections et génère des paires question/réponse.

📖 **Documentation complète : [parsing.md](parsing.md)**

---

## Préparation manuelle des données (optionnel)

### Format des données

Les données doivent être au format JSONL avec la structure suivante :

```json
{"instruction": "Question sur une méthodologie", "input": "", "output": "Réponse détaillée"}
```

### Exemple

```json
{"instruction": "Comment calcule-t-on l'IPC ?", "input": "", "output": "L'IPC est calculé selon la formule de Laspeyres..."}
```

### Enrichir les données

1. Ouvrir `data/methodologies_anstat.jsonl`
2. Ajouter vos propres exemples de méthodologies
3. Recommandation : minimum 50-100 exemples pour de bons résultats

## Lancer le fine-tuning

### Option 1 : En local (GPU requis)

```bash
# Fine-tuning basique
python train_lora.py \
    --data_path ./data/methodologies_anstat.jsonl \
    --output_dir ./output/phi3-anstat-lora \
    --num_epochs 3 \
    --batch_size 4

# Fine-tuning avec QLoRA (pour GPU 16 Go comme T4)
python train_lora.py \
    --data_path ./data/methodologies_anstat.jsonl \
    --output_dir ./output/phi3-anstat-lora \
    --num_epochs 3 \
    --batch_size 2 \
    --use_4bit \
    --gradient_checkpointing
```

### Option 2 : Sur Kubernetes

```bash
# Construire l'image Docker
docker build -t anstat/phi3-finetuning:latest .

# Pousser vers votre registry
docker push anstat/phi3-finetuning:latest

# Copier les données vers le PVC
kubectl cp ./data/methodologies_anstat.jsonl vllm-chat/pod-name:/data/

# Lancer le job de fine-tuning
kubectl apply -f k8s/finetuning-job.yaml -n vllm-chat

# Suivre les logs
kubectl logs -f job/phi3-finetuning-lora -n vllm-chat
```

## Fusion des poids LoRA

Après le fine-tuning, fusionner les adaptateurs LoRA avec le modèle de base :

```bash
python merge_lora.py \
    --lora_path ./output/phi3-anstat-lora \
    --output_path ./output/phi3-anstat-merged
```

## Déploiement du modèle fine-tuné

### Sur Kubernetes

```bash
# Copier le modèle fusionné vers le PVC
kubectl cp ./output/phi3-anstat-merged vllm-chat/pod-name:/models/

# Déployer
kubectl apply -f k8s/phi3-anstat-deployment.yaml -n vllm-chat
```

### Mise à jour d'OpenWebUI

Configurer OpenWebUI pour pointer vers le nouveau service :
- URL : `http://phi3-anstat-service:8000/v1`
- Nom du modèle : `phi3-anstat`

## Configurations par GPU

### NVIDIA T4 (16 Go VRAM)

```bash
python train_lora.py \
    --use_4bit \
    --batch_size 2 \
    --gradient_accumulation_steps 8 \
    --lora_r 8 \
    --gradient_checkpointing
```

### NVIDIA A100 40GB

```bash
python train_lora.py \
    --batch_size 8 \
    --gradient_accumulation_steps 2 \
    --lora_r 32 \
    --lora_alpha 64
```

### NVIDIA A100 80GB / 4x A100

```bash
python train_lora.py \
    --batch_size 16 \
    --lora_r 64 \
    --lora_alpha 128
```

## Hyperparamètres recommandés

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `lora_r` | 16 | Rang de la décomposition LoRA |
| `lora_alpha` | 32 | Facteur de scaling (2x le rang) |
| `lora_dropout` | 0.05 | Dropout pour régularisation |
| `learning_rate` | 2e-4 | Taux d'apprentissage |
| `num_epochs` | 3 | Nombre d'époques |
| `batch_size` | 4 | Taille du batch (ajuster selon GPU) |

## Vérification du modèle

Après fusion, tester le modèle :

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("./output/phi3-anstat-merged")
tokenizer = AutoTokenizer.from_pretrained("./output/phi3-anstat-merged")

prompt = "<|user|>\nComment calcule-t-on l'IPC à l'ANSTAT ?<|end|>\n<|assistant|>\n"
inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=200)
print(tokenizer.decode(outputs[0]))
```

## Troubleshooting

### Erreur CUDA Out of Memory

- Réduire `batch_size`
- Activer `--use_4bit` (QLoRA)
- Activer `--gradient_checkpointing`
- Réduire `lora_r`

### Modèle ne converge pas

- Augmenter `num_epochs`
- Ajuster `learning_rate` (essayer 1e-4 ou 5e-5)
- Vérifier la qualité des données

### Flash Attention non disponible

Le script fonctionne sans flash-attention mais sera plus lent. Pour l'installer :

```bash
pip install flash-attn --no-build-isolation
```

## Ressources

- [Documentation PEFT](https://huggingface.co/docs/peft)
- [Phi-3 sur HuggingFace](https://huggingface.co/microsoft/Phi-3.5-mini-instruct)
- [Guide LoRA](https://huggingface.co/docs/peft/conceptual_guides/lora)

## Support

Centre de Calcul CAE & DataLab ANSTAT
Email : cae@stat.plan.gouv.ci
