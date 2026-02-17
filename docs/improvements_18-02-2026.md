# Ameliorations RAG ANSTAT - 18/02/2026

## Etat actuel

- **Architecture** : OpenWebUI Pipe → rag-search-service (FAISS + reranker) → Qwen2.5-7B-AWQ (vLLM)
- **Embeddings** : `paraphrase-multilingual-MiniLM-L12-v2` (384 dims)
- **Reranker** : `cross-encoder/ms-marco-MiniLM-L-2-v2`
- **Index** : 9 234 chunks, 38+ documents statistiques
- **Hardware** : 1x NVIDIA T4 (16 Go VRAM), CPU pour la recherche

---

## Techniques avancees (recherche Apple)

### 1. CLaRa (Continuous Latent Reasoning for RAG)

**Principe** : Au lieu d'envoyer du texte brut dans le prompt, les documents sont encodes en representations latentes continues. Le LLM raisonne directement sur ces representations, sans avoir besoin de lire le texte mot par mot.

**Avantages** :
- Reduit enormement la taille du contexte envoye au LLM
- Le modele comprend mieux les relations entre documents
- Meilleure extraction d'information dans les textes denses (tableaux, chiffres)

**Faisabilite pour ANSTAT** : **POSSIBLE**
- Necessite un fine-tuning de Qwen2.5 pour qu'il comprenne les representations latentes
- L'infrastructure de fine-tuning existe deja (dossier `finetuning/`)
- Le T4 peut supporter un fine-tuning avec LoRA/QLoRA sur un 7B
- Etapes :
  1. Preparer un dataset de paires (question, documents, reponse attendue)
  2. Encoder les documents avec le modele d'embedding existant
  3. Fine-tuner Qwen2.5 avec LoRA pour qu'il prenne en entree les embeddings latents
  4. Adapter le Pipe pour envoyer les representations au lieu du texte
- **Effort estime** : Significatif mais faisable, necessite de la recherche sur l'implementation exacte du papier

### 2. Superposition Prompting

**Principe** : Chaque document est traite dans un chemin de prompt parallele independant. Le modele evalue chaque document separement puis fusionne les resultats, au lieu de tout concatener dans un seul prompt.

