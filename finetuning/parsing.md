# Parsing des documents de méthodologies ANSTAT

Ce guide explique comment convertir automatiquement vos documents de méthodologies (PDF, Word, etc.) en données de fine-tuning.

## Vue d'ensemble

```
┌─────────────────────────┐      ┌──────────────────────┐      ┌─────────────────────────┐
│  Documents sources      │      │  parse_methodologies │      │  Données fine-tuning    │
│  ─────────────────      │  ──▶ │  .py                 │  ──▶ │  ──────────────────     │
│  • PDF                  │      │                      │      │  methodologies_anstat   │
│  • DOCX                 │      │  Extraction texte    │      │  .jsonl                 │
│  • TXT                  │      │  Détection sections  │      │                         │
│  • Markdown             │      │  Génération Q&A      │      │  Format prêt pour       │
│                         │      │                      │      │  train_lora.py          │
└─────────────────────────┘      └──────────────────────┘      └─────────────────────────┘
```

## Prérequis

```bash
pip install pymupdf python-docx
```

## Étape 1 : Placer vos documents

Copiez vos documents de méthodologies dans le dossier `methodologies_sources/` :

```bash
finetuning/
└── methodologies_sources/
    ├── methodologie_ipc.pdf
    ├── guide_rgph.docx
    ├── manuel_enquetes_menages.pdf
    ├── comptes_nationaux.pdf
    ├── normes_sdmx.txt
    └── procedures_qualite.md
```

### Formats supportés

| Format | Extension | Bibliothèque |
|--------|-----------|--------------|
| PDF | `.pdf` | PyMuPDF |
| Word | `.docx` | python-docx |
| Texte | `.txt` | Built-in |
| Markdown | `.md`, `.markdown` | Built-in |

## Étape 2 : Lancer le parsing

### Commande de base

```bash
python parse_methodologies.py
```

### Avec options personnalisées

```bash
python parse_methodologies.py \
    --input_dir ./methodologies_sources \
    --output_file ./data/methodologies_anstat.jsonl \
    --max_content_length 40000
```

### Options disponibles

| Option | Description | Valeur par défaut |
|--------|-------------|-------------------|
| `--input_dir` | Dossier contenant les documents | `./methodologies_sources` |
| `--output_file` | Fichier JSONL de sortie | `./data/methodologies_anstat_parsed.jsonl` |
| `--max_content_length` | Longueur maximale du contenu par exemple | `2000` |
| `--append` | Ajouter aux données existantes | `false` |

## Étape 3 : Vérifier les résultats

### Exemple de sortie console

```
============================================================
ANSTAT AI - Parsing des méthodologies
============================================================

📁 5 fichier(s) trouvé(s) dans ./methodologies_sources

📄 Traitement: methodologie_ipc.pdf
   → 8 section(s) extraite(s)
📄 Traitement: guide_rgph.docx
   → 12 section(s) extraite(s)
📄 Traitement: manuel_enquetes.pdf
   → 6 section(s) extraite(s)

📊 Total: 26 sections extraites
📝 Total: 52 exemples de fine-tuning générés

✅ 52 exemples sauvegardés dans ./data/methodologies_anstat.jsonl

============================================================
RÉSUMÉ
============================================================
Fichiers traités: 5
Sections extraites: 26
Exemples générés: 52
Fichier de sortie: ./data/methodologies_anstat.jsonl

Pour lancer le fine-tuning:
  python train_lora.py --data_path ./data/methodologies_anstat.jsonl
```

### Format des données générées

Chaque ligne du fichier JSONL contient :

```json
{
  "instruction": "Comment calcule-t-on l'Indice des Prix à la Consommation ?",
  "input": "",
  "output": "L'IPC est calculé selon la formule de Laspeyres : IPC = Σ(Pi,t / Pi,0) × Wi × 100\n\nOù :\n- Pi,t est le prix au temps t\n- Pi,0 est le prix de base\n- Wi est la pondération du produit\n\nLa collecte des prix est effectuée mensuellement dans les principaux marchés d'Abidjan et des grandes villes.\n\n(Source: methodologie_ipc.pdf, page 15)"
}
```

## Comment le script génère les questions

Le script analyse le titre de chaque section et génère des questions appropriées :

| Mots-clés dans le titre | Questions générées |
|-------------------------|-------------------|
| méthodologie, méthode, procédure | "Quelle est la méthodologie utilisée pour..." |
| calcul, formule, indice | "Comment calcule-t-on..." |
| définition, concept | "Qu'est-ce que..." |
| source, données, collecte | "Quelles sont les sources de données pour..." |
| échantillon, sondage, enquête | "Quelle est la méthodologie d'échantillonnage..." |

## Ajouter des données manuellement

Vous pouvez compléter les données générées avec des exemples manuels :

```bash
# Ajouter aux données existantes
python parse_methodologies.py --append --output_file ./data/methodologies_anstat.jsonl
```

Ou éditer directement le fichier JSONL :

```json
{"instruction": "Quelle est la périodicité de publication de l'IPC ?", "input": "", "output": "L'IPC est publié mensuellement par l'ANSTAT, généralement dans les 15 premiers jours du mois suivant la période de référence."}
```

## Conseils pour de meilleurs résultats

### Structure des documents

Le script détecte mieux les sections si vos documents ont :
- Des titres numérotés (1. Introduction, 2.1 Méthodologie, etc.)
- Des titres en majuscules
- Des titres Markdown (# Titre, ## Sous-titre)

### Recommandations

| Aspect | Recommandation |
|--------|----------------|
| Nombre de documents | 5-20 documents |
| Taille des documents | 10-100 pages chacun |
| Exemples générés | Minimum 50-100 pour de bons résultats |
| Qualité | Relire et corriger les exemples générés |

### Améliorer la qualité

1. **Relire les exemples générés** et corriger les erreurs
2. **Supprimer les doublons** ou exemples peu pertinents
3. **Ajouter des variations** de questions manuellement
4. **Enrichir les réponses** avec plus de détails si nécessaire

## Pipeline complet

```bash
# 1. Placer les documents
cp /path/to/docs/*.pdf ./methodologies_sources/

# 2. Parser les documents
python parse_methodologies.py

# 3. Vérifier le fichier généré
head -5 ./data/methodologies_anstat_parsed.jsonl

# 4. Lancer le fine-tuning
python train_lora.py --data_path ./data/methodologies_anstat_parsed.jsonl
```

## Troubleshooting

### Erreur "PyMuPDF non installé"

```bash
pip install pymupdf
```

### Erreur "python-docx non installé"

```bash
pip install python-docx
```

### Peu de sections extraites

- Vérifiez que vos documents ont des titres bien formatés
- Essayez de convertir les PDF scannés en PDF texte (OCR)
- Utilisez des documents Word plutôt que PDF si possible

### Contenu tronqué

Augmentez la longueur maximale :

```bash
python parse_methodologies.py --max_content_length 3000
```

## Support

Centre de Calcul CAE & DataLab ANSTAT
Email : cae@stat.plan.gouv.ci
