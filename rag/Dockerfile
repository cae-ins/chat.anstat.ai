FROM python:3.12-slim

LABEL maintainer="Projet RAG ANSTAT"
LABEL description="Service de recherche RAG pour documents ANSTAT"

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# PyTorch CPU en premier (layer cache Docker)
RUN pip install --no-cache-dir --default-timeout=1000 \
    torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

# Pre-telecharger les modeles dans l'image (pas de download au runtime)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-2-v2')"

# API et donnees
COPY src/rag_api.py ./src/
COPY data/embeddings/ ./data/embeddings/

EXPOSE 8084

CMD ["python", "src/rag_api.py"]
