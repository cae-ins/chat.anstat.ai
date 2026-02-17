# Dockerfile pour le fine-tuning LoRA de Phi-3.5-mini
# ANSTAT AI - Méthodologies statistiques

FROM nvidia/cuda:12.1-devel-ubuntu22.04

# Variables d'environnement
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="${CUDA_HOME}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}"

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-venv \
    git \
    wget \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Mise à jour de pip
RUN python3 -m pip install --upgrade pip setuptools wheel

# Installation de PyTorch avec CUDA
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Installation des dépendances de fine-tuning
RUN pip3 install \
    transformers>=4.40.0 \
    datasets>=2.18.0 \
    accelerate>=0.28.0 \
    peft>=0.10.0 \
    bitsandbytes>=0.43.0 \
    scipy \
    sentencepiece \
    protobuf \
    einops \
    flash-attn --no-build-isolation \
    wandb \
    tensorboard \
    trl>=0.8.0 \
    huggingface_hub

# Installation de vLLM pour l'inférence après fine-tuning
RUN pip3 install vllm>=0.4.0

# Création du répertoire de travail
WORKDIR /workspace

# Copie des fichiers de fine-tuning
COPY train_lora.py /workspace/
COPY merge_lora.py /workspace/
COPY config/ /workspace/config/
COPY data/ /workspace/data/

# Création des répertoires de sortie
RUN mkdir -p /workspace/output /workspace/logs /workspace/models

# Point d'entrée par défaut
ENTRYPOINT ["python3"]
CMD ["train_lora.py", "--help"]
