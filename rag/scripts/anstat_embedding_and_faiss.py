# =========================================================
# prepare_embeddings_optimized.py
# Version optimisée pour documents institutionnels
# =========================================================

import json
import unicodedata
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss

# -----------------------
# CONFIGURATION
# -----------------------
CHUNKS_DIR = Path("./chunks_output_fast")  # Tes chunks ultra rapides
OUTPUT_DIR = Path("./embeddings_optimized")
EMBEDDING_MODEL_NAME = "dangvantuan/sentence-camembert-base"  # MEILLEUR pour français
# Ou: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
FAISS_INDEX_FILE = OUTPUT_DIR / "faiss_index.bin"
CHUNK_MAP_FILE = OUTPUT_DIR / "chunk_map.json"
METADATA_FILE = OUTPUT_DIR / "metadata.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------
# FONCTIONS AMÉLIORÉES
# -----------------------

def clean_text_enhanced(text: str) -> str:
    """Nettoyage robuste pour documents institutionnels"""
    if not text or not isinstance(text, str):
        return ""
    
    # Normalisation Unicode
    text = unicodedata.normalize("NFKC", text)
    
    # Remplacement des caractères problématiques
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    
    # Suppression des espaces multiples
    text = " ".join(text.split())
    
    # Suppression des URL et emails (parfois dans les PDF)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\S+@\S+', '', text)
    
    # Suppression des numéros de page isolés
    text = re.sub(r'\b\d{1,3}\s*/\s*\d{1,3}\b', '', text)
    
    return text.strip()