**Avantages** :
- Elimine le probleme du "lost in the middle" (le LLM ignore les documents au milieu d'un long contexte)
- Meilleure precision sur chaque source individuelle

**Faisabilite pour ANSTAT** : **DIFFICILE**
- Necessite des modifications a l'architecture du transformer
- Pas implementable via un Pipe ou une API standard
- Necessite un modele specifiquement modifie

### 3. Context Tuning (Long Context)

**Principe** : Utiliser un LLM a tres long contexte (128K+ tokens) pour ingerer beaucoup plus de documents d'un coup. Le modele fait le tri lui-meme (in-context retrieval).

**Avantages** :
- Simplifie le pipeline (moins besoin de FAISS + reranker)
- Le modele a acces a plus d'information

**Faisabilite pour ANSTAT** : **PAS POSSIBLE ACTUELLEMENT**
- Necessite beaucoup plus de VRAM (A100 80 Go minimum)
- Qwen2.5-7B-AWQ est limite a ~8K tokens sur T4
- Envisageable si upgrade GPU vers A100 ou H100

---

## Techniques intermediaires (implementables maintenant)

### 1. HyDE (Hypothetical Document Embeddings) - PRIORITE HAUTE

**Principe** : Avant de chercher dans FAISS, demander au LLM de generer une "reponse hypothetique" a la question. Utiliser cette reponse comme query de recherche au lieu de la question brute.

**Pourquoi** : Une reponse hypothetique ressemble beaucoup plus aux documents stockes qu'une simple question. La correspondance semantique dans FAISS est donc bien meilleure.

**Exemple** :
- Question utilisateur : "Quel est le taux de pauvrete ?"
- Reponse hypothetique generee : "Le taux de pauvrete en Cote d'Ivoire est de 39,4% selon l'enquete EHCVM 2021..."
- Cette reponse hypothetique est utilisee comme query FAISS → meilleurs resultats

**Implementation** :
1. Dans le Pipe, avant d'appeler `/search`, faire un appel rapide au LLM (non-streaming, max 100 tokens)
2. Utiliser la reponse generee comme query pour le service de recherche
3. Continuer le pipeline normal avec les meilleurs resultats

**Impact** : Fort, surtout pour les questions vagues ou generales
**Effort** : Faible (quelques lignes dans le Pipe)
**Cout** : Un appel LLM supplementaire (~0.5s sur T4)

### 2. Hybrid Search (BM25 + FAISS) - PRIORITE HAUTE

**Principe** : Combiner la recherche vectorielle (semantique, FAISS) avec une recherche par mots-cles classique (BM25). Les deux listes de resultats sont fusionnees avec un score combine.

**Pourquoi** : Les embeddings capturent le sens general mais peuvent rater des termes techniques precis, des acronymes (EHCVM, ENV, RGPH) ou des chiffres. BM25 excelle pour la correspondance exacte de mots-cles.

**Implementation** :
1. Ajouter `rank-bm25` dans les dependances
2. Construire un index BM25 au demarrage (a partir des memes chunks)
3. Pour chaque query : chercher dans FAISS ET dans BM25
4. Fusionner les resultats avec Reciprocal Rank Fusion (RRF)
5. Puis passer au reranker comme d'habitude

**Impact** : Fort, surtout pour les termes techniques et les chiffres
**Effort** : Moyen (modifier `rag_api.py`, ajouter ~50 lignes)

### 3. Query Expansion - PRIORITE MOYENNE

**Principe** : Generer 2-3 reformulations de la question, chercher pour chacune dans FAISS, puis fusionner et dedupliquer les resultats.

**Exemple** :
- Question : "chomage en Cote d'Ivoire"
- Expansion 1 : "taux de chomage population active Cote d'Ivoire"
- Expansion 2 : "emploi inactivite marche du travail ivoirien"

**Implementation** :
1. Appel LLM rapide pour generer 2 variantes de la question
2. 3 recherches FAISS (question originale + 2 variantes)
3. Fusion des resultats, deduplication, reranking

**Impact** : Moyen, aide surtout quand le vocabulaire utilisateur ≠ vocabulaire documents
**Effort** : Faible (quelques lignes dans le Pipe)
**Cout** : Un appel LLM + 2 recherches FAISS supplementaires

### 4. Contextual Chunking (chunks chevauchants) - PRIORITE MOYENNE

**Principe** : Au lieu de decouper les documents en chunks non chevauchants, utiliser un chevauchement de 20-30% entre chunks consecutifs. Cela evite de couper une information en deux.

**Implementation** :
1. Modifier le script de preparation des chunks (`anstat_preparation_fast.py`)
2. Ajouter un parametre `overlap` (ex: 200 caracteres de chevauchement)
3. Regenerer les embeddings et l'index FAISS
4. Rebuild l'image Docker

**Impact** : Moyen, reduit les cas ou un chiffre est dans un chunk et son contexte dans le suivant
**Effort** : Faible (modifier le script de chunking)
**Inconvenient** : Augmente le nombre de chunks (~30% de plus)

---

## Plan d'implementation recommande

### Phase 1 (rapide, sans rebuild Docker)
1. **HyDE** dans le Pipe OpenWebUI
2. **Query Expansion** dans le Pipe OpenWebUI

### Phase 2 (necessite rebuild Docker)
3. **Hybrid Search BM25** dans `rag_api.py`
4. **Contextual Chunking** dans les scripts de preparation

### Phase 3 (recherche + fine-tuning)
5. **CLaRa** - etude du papier Apple, preparation du dataset, fine-tuning LoRA

---

## Ressources

- CLaRa paper : rechercher "Apple CLaRa Continuous Latent Reasoning RAG"
- HyDE paper : "Precise Zero-Shot Dense Retrieval without Relevance Labels" (Gao et al., 2022)
- Rank-BM25 : `pip install rank-bm25`
- LoRA/QLoRA fine-tuning : compatible T4 avec `peft` + `bitsandbytes`
