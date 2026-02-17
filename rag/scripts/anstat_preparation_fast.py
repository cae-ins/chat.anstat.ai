# ============================================================================
# PREPARATION_CHUNK_INSTITUTIONNEL_FAST.py
# PIPELINE RAG INSTITUTIONNEL OPTIMISÉ - VERSION RAPIDE
# Python 3.12
# ============================================================================

import os
import json
import time
import hashlib
import traceback
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
import multiprocessing

import fitz  # PyMuPDF
import pandas as pd
import numpy as np

# ============================================================================
# CONFIGURATION OPTIMISÉE
# ============================================================================

@dataclass
class PipelineConfigFast:
    """Configuration optimisée pour vitesse"""
    
    def __init__(
        self,
        documents_dir: Path,
        output_dir: Path,
        chunk_size: int = 1000,  # Augmenté pour réduire le nombre de chunks
        chunk_overlap: int = 200,
        min_chunk_size: int = 150,
        max_chunk_size: int = 1500,
        use_semantic_chunking: bool = False,  # DÉSACTIVÉ pour la vitesse
        use_spacy: bool = False,  # DÉSACTIVÉ par défaut
        max_workers: int = None,  # Auto-détection
        log_level: str = "INFO"
    ):
        self.documents_dir = documents_dir
        self.output_dir = output_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.use_semantic_chunking = use_semantic_chunking
        self.use_spacy = use_spacy
        self.max_workers = max_workers or max(1, multiprocessing.cpu_count() - 1)
        self.log_level = log_level
        
        # Créer les répertoires
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "logs").mkdir(exist_ok=True)

# ============================================================================
# PIPELINE OPTIMISÉ
# ============================================================================