def load_and_filter_chunks(chunks_dir: Path) -> List[Dict[str, Any]]:
    """Charge et filtre intelligemment les chunks"""
    all_chunks = []
    json_files = list(chunks_dir.glob("*_chunks.json"))
    
    print(f"📁 Fichiers trouvés: {len(json_files)}")
    
    for file_path in tqdm(json_files, desc="Chargement des chunks"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Gestion des deux formats possibles
            if isinstance(data, dict):
                # Format: {"chunks": [...], "metadata": {...}}
                chunks_list = data.get("chunks", [])
                doc_metadata = data.get("metadata", {})
            else:
                # Format: liste directe
                chunks_list = data
                doc_metadata = {"document_name": file_path.stem}
            
            for chunk in chunks_list:
                # Vérifier la structure
                if not isinstance(chunk, dict):
                    continue
                
                # Extraire le texte (support multiple formats)
                text = ""
                if "content" in chunk:
                    text = chunk["content"]
                elif "text" in chunk:
                    text = chunk["text"]
                else:
                    continue
                
                # Nettoyer
                cleaned_text = clean_text_enhanced(text)
                
                # FILTRES DE QUALITÉ
                # 1. Longueur minimale
                if len(cleaned_text) < 100:
                    continue
                
                # 2. Longueur maximale
                if len(cleaned_text) > 3000:
                    cleaned_text = cleaned_text[:3000] + "..."
                
                # 3. Vérifier que c'est du vrai texte
                if cleaned_text.isnumeric() or len(set(cleaned_text)) < 10:
                    continue
                
                # 4. Ratio de mots uniques (éviter les répétitions)
                words = cleaned_text.split()
                if len(words) < 15:
                    continue
                
                unique_ratio = len(set(words)) / len(words)
                if unique_ratio < 0.3:  # Trop répétitif
                    continue
                
                # Préparer les métadonnées
                metadata = chunk.get("metadata", {})
                if isinstance(metadata, dict):
                    # Enrichir avec les métadonnées du document
                    metadata.update({
                        "document_name": doc_metadata.get("document_name", file_path.stem),
                        "source_file": str(file_path.name),
                        "chunk_length": len(cleaned_text),
                        "word_count": len(words)
                    })
                else:
                    metadata = {
                        "document_name": doc_metadata.get("document_name", file_path.stem),
                        "source_file": str(file_path.name)
                    }
                
                # ID du chunk
                chunk_id = chunk.get("chunk_id")
                if not chunk_id:
                    import hashlib
                    chunk_id = hashlib.md5(cleaned_text.encode()).hexdigest()[:16]
                
                all_chunks.append({
                    "chunk_id": chunk_id,
                    "content": cleaned_text,
                    "metadata": metadata,
                    "original_text": text[:500]  # Garder un extrait original
                })
                
        except Exception as e:
            print(f"⚠️ Erreur avec {file_path.name}: {str(e)}")
    
    return all_chunks

def deduplicate_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Supprime les doublons sémantiques"""
    if len(chunks) <= 1:
        return chunks
    
    # Méthode simple: basée sur les débuts de texte
    seen_starts = set()
    unique_chunks = []
    
    for chunk in chunks:
        text = chunk["content"]
        if len(text) < 100:
            signature = text
        else:
            signature = text[:150]  # 150 premiers caractères
        
        if signature not in seen_starts:
            seen_starts.add(signature)
            unique_chunks.append(chunk)
        else:
            print(f"📝 Doublon détecté et supprimé: {chunk['chunk_id']}")
    
    return unique_chunks

def create_embeddings_batched(chunks: List[Dict[str, Any]], model_name: str, batch_size: int = 32) -> Tuple[np.ndarray, Dict[str, Dict[str, Any]]]:
    """Crée embeddings par batch pour gérer la mémoire"""
    print(f"🔧 Chargement du modèle: {model_name}")
    model = SentenceTransformer(model_name)
    
    # Préparer les textes
    texts = [chunk["content"] for chunk in chunks]
    
    print(f"⚡ Création des embeddings ({len(texts)} textes)...")
    
    # Encoder par batch
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True
    )
    
    # Créer le mapping
    chunk_map = {}
    for chunk in chunks:
        chunk_map[chunk["chunk_id"]] = {
            "document_id": chunk["metadata"].get("document_name", "unknown"),
            "page_number": chunk["metadata"].get("page_number", -1),
            "content": chunk["content"],
            "source_file": chunk["metadata"].get("source_file", ""),
            "word_count": chunk["metadata"].get("word_count", 0),
            "original_preview": chunk.get("original_text", "")[:200]
        }
    
    return embeddings.astype(np.float32), chunk_map

def build_optimized_faiss_index(embeddings: np.ndarray, use_gpu: bool = False):
    """Construit un index FAISS optimisé"""
    dim = embeddings.shape[1]
    
    # Pour meilleure qualité: Index FlatIP (cosine similarity)
    index = faiss.IndexFlatIP(dim)
    
    # Normaliser les embeddings (déjà fait par SentenceTransformer)
    index.add(embeddings)
    
    # Option: ajouter une couche de clustering pour vitesse
    if embeddings.shape[0] > 10000:
        print("🔧 Création d'index IVF pour meilleure performance...")
        nlist = min(100, embeddings.shape[0] // 100)
        quantizer = faiss.IndexFlatIP(dim)
        index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)
        index.train(embeddings)
        index.add(embeddings)
        index.nprobe = 10  # Compromis vitesse/précision
    
    return index

def save_all_data(embeddings: np.ndarray, chunk_map: Dict[str, Dict[str, Any]], index: faiss.IndexFlatIP, chunks: List[Dict[str, Any]]):
    """Sauvegarde complète"""
    # 1. Embeddings
    np.savez_compressed(OUTPUT_DIR / "embeddings.npz", embeddings=embeddings)
    
    # 2. Mapping chunks
    with open(CHUNK_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(chunk_map, f, ensure_ascii=False, indent=2)
    
    # 3. Index FAISS
    faiss.write_index(index, str(FAISS_INDEX_FILE))
    
    # 4. Métadonnées complètes
    metadata = {
        "total_chunks": len(chunks),
        "embedding_dim": embeddings.shape[1],
        "model_used": EMBEDDING_MODEL_NAME,
        "chunk_stats": {
            "avg_length": np.mean([len(c["content"]) for c in chunks]),
            "min_length": min([len(c["content"]) for c in chunks]),
            "max_length": max([len(c["content"]) for c in chunks]),
            "total_words": sum([c["metadata"].get("word_count", 0) for c in chunks])
        }
    }
    
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Données sauvegardées dans {OUTPUT_DIR}")

# -----------------------
# PIPELINE PRINCIPAL
# -----------------------

def main():
    print("\n" + "="*60)
    print("PIPELINE EMBEDDINGS OPTIMISÉ - Documents Institutionnels")
    print("="*60 + "\n")
    
    # 1. Chargement et filtrage
    print("📂 Étape 1: Chargement et filtrage des chunks...")
    chunks = load_and_filter_chunks(CHUNKS_DIR)
    
    if not chunks:
        print("❌ Aucun chunk valide trouvé!")
        return
    
    print(f"✅ {len(chunks)} chunks chargés")
    
    # 2. Déduplication
    print("\n🧹 Étape 2: Déduplication...")
    chunks = deduplicate_chunks(chunks)
    print(f"✅ {len(chunks)} chunks uniques après déduplication")
    
    # 3. Création des embeddings
    print("\n⚡ Étape 3: Création des embeddings...")
    embeddings, chunk_map = create_embeddings_batched(chunks, EMBEDDING_MODEL_NAME)
    print(f"✅ Embeddings créés: {embeddings.shape}")
    
    # 4. Construction de l'index
    print("\n🔗 Étape 4: Construction de l'index FAISS...")
    index = build_optimized_faiss_index(embeddings)
    print(f"✅ Index FAISS créé avec {index.ntotal} vecteurs")
    
    # 5. Sauvegarde
    print("\n💾 Étape 5: Sauvegarde...")
    save_all_data(embeddings, chunk_map, index, chunks)
    
    # 6. Statistiques
    print("\n📊 STATISTIQUES FINALES:")
    print(f"   • Chunks: {len(chunks)}")
    print(f"   • Dimensions: {embeddings.shape[1]}")
    print(f"   • Taille index: {index.ntotal} vecteurs")
    
    # Vérifier la qualité
    print("\n🧪 Test de vérification...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    test_queries = [
        "pauvreté en Côte d'Ivoire",
        "statistiques démographiques",
        "enquête EHCVM"
    ]
    
    for query_text in test_queries:
        q_emb = model.encode([query_text], normalize_embeddings=True)
        scores, indices = index.search(q_emb, 1)
        
        if indices[0][0] >= 0:
            chunk_id = list(chunk_map.keys())[indices[0][0]]
            chunk_data = chunk_map[chunk_id]
            print(f"\n🔍 Query: '{query_text}'")
            print(f"   📄 Document: {chunk_data['document_id']}")
            print(f"   📄 Contenu: {chunk_data['content'][:100]}...")
            print(f"   ⭐ Score: {scores[0][0]:.3f}")
    
    print("\n" + "="*60)
    print("✅ PIPELINE TERMINÉ AVEC SUCCÈS!")
    print("="*60)
    print(f"\n📁 Résultats dans: {OUTPUT_DIR}")
    print(f"📄 Fichiers créés:")
    print(f"   • faiss_index.bin (index de recherche)")
    print(f"   • chunk_map.json (mapping chunk -> metadata)")
    print(f"   • embeddings.npz (vecteurs)")
    print(f"   • metadata.json (statistiques)")
    print(f"\n🚀 Prêt pour la recherche RAG!")

if __name__ == "__main__":
    main()