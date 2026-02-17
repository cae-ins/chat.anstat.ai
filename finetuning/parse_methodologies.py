#!/usr/bin/env python3
"""
Script de parsing des documents de méthodologies ANSTAT
Convertit les documents PDF, DOCX, TXT, MD en format JSONL pour le fine-tuning

Usage:
    python parse_methodologies.py --input_dir ./methodologies_sources --output_file ./data/methodologies_anstat.jsonl
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class Section:
    """Représente une section de document."""
    title: str
    content: str
    source_file: str
    page_number: Optional[int] = None


@dataclass
class TrainingExample:
    """Exemple de fine-tuning."""
    instruction: str
    input: str
    output: str


# =============================================================================
# EXTRACTEURS DE TEXTE
# =============================================================================

def extract_from_pdf(file_path: str) -> List[Tuple[str, int]]:
    """Extrait le texte d'un fichier PDF avec numéros de page."""
    try:
        import pymupdf  # PyMuPDF
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            print(f"⚠️  PyMuPDF non installé. Installer avec: pip install pymupdf")
            return []

    pages = []
    try:
        doc = pymupdf.open(file_path)
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            if text.strip():
                pages.append((text.strip(), page_num))
        doc.close()
    except Exception as e:
        print(f"❌ Erreur lecture PDF {file_path}: {e}")

    return pages


def extract_from_docx(file_path: str) -> str:
    """Extrait le texte d'un fichier Word DOCX."""
    try:
        from docx import Document
    except ImportError:
        print(f"⚠️  python-docx non installé. Installer avec: pip install python-docx")
        return ""

    try:
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as e:
        print(f"❌ Erreur lecture DOCX {file_path}: {e}")
        return ""


def extract_from_txt(file_path: str) -> str:
    """Extrait le texte d'un fichier TXT."""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    print(f"❌ Erreur encodage {file_path}")
    return ""


def extract_from_markdown(file_path: str) -> str:
    """Extrait le texte d'un fichier Markdown."""
    return extract_from_txt(file_path)


# =============================================================================
# DETECTION DES SECTIONS
# =============================================================================

def detect_sections(text: str, source_file: str) -> List[Section]:
    """Détecte et extrait les sections d'un texte."""
    sections = []

    # Patterns pour détecter les titres de sections
    patterns = [
        # Titres numérotés (1. Titre, 1.1 Titre, etc.)
        r'^(\d+\.?\d*\.?\d*\.?\s+[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][^\n]+)',
        # Titres en majuscules
        r'^([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ\s]{10,}[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ])$',
        # Titres avec tirets ou underscores
        r'^([-=]{3,})\n(.+)\n\1',
        # Markdown headers
        r'^(#{1,3})\s+(.+)$',
    ]

    # Découpage par lignes vides multiples comme fallback
    paragraphs = re.split(r'\n{2,}', text)

    current_title = "Introduction"
    current_content = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Vérifier si c'est un titre
        is_title = False
        for pattern in patterns:
            if re.match(pattern, para, re.MULTILINE):
                # Sauvegarder la section précédente
                if current_content:
                    sections.append(Section(
                        title=current_title,
                        content="\n\n".join(current_content),
                        source_file=source_file
                    ))

                # Nouvelle section
                current_title = para.strip('#- \t')
                current_content = []
                is_title = True
                break

        if not is_title:
            current_content.append(para)

    # Dernière section
    if current_content:
        sections.append(Section(
            title=current_title,
            content="\n\n".join(current_content),
            source_file=source_file
        ))

    return sections


def detect_sections_from_pdf(pages: List[Tuple[str, int]], source_file: str) -> List[Section]:
    """Détecte les sections depuis des pages PDF."""
    sections = []
    full_text = "\n\n".join([text for text, _ in pages])

    # Utiliser la détection standard
    base_sections = detect_sections(full_text, source_file)

    # Ajouter les numéros de page approximatifs
    current_page = 1
    for section in base_sections:
        for text, page_num in pages:
            if section.content[:100] in text:
                section.page_number = page_num
                break
        sections.append(section)

    return sections


# =============================================================================
# GENERATION DES EXEMPLES DE FINE-TUNING
# =============================================================================

def generate_questions_for_section(section: Section) -> List[str]:
    """Génère des questions pertinentes pour une section."""
    questions = []
    title = section.title.lower()
    content = section.content.lower()

    # Questions basées sur le titre
    if any(word in title for word in ['méthodologie', 'méthode', 'procédure']):
        questions.append(f"Quelle est la méthodologie utilisée pour {section.title.lower()} ?")
        questions.append(f"Explique-moi la procédure de {section.title.lower()}.")

    if any(word in title for word in ['calcul', 'formule', 'indice']):
        questions.append(f"Comment calcule-t-on {section.title.lower()} ?")
        questions.append(f"Quelle est la formule de {section.title.lower()} ?")

    if any(word in title for word in ['définition', 'concept']):
        questions.append(f"Qu'est-ce que {section.title.lower()} ?")
        questions.append(f"Définis {section.title.lower()}.")

    if any(word in title for word in ['source', 'données', 'collecte']):
        questions.append(f"Quelles sont les sources de données pour {section.title.lower()} ?")
        questions.append(f"Comment sont collectées les données de {section.title.lower()} ?")

    if any(word in title for word in ['échantillon', 'sondage', 'enquête']):
        questions.append(f"Quelle est la méthodologie d'échantillonnage pour {section.title.lower()} ?")

    # Questions génériques si aucune spécifique
    if not questions:
        questions.append(f"Explique-moi {section.title}.")
        questions.append(f"Qu'est-ce que {section.title} selon l'ANSTAT ?")

    return questions