class FastRAGPipeline:
    """Pipeline optimisé pour vitesse (sans spaCy par défaut)"""
    
    def __init__(self, config: PipelineConfigFast):
        self.config = config
        self.output_dir = config.output_dir
        
        # Expressions régulières optimisées
        self.sentence_endings = re.compile(r'[.!?]+[\s\n]+')
        self.paragraph_separator = re.compile(r'\n\s*\n')
        self.juridical_patterns = {
            'article': re.compile(r'^(Article|ART\.?)\s*\d+', re.IGNORECASE),
            'loi': re.compile(r'^(Loi|Décret|Arrêté)\s', re.IGNORECASE),
        }
        
        # Log file
        self.log_file = self.output_dir / "logs" / f"fast_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Stats globales
        self.total_pages = 0
        self.total_chunks = 0
        self.start_time = time.time()
    
    def log(self, message: str, level: str = "INFO"):
        """Journalisation rapide"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")
        
        if level == "ERROR" or self.config.log_level == "INFO":
            print(f"[{level}] {message}")
    
    # ------------------------------------------------------------------------
    # EXTRACTION RAPIDE
    # ------------------------------------------------------------------------
    
    def extract_text_fast(self, pdf_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Extraction rapide sans analyse structurelle lourde"""
        self.log(f"Extraction: {pdf_path.name}")
        
        try:
            doc = fitz.open(pdf_path)
            pages_data = []
            
            for page_num, page in enumerate(doc, start=1):
                # Extraction simple et rapide
                text = page.get_text("text").strip()
                
                if not text:
                    continue
                
                # Nettoyage rapide
                text = re.sub(r'\s+', ' ', text)  # Espaces multiples
                text = re.sub(r'\n{3,}', '\n\n', text)  # Sauts de ligne multiples
                
                pages_data.append({
                    "page_number": page_num,
                    "text": text,
                    "char_count": len(text),
                    "word_count": len(text.split())
                })
            
            doc.close()
            
            # Métadonnées basiques
            metadata = {
                "document_name": pdf_path.name,
                "document_path": str(pdf_path),
                "document_size": pdf_path.stat().st_size,
                "total_pages": len(pages_data),
                "extraction_date": datetime.now(timezone.utc).isoformat()
            }
            
            return pages_data, metadata
            
        except Exception as e:
            self.log(f"Erreur extraction {pdf_path.name}: {str(e)}", "ERROR")
            return [], {}
    
    # ------------------------------------------------------------------------
    # CHUNKING RAPIDE (SANS spaCy)
    # ------------------------------------------------------------------------
    
    def fast_chunking(self, pages_data: List[Dict[str, Any]], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunking rapide basé sur paragraphes et taille fixe"""
        all_chunks = []
        
        for page in pages_data:
            text = page["text"]
            page_num = page["page_number"]
            
            if not text or len(text) < self.config.min_chunk_size:
                # Page trop courte, chunk unique
                if text and len(text) > 50:
                    chunk = self._create_chunk_fast(
                        text=text,
                        page_num=page_num,
                        metadata=metadata,
                        chunk_index=0
                    )
                    if chunk:
                        all_chunks.append(chunk)
                continue
            
            # Méthode 1: D'abord par paragraphes
            paragraphs = [p.strip() for p in self.paragraph_separator.split(text) if p.strip()]
            
            if paragraphs:
                chunks_from_paragraphs = self._chunk_by_paragraphs(paragraphs, page_num, metadata)
                all_chunks.extend(chunks_from_paragraphs)
            else:
                # Méthode 2: Par taille fixe avec overlap intelligent
                chunks_from_fixed = self._chunk_by_fixed_size(text, page_num, metadata)
                all_chunks.extend(chunks_from_fixed)
        
        return all_chunks
    
    def _chunk_by_paragraphs(self, paragraphs: List[str], page_num: int, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunking basé sur paragraphes (plus naturel)"""
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            # Si le paragraphe seul est trop long, on le divise
            if para_length > self.config.max_chunk_size:
                # Diviser le paragraphe trop long
                sub_chunks = self._split_long_paragraph(para, page_num, metadata, chunk_index)
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
                current_chunk = []
                current_length = 0
                continue
            
            # Ajouter au chunk courant si possible
            if current_length + para_length <= self.config.chunk_size:
                current_chunk.append(para)
                current_length += para_length
            else:
                # Créer un chunk avec les paragraphes accumulés
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    if len(chunk_text) >= self.config.min_chunk_size:
                        chunk = self._create_chunk_fast(
                            text=chunk_text,
                            page_num=page_num,
                            metadata=metadata,
                            chunk_index=chunk_index
                        )
                        if chunk:
                            chunks.append(chunk)
                            chunk_index += 1
                
                # Pour l'overlap, garder le dernier paragraphe
                current_chunk = [para] if para_length <= self.config.chunk_overlap else []
                current_length = para_length
        
        # Dernier chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            if len(chunk_text) >= self.config.min_chunk_size:
                chunk = self._create_chunk_fast(
                    text=chunk_text,
                    page_num=page_num,
                    metadata=metadata,
                    chunk_index=chunk_index
                )
                if chunk:
                    chunks.append(chunk)
        
        return chunks
    
    def _chunk_by_fixed_size(self, text: str, page_num: int, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunking par taille fixe (fallback)"""
        chunks = []
        chunk_index = 0
        
        # Découpage par phrases approximatives
        sentences = self.sentence_endings.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            # Découpage brutal par caractères
            for i in range(0, len(text), self.config.chunk_size - self.config.chunk_overlap):
                chunk_text = text[i:i + self.config.chunk_size]
                if len(chunk_text) >= self.config.min_chunk_size:
                    chunk = self._create_chunk_fast(
                        text=chunk_text,
                        page_num=page_num,
                        metadata=metadata,
                        chunk_index=chunk_index
                    )
                    if chunk:
                        chunks.append(chunk)
                        chunk_index += 1
        else:
            # Découpage par phrases
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                sent_length = len(sentence)
                
                if current_length + sent_length <= self.config.chunk_size:
                    current_chunk.append(sentence)
                    current_length += sent_length
                else:
                    if current_chunk:
                        chunk_text = " ".join(current_chunk)
                        if len(chunk_text) >= self.config.min_chunk_size:
                            chunk = self._create_chunk_fast(
                                text=chunk_text,
                                page_num=page_num,
                                metadata=metadata,
                                chunk_index=chunk_index
                            )
                            if chunk:
                                chunks.append(chunk)
                                chunk_index += 1
                    
                    # Overlap: garder les 1-2 dernières phrases
                    overlap_text = []
                    overlap_length = 0
                    for prev_sent in reversed(current_chunk[-2:]):  # Max 2 phrases pour overlap
                        if overlap_length + len(prev_sent) <= self.config.chunk_overlap:
                            overlap_text.insert(0, prev_sent)
                            overlap_length += len(prev_sent)
                    
                    current_chunk = overlap_text + [sentence]
                    current_length = overlap_length + sent_length
            
            # Dernier chunk
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= self.config.min_chunk_size:
                    chunk = self._create_chunk_fast(
                        text=chunk_text,
                        page_num=page_num,
                        metadata=metadata,
                        chunk_index=chunk_index
                    )
                    if chunk:
                        chunks.append(chunk)
        
        return chunks
    
    def _split_long_paragraph(self, paragraph: str, page_num: int, metadata: Dict[str, Any], start_index: int) -> List[Dict[str, Any]]:
        """Diviser un paragraphe trop long"""
        chunks = []
        chunk_index = start_index
        
        # Chercher des points de coupure naturels
        sentences = self.sentence_endings.split(paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 1:
            # Pas de phrases, découpage brutal
            for i in range(0, len(paragraph), self.config.chunk_size - self.config.chunk_overlap):
                chunk_text = paragraph[i:i + self.config.chunk_size]
                if len(chunk_text) >= self.config.min_chunk_size:
                    chunk = self._create_chunk_fast(
                        text=chunk_text,
                        page_num=page_num,
                        metadata=metadata,
                        chunk_index=chunk_index
                    )
                    if chunk:
                        chunks.append(chunk)
                        chunk_index += 1
        else:
            # Utiliser les phrases
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                sent_length = len(sentence)
                
                if current_length + sent_length <= self.config.chunk_size:
                    current_chunk.append(sentence)
                    current_length += sent_length
                else:
                    if current_chunk:
                        chunk_text = " ".join(current_chunk)
                        chunk = self._create_chunk_fast(
                            text=chunk_text,
                            page_num=page_num,
                            metadata=metadata,
                            chunk_index=chunk_index
                        )
                        if chunk:
                            chunks.append(chunk)
                            chunk_index += 1
                    
                    current_chunk = [sentence]
                    current_length = sent_length
            
            # Dernier chunk
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                chunk = self._create_chunk_fast(
                    text=chunk_text,
                    page_num=page_num,
                    metadata=metadata,
                    chunk_index=chunk_index
                )
                if chunk:
                    chunks.append(chunk)
        
        return chunks
    
    def _create_chunk_fast(self, text: str, page_num: int, metadata: Dict[str, Any], chunk_index: int) -> Dict[str, Any]:
        """Création rapide d'un chunk"""
        try:
            if not text or len(text.strip()) < self.config.min_chunk_size:
                return None
            
            # ID unique simple
            chunk_id = hashlib.md5(
                f"{metadata['document_name']}_{page_num}_{chunk_index}".encode()
            ).hexdigest()
            
            # Métadonnées basiques
            word_count = len(text.split())
            char_count = len(text)
            
            # Détection simple de type
            content_type = "paragraphe"
            if len(text) < 200 and (text.isupper() or text.endswith(':')):
                content_type = "titre"
            elif any(pattern.search(text) for pattern in self.juridical_patterns.values()):
                content_type = "article"
            
            # Thèmes simples
            themes = []
            text_lower = text.lower()
            theme_keywords = {
                'statistique': ['statistique', 'donnée', 'pourcentage', 'enquête', 'échantillon'],
                'financier': ['budget', 'finance', 'coût', 'euro', 'dépense'],
                'social': ['pauvreté', 'social', 'ménage', 'revenu', 'population']
            }
            
            for theme, keywords in theme_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    themes.append(theme)
            
            chunk_data = {
                "chunk_id": chunk_id,
                "text": text,
                "metadata": {
                    "document_name": metadata["document_name"],
                    "document_path": metadata["document_path"],
                    "page_number": page_num,
                    "chunk_index": chunk_index,
                    "content_type": content_type,
                    "themes": themes[:2],
                    "word_count": word_count,
                    "char_count": char_count,
                    "sentence_count": text.count('.') + text.count('!') + text.count('?'),
                    "extraction_method": "fast_chunking",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
            return chunk_data
            
        except Exception as e:
            self.log(f"Erreur création chunk: {str(e)}", "WARNING")
            return None
    
    # ------------------------------------------------------------------------
    # VALIDATION RAPIDE
    # ------------------------------------------------------------------------
    
    def validate_chunks_fast(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validation rapide"""
        valid_chunks = []
        
        for chunk in chunks:
            if not chunk:
                continue
            
            text = chunk.get("text", "")
            
            # Critères simples
            if (len(text) >= self.config.min_chunk_size and 
                len(text) <= self.config.max_chunk_size and
                text.strip()):
                valid_chunks.append(chunk)
        
        return valid_chunks
    
    # ------------------------------------------------------------------------
    # TRAITEMENT PAR DOCUMENT
    # ------------------------------------------------------------------------
    
    def process_single_document(self, pdf_path: Path) -> Dict[str, Any]:
        """Traiter un seul document (fonction pour parallélisation)"""
        doc_start = time.time()
        result = {
            "file": pdf_path.name,
            "success": False,
            "chunks_count": 0,
            "processing_time": 0,
            "error": None
        }
        
        try:
            # 1. Extraction
            pages_data, metadata = self.extract_text_fast(pdf_path)
            
            if not pages_data:
                result["error"] = "Aucun texte extrait"
                return result
            
            # 2. Chunking
            chunks = self.fast_chunking(pages_data, metadata)
            
            # 3. Validation
            chunks = self.validate_chunks_fast(chunks)
            
            # 4. Sauvegarde
            if chunks:
                output_file = self.output_dir / f"{pdf_path.stem.replace(' ', '_')}_chunks.json"
                
                output_data = {
                    "metadata": metadata,
                    "chunks_count": len(chunks),
                    "processing_date": datetime.now(timezone.utc).isoformat(),
                    "chunks": chunks
                }
                
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            # 5. Mise à jour du résultat
            result.update({
                "success": True,
                "chunks_count": len(chunks),
                "processing_time": time.time() - doc_start,
                "pages_count": len(pages_data)
            })
            
            self.log(f"✓ {pdf_path.name}: {len(chunks)} chunks en {result['processing_time']:.1f}s")
            
        except Exception as e:
            result["error"] = str(e)
            self.log(f"✗ {pdf_path.name}: {str(e)}", "ERROR")
        
        return result
    
    # ------------------------------------------------------------------------
    # TRAITEMENT BATCH PARALLÈLE
    # ------------------------------------------------------------------------
    
    def process_all_documents_parallel(self) -> Dict[str, Any]:
        """Traiter tous les documents en parallèle"""
        self.log("=== DÉMARRAGE TRAITEMENT PARALLÈLE ===")
        
        # Trouver les PDFs
        pdf_files = list(self.config.documents_dir.glob("*.pdf"))
        if not pdf_files:
            pdf_files = list(self.config.documents_dir.glob("**/*.pdf"))
        
        total_files = len(pdf_files)
        self.log(f"📚 Documents à traiter: {total_files}")
        
        if total_files == 0:
            return {"error": "Aucun PDF trouvé"}
        
        # Traitement parallèle
        all_results = []
        start_time = time.time()
        
        # Utiliser ProcessPoolExecutor pour vrai parallélisme
        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Soumettre tous les jobs
            future_to_doc = {executor.submit(self.process_single_document, pdf): pdf for pdf in pdf_files}
            
            # Suivi de progression
            completed = 0
            for future in as_completed(future_to_doc):
                completed += 1
                result = future.result()
                all_results.append(result)
                
                # Afficher progression
                progress = (completed / total_files) * 100
                elapsed = time.time() - start_time
                eta = (elapsed / completed) * (total_files - completed) if completed > 0 else 0
                
                print(f"\r📊 Progression: {completed}/{total_files} ({progress:.1f}%) - "
                      f"Temps: {elapsed:.0f}s - ETA: {eta:.0f}s", end="", flush=True)
        
        print()  # Nouvelle ligne après la barre de progression
        
        # Analyse des résultats
        successful = [r for r in all_results if r["success"]]
        failed = [r for r in all_results if not r["success"]]
        
        total_chunks = sum(r["chunks_count"] for r in successful)
        total_time = time.time() - start_time
        
        # Rapport global
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_documents": total_files,
            "successful_documents": len(successful),
            "failed_documents": len(failed),
            "total_chunks_generated": total_chunks,
            "total_processing_time": total_time,
            "average_time_per_document": total_time / len(successful) if successful else 0,
            "documents_per_minute": (len(successful) / total_time) * 60 if total_time > 0 else 0,
            "chunks_per_minute": (total_chunks / total_time) * 60 if total_time > 0 else 0,
            "successful_files": [r["file"] for r in successful],
            "failed_files": [{"file": r["file"], "error": r["error"]} for r in failed]
        }
        
        # Sauvegarder le rapport
        report_file = self.output_dir / "fast_processing_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # Sauvegarder CSV de résumé
        if successful:
            summary_data = []
            for result in successful:
                summary_data.append({
                    "file": result["file"],
                    "chunks": result["chunks_count"],
                    "pages": result.get("pages_count", 0),
                    "processing_time": result["processing_time"]
                })
            
            df = pd.DataFrame(summary_data)
            csv_file = self.output_dir / "fast_processing_summary.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            report["summary_csv"] = str(csv_file)
        
        # Afficher le rapport
        self._print_summary(report)
        
        return report
    
    def _print_summary(self, report: Dict[str, Any]):
        """Afficher un résumé clair"""
        print("\n" + "="*60)
        print("RAPPORT DE TRAITEMENT RAPIDE")
        print("="*60)
        
        print(f"✅ Documents réussis: {report['successful_documents']}/{report['total_documents']}")
        print(f"📊 Total chunks générés: {report['total_chunks_generated']}")
        print(f"⏱️  Temps total: {report['total_processing_time']:.1f} secondes")
        print(f"🚀 Vitesse: {report['documents_per_minute']:.1f} documents/minute")
        print(f"📈 Chunks/minute: {report['chunks_per_minute']:.1f}")
        
        if report['failed_documents'] > 0:
            print(f"\n❌ Documents échoués: {report['failed_documents']}")
            for failed in report['failed_files'][:5]:  # Afficher seulement les 5 premiers
                print(f"   • {failed['file']}: {failed['error'][:50]}...")
        
        print(f"\n📁 Résultats dans: {self.output_dir}")
        print(f"   • Rapport: fast_processing_report.json")
        print(f"   • Résumé: fast_processing_summary.csv")
        print(f"   • Chunks: [nom]_chunks.json")
        print("="*60)

# ============================================================================
# EXECUTION PRINCIPALE OPTIMISÉE
# ============================================================================

def main_fast():
    """Version rapide - pour 40 documents en quelques minutes"""
    
    print("\n" + "="*60)
    print("PIPELINE RAG ULTRA-RAPIDE")
    print("Optimisé pour 40+ documents")
    print("="*60 + "\n")
    
    # Configuration ULTRA RAPIDE
    config = PipelineConfigFast(
        documents_dir=Path(r"C:\Users\KABA\rag_anstat\pro\documents"),
        output_dir=Path("./chunks_output_fast"),  # Nouveau dossier
        chunk_size=1200,           # Plus gros = moins de chunks = plus rapide
        chunk_overlap=200,
        min_chunk_size=200,        # Éviter les chunks trop petits
        max_chunk_size=2000,       # Limite haute
        use_semantic_chunking=False,  # DÉSACTIVÉ = 10x plus rapide
        use_spacy=False,           # DÉSACTIVÉ = 100x plus rapide
        max_workers=None,          # Auto-détection (utilise tous les cœurs)
        log_level="INFO"
    )
    
    # Vérifications
    if not config.documents_dir.exists():
        print(f"❌ Répertoire introuvable: {config.documents_dir}")
        return
    
    pdf_files = list(config.documents_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ Aucun PDF trouvé dans: {config.documents_dir}")
        return
    
    print(f"📁 Source: {config.documents_dir}")
    print(f"📁 Destination: {config.output_dir}")
    print(f"📚 Documents trouvés: {len(pdf_files)}")
    print(f"⚙️  Workers parallèles: {config.max_workers}")
    print(f"⚡ Mode: ULTRA RAPIDE (sans spaCy)")
    print()
    
    # Estimation du temps
    avg_doc_size = sum(f.stat().st_size for f in pdf_files[:5]) / min(5, len(pdf_files))
    estimated_time = (len(pdf_files) * avg_doc_size) / (1024 * 1024 * 10)  # Estimation: 10MB/s
    
    print(f"⏱️  Temps estimé: {estimated_time:.1f} - {estimated_time*2:.1f} minutes")
    print("🚀 Démarrage dans 3 secondes...")
    time.sleep(3)
    
    # Exécution
    pipeline = FastRAGPipeline(config)
    
    try:
        report = pipeline.process_all_documents_parallel()
        
        if report.get("successful_documents", 0) > 0:
            print("\n✅ TRAITEMENT TERMINÉ AVEC SUCCÈS!")
        else:
            print("\n⚠️  Aucun document traité avec succès")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur critique: {str(e)}")
        traceback.print_exc()

# ============================================================================
# VERSION SIMPLE EN 1 FICHIER
# ============================================================================

def quick_chunking():
    """Version encore plus simple si vraiment besoin de vitesse"""
    
    print("\n⚡ CHUNKING EXPRESS (pour tests)")
    
    import fitz
    import json
    from pathlib import Path
    
    input_dir = Path(r"C:\Users\KABA\rag_anstat\pro\documents")
    output_dir = Path("./chunks_express")
    output_dir.mkdir(exist_ok=True)
    
    pdf_files = list(input_dir.glob("*.pdf"))
    
    print(f"Traitement de {len(pdf_files)} documents...")
    
    for pdf_path in pdf_files:
        try:
            print(f"  • {pdf_path.name}", end="", flush=True)
            
            doc = fitz.open(pdf_path)
            chunks = []
            chunk_id = 0
            
            for page_num, page in enumerate(doc, 1):
                text = page.get_text("text").strip()
                
                if not text:
                    continue
                
                # Découpage simple par paragraphes
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                
                for para in paragraphs:
                    if 200 <= len(para) <= 1500:  # Filtre de taille
                        chunk = {
                            "chunk_id": f"{pdf_path.stem}_{page_num}_{chunk_id}",
                            "text": para,
                            "metadata": {
                                "document": pdf_path.name,
                                "page": page_num,
                                "size": len(para)
                            }
                        }
                        chunks.append(chunk)
                        chunk_id += 1
            
            doc.close()
            
            # Sauvegarde
            if chunks:
                output_file = output_dir / f"{pdf_path.stem}.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=2)
                
                print(f" ✓ {len(chunks)} chunks")
            else:
                print(" ✗ vide")
                
        except Exception as e:
            print(f" ✗ erreur: {str(e)[:30]}")
    
    print(f"\n✅ Terminé! Résultats dans: {output_dir}")

# ============================================================================
# CHOIX DU MODE
# ============================================================================

if __name__ == "__main__":
    print("Sélectionnez le mode de traitement:")
    print("1. ⚡ Mode ULTRA RAPIDE (recommandé pour 40+ documents)")
    print("2. 🚀 Mode Express (le plus rapide, basique)")
    print("3. 🐌 Mode Complet (avec analyse avancée)")
    
    choice = input("\nVotre choix [1-3] (défaut: 1): ").strip()
    
    if choice == "2":
        quick_chunking()
    elif choice == "3":
        # Importer et exécuter la version complète
        print("Mode Complet non disponible dans cette version rapide.")
        print("Utilisez le fichier original pour l'analyse avancée.")
        main_fast()  # Fallback sur fast
    else:
        main_fast()  # Défaut: mode ultra rapide
        
        
        
        
        
        
# Vérifier la qualité des chunks
import json
from pathlib import Path

# Charger un fichier de chunks
chunk_file = Path("./chunks_output_fast/EHCVM_2018_chunks.json")
with open(chunk_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

chunks = data.get("chunks", [])
print(f"Nombre de chunks: {len(chunks)}")

# Afficher quelques chunks
for i, chunk in enumerate(chunks[:3]):
    print(f"\n=== Chunk {i+1} ===")
    print(f"Taille: {len(chunk['text'])} caractères")
    print(f"Type: {chunk['metadata']['content_type']}")
    print(f"Thèmes: {chunk['metadata']['themes']}")
    print(f"Extrait: {chunk['text'][:200]}...")
    
    
    
    
    
    
    


# Post-traitement optionnel pour améliorer la qualité
def postprocess_chunks(chunks_dir: Path):
    """Amélioration légère après traitement rapide"""
    import hashlib
    
    for chunk_file in chunks_dir.glob("*_chunks.json"):
        with open(chunk_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = data.get("chunks", [])
        
        # 1. Supprimer les doublons exacts
        unique_texts = set()
        unique_chunks = []
        
        for chunk in chunks:
            text = chunk["text"]
            if text not in unique_texts:
                unique_texts.add(text)
                unique_chunks.append(chunk)
        
        # 2. Mettre à jour les IDs
        for i, chunk in enumerate(unique_chunks):
            chunk["chunk_id"] = hashlib.md5(
                f"{chunk['metadata']['document_name']}_{i}".encode()
            ).hexdigest()
        
        # Sauvegarder
        data["chunks"] = unique_chunks
        data["chunks_count"] = len(unique_chunks)
        
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)