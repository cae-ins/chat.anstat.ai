# ============================================================
# GRAPH EXTRACTOR - ANSTAT
# Extrait les entités statistiques des chunks pour Neo4j
# Utilise Ollama (gpt-oss:20b) en local
#
# Usage : python graph_extractor.py
# Relançable : reprend là où il s'est arrêté
# ============================================================

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import requests
from tqdm import tqdm

# ============================================================
# CONFIGURATION
# ============================================================

_HERE        = Path(__file__).parent          # rag/scripts/
CHUNKS_DIR   = _HERE / "../data/chunks"
OUTPUT_FILE  = _HERE / "../data/graph/graph_data.json"
PROGRESS_FILE= _HERE / "../data/graph/progress.json"

OLLAMA_URL   = "http://localhost:11434/v1/chat/completions"
OLLAMA_MODEL = "gpt-oss:20b"

SAVE_EVERY   = 50   # Sauvegarde tous les N chunks
MAX_RETRIES  = 3
WORKERS      = 4    # Appels Ollama simultanés (ajuster selon ta RAM)

# ============================================================
# PROMPT D'EXTRACTION
# ============================================================

SYSTEM_PROMPT = (
    "Tu es un extracteur d'entités statistiques pour l'ANSTAT (Côte d'Ivoire). "
    "Tu réponds UNIQUEMENT avec du JSON valide, sans aucune explication."
)

USER_PROMPT_TEMPLATE = """Analyse ce texte extrait d'un rapport statistique officiel.
Extrait TOUS les indicateurs chiffrés trouvés.

Retourne ce JSON strict (et rien d'autre) :
{{
  "domaine": "thème statistique principal (ex: Pauvreté, Éducation, Santé, Démographie, Emploi, Agriculture...)",
  "indicateurs": [
    {{
      "nom": "nom exact de l'indicateur",
      "valeur": "valeur avec unité (ex: 39.4%, 1 200 FCFA, 3.2 millions)",
      "periodicite": "année ou période (ex: 2021, 2018-2019, annuel)",
      "couverture": "zone géographique (ex: National, Rural, Urbain, Abidjan, Région des Lagunes)"
    }}
  ]
}}

Règles :
- Un chiffre ou pourcentage = un indicateur séparé
- Si aucun indicateur chiffré : retourne {{"domaine": "", "indicateurs": []}}
- Ne retourne QUE le JSON, rien avant ni après

Texte :
{text}"""


# ============================================================
# APPEL OLLAMA
# ============================================================

def call_ollama(text: str) -> Optional[dict]:
    """Appelle Ollama et retourne le dict JSON extrait, ou None si échec."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": USER_PROMPT_TEMPLATE.format(text=text[:2000])},
                    ],
                    "temperature": 0.0,
                    "stream": False,
                },
                timeout=90,
            )

            if resp.status_code != 200:
                time.sleep(2)
                continue

            raw = resp.json()["choices"][0]["message"]["content"].strip()

            # Extraire le JSON même si le modèle ajoute du texte autour
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                return json.loads(match.group())

        except (json.JSONDecodeError, KeyError):
            pass
        except requests.RequestException as e:
            print(f"\n[Ollama] Erreur réseau (tentative {attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(3)

    return None


# ============================================================
# CHARGEMENT DES CHUNKS
# ============================================================

def load_all_chunks() -> list:
    """Charge tous les chunks depuis les fichiers JSON."""
    all_chunks = []

    for chunk_file in sorted(CHUNKS_DIR.glob("*_chunks.json")):
        try:
            with open(chunk_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            doc_name = data.get("metadata", {}).get("document_name", chunk_file.stem)

            for chunk in data.get("chunks", []):
                all_chunks.append({
                    "chunk_id": chunk["chunk_id"],
                    "content":  chunk["text"],
                    "doc":      doc_name,
                    "page":     chunk["metadata"]["page_number"],
                })

        except Exception as e:
            print(f"[Chargement] Erreur sur {chunk_file.name}: {e}")

    return all_chunks


# ============================================================
# GESTION DE LA PROGRESSION (reprise après interruption)
# ============================================================

def load_progress() -> set:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_progress(processed_ids: set):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(processed_ids), f)


def load_existing_results() -> list:
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_results(graph_data: list):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, ensure_ascii=False, indent=2)


# ============================================================
# MAIN
# ============================================================

def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("GRAPH EXTRACTOR - ANSTAT")
    print(f"Modèle : {OLLAMA_MODEL}")
    print(f"Source : {CHUNKS_DIR}")
    print(f"Sortie : {OUTPUT_FILE}")
    print("=" * 60)

    # Charger les chunks
    all_chunks = load_all_chunks()
    print(f"\n{len(all_chunks)} chunks chargés")

    # Charger progression et résultats existants
    processed_ids = load_progress()
    graph_data    = load_existing_results()

    pending = [c for c in all_chunks if c["chunk_id"] not in processed_ids]
    print(f"{len(processed_ids)} déjà traités — {len(pending)} restants\n")

    if not pending:
        print("✓ Tout est déjà traité.")
        return

    # Pré-filtrage : ignorer les chunks sans chiffres (~40% de gain)
    before = len(pending)
    pending = [c for c in pending if re.search(r'\d', c["content"])]
    skipped = before - len(pending)
    print(f"{skipped} chunks sans chiffres ignorés → {len(pending)} à traiter\n")

    # Traitement parallèle
    stats = {"extraits": 0, "vides": 0, "erreurs": 0}
    lock_data = []  # résultats collectés depuis les threads

    def process_chunk(chunk):
        result = call_ollama(chunk["content"])
        return chunk, result

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(process_chunk, c): c for c in pending}

        for future in tqdm(as_completed(futures), total=len(futures), desc="Extraction", unit="chunk"):
            chunk, result = future.result()

            if result is None:
                stats["erreurs"] += 1
            elif not result.get("indicateurs"):
                stats["vides"] += 1
            else:
                for ind in result["indicateurs"]:
                    if not ind.get("nom") or not ind.get("valeur"):
                        continue
                    lock_data.append({
                        "domaine":     result.get("domaine", "").strip(),
                        "indicateur":  ind.get("nom", "").strip(),
                        "valeur":      ind.get("valeur", "").strip(),
                        "periodicite": ind.get("periodicite", "").strip(),
                        "couverture":  ind.get("couverture", "National").strip(),
                        "source":      chunk["doc"],
                        "page":        chunk["page"],
                        "chunk_id":    chunk["chunk_id"],
                    })
                    stats["extraits"] += 1

            processed_ids.add(chunk["chunk_id"])
            graph_data.extend(lock_data)
            lock_data.clear()

            # Sauvegarde intermédiaire
            if len(processed_ids) % SAVE_EVERY == 0:
                save_results(graph_data)
                save_progress(processed_ids)

    # Sauvegarde finale
    save_results(graph_data)
    save_progress(processed_ids)

    print("\n" + "=" * 60)
    print(f"✓ Indicateurs extraits : {stats['extraits']}")
    print(f"  Chunks sans données  : {stats['vides']}")
    print(f"  Erreurs Ollama       : {stats['erreurs']}")
    print(f"  Fichier              : {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