def generate_training_examples(sections: List[Section],
                               max_content_length: int = 2000) -> List[TrainingExample]:
    """Génère les exemples de fine-tuning depuis les sections."""
    examples = []

    for section in sections:
        # Ignorer les sections trop courtes
        if len(section.content) < 100:
            continue

        # Tronquer si trop long
        content = section.content
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        # Nettoyer le contenu
        content = clean_text(content)

        # Générer les questions
        questions = generate_questions_for_section(section)

        for question in questions:
            # Ajouter la source dans la réponse
            source_info = f"\n\n(Source: {section.source_file}"
            if section.page_number:
                source_info += f", page {section.page_number}"
            source_info += ")"

            examples.append(TrainingExample(
                instruction=question,
                input="",
                output=content + source_info
            ))

    return examples


def clean_text(text: str) -> str:
    """Nettoie le texte extrait."""
    # Supprimer les espaces multiples
    text = re.sub(r' +', ' ', text)
    # Supprimer les lignes vides multiples
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Supprimer les caractères de contrôle
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()


# =============================================================================
# PIPELINE PRINCIPAL
# =============================================================================

def process_file(file_path: str) -> List[Section]:
    """Traite un fichier et extrait les sections."""
    ext = Path(file_path).suffix.lower()
    filename = Path(file_path).name

    print(f"📄 Traitement: {filename}")

    if ext == '.pdf':
        pages = extract_from_pdf(file_path)
        if pages:
            return detect_sections_from_pdf(pages, filename)
    elif ext == '.docx':
        text = extract_from_docx(file_path)
        if text:
            return detect_sections(text, filename)
    elif ext == '.txt':
        text = extract_from_txt(file_path)
        if text:
            return detect_sections(text, filename)
    elif ext in ['.md', '.markdown']:
        text = extract_from_markdown(file_path)
        if text:
            return detect_sections(text, filename)
    else:
        print(f"⚠️  Format non supporté: {ext}")

    return []


def process_directory(input_dir: str) -> List[Section]:
    """Traite tous les fichiers d'un répertoire."""
    all_sections = []
    supported_extensions = {'.pdf', '.docx', '.txt', '.md', '.markdown'}

    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"❌ Répertoire non trouvé: {input_dir}")
        return []

    files = [f for f in input_path.iterdir()
             if f.is_file() and f.suffix.lower() in supported_extensions]

    if not files:
        print(f"⚠️  Aucun fichier supporté trouvé dans {input_dir}")
        print(f"   Formats supportés: {', '.join(supported_extensions)}")
        return []

    print(f"\n📁 {len(files)} fichier(s) trouvé(s) dans {input_dir}\n")

    for file_path in sorted(files):
        sections = process_file(str(file_path))
        all_sections.extend(sections)
        print(f"   → {len(sections)} section(s) extraite(s)")

    return all_sections


def save_to_jsonl(examples: List[TrainingExample], output_file: str):
    """Sauvegarde les exemples en format JSONL."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        for example in examples:
            json_line = json.dumps(asdict(example), ensure_ascii=False)
            f.write(json_line + '\n')

    print(f"\n✅ {len(examples)} exemples sauvegardés dans {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Parse les documents de méthodologies ANSTAT pour le fine-tuning"
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        default="./methodologies_sources",
        help="Répertoire contenant les documents de méthodologies"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="./data/methodologies_anstat_parsed.jsonl",
        help="Fichier JSONL de sortie"
    )
    parser.add_argument(
        "--max_content_length",
        type=int,
        default=2000,
        help="Longueur maximale du contenu par exemple"
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Ajouter aux données existantes au lieu de remplacer"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("ANSTAT AI - Parsing des méthodologies")
    print("=" * 60)

    # Extraction des sections
    sections = process_directory(args.input_dir)

    if not sections:
        print("\n❌ Aucune section extraite. Vérifiez vos documents.")
        return

    print(f"\n📊 Total: {len(sections)} sections extraites")

    # Génération des exemples
    examples = generate_training_examples(sections, args.max_content_length)

    print(f"📝 Total: {len(examples)} exemples de fine-tuning générés")

    # Chargement des données existantes si append
    if args.append and Path(args.output_file).exists():
        with open(args.output_file, 'r', encoding='utf-8') as f:
            existing = [json.loads(line) for line in f]
        existing_examples = [TrainingExample(**e) for e in existing]
        examples = existing_examples + examples
        print(f"📎 Ajout aux {len(existing_examples)} exemples existants")

    # Sauvegarde
    save_to_jsonl(examples, args.output_file)

    # Résumé
    print("\n" + "=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)
    print(f"Fichiers traités: {len(set(s.source_file for s in sections))}")
    print(f"Sections extraites: {len(sections)}")
    print(f"Exemples générés: {len(examples)}")
    print(f"Fichier de sortie: {args.output_file}")
    print("\nPour lancer le fine-tuning:")
    print(f"  python train_lora.py --data_path {args.output_file}")


if __name__ == "__main__":
    main()
