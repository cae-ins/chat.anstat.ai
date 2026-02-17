#!/usr/bin/env python3
"""
Fine-tuning LoRA pour Phi-3.5-mini-instruct
ANSTAT AI - Intégration des méthodologies statistiques

Ce script permet de fine-tuner le modèle Phi-3.5-mini avec l'approche LoRA
pour intégrer les méthodologies statistiques de l'ANSTAT.
"""

import os
import json
import torch
import argparse
from datetime import datetime
from datasets import load_dataset, Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    BitsAndBytesConfig
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType
)

# Configuration par défaut
DEFAULT_MODEL = "microsoft/Phi-3.5-mini-instruct"
DEFAULT_OUTPUT_DIR = "./output/phi3-anstat-lora"
DEFAULT_DATA_PATH = "./data/methodologies_anstat.jsonl"


def parse_args():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Fine-tuning LoRA de Phi-3.5-mini pour ANSTAT"
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default=DEFAULT_MODEL,
        help="Nom du modèle de base HuggingFace"
    )
    parser.add_argument(
        "--data_path",
        type=str,
        default=DEFAULT_DATA_PATH,
        help="Chemin vers les données d'entraînement (JSONL)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Répertoire de sortie pour le modèle fine-tuné"
    )
    parser.add_argument(
        "--num_epochs",
        type=int,
        default=3,
        help="Nombre d'époques d'entraînement"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=4,
        help="Taille du batch d'entraînement"
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=2e-4,
        help="Taux d'apprentissage"
    )
    parser.add_argument(
        "--max_length",
        type=int,
        default=2048,
        help="Longueur maximale des séquences"
    )
    parser.add_argument(
        "--lora_r",
        type=int,
        default=16,
        help="Rang LoRA (dimension de la décomposition)"
    )
    parser.add_argument(
        "--lora_alpha",
        type=int,
        default=32,
        help="Alpha LoRA (facteur de scaling)"
    )
    parser.add_argument(
        "--lora_dropout",
        type=float,
        default=0.05,
        help="Dropout LoRA"
    )
    parser.add_argument(
        "--use_4bit",
        action="store_true",
        help="Utiliser la quantification 4-bit (QLoRA)"
    )
    parser.add_argument(
        "--use_8bit",
        action="store_true",
        help="Utiliser la quantification 8-bit"
    )
    parser.add_argument(
        "--gradient_checkpointing",
        action="store_true",
        help="Activer le gradient checkpointing pour économiser la mémoire"
    )
    return parser.parse_args()


def load_tokenizer(model_name: str):
    """Charge le tokenizer."""
    print(f"Chargement du tokenizer: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
        padding_side="right"
    )

    # Phi-3 utilise un token de padding spécial
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    return tokenizer


def load_model(model_name: str, use_4bit: bool = False, use_8bit: bool = False):
    """Charge le modèle avec quantification optionnelle."""
    print(f"Chargement du modèle: {model_name}")

    # Configuration de la quantification
    bnb_config = None
    if use_4bit:
        print("Utilisation de la quantification 4-bit (QLoRA)")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True
        )
    elif use_8bit:
        print("Utilisation de la quantification 8-bit")
        bnb_config = BitsAndBytesConfig(load_in_8bit=True)

    # Chargement du modèle
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16 if not (use_4bit or use_8bit) else None,
        attn_implementation="flash_attention_2"  # Optimisation pour Phi-3
    )

    # Préparation pour l'entraînement k-bit si quantifié
    if use_4bit or use_8bit:
        model = prepare_model_for_kbit_training(model)

    return model


def create_lora_config(args):
    """Crée la configuration LoRA."""
    print(f"Configuration LoRA: r={args.lora_r}, alpha={args.lora_alpha}, dropout={args.lora_dropout}")

    # Modules cibles pour Phi-3
    target_modules = [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj"
    ]

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=target_modules,
        bias="none",
        task_type=TaskType.CAUSAL_LM
    )

    return lora_config


def format_prompt(example: dict) -> str:
    """
    Formate un exemple en prompt pour Phi-3.

    Format attendu des données:
    {
        "instruction": "Question ou instruction",
        "input": "Contexte optionnel",
        "output": "Réponse attendue"
    }
    """
    instruction = example.get("instruction", "")
    input_text = example.get("input", "")
    output = example.get("output", "")

    # Format de prompt Phi-3
    if input_text:
        prompt = f"""<|user|>
{instruction}

Contexte: {input_text}<|end|>
<|assistant|>
{output}<|end|>"""
    else:
        prompt = f"""<|user|>
{instruction}<|end|>
<|assistant|>
{output}<|end|>"""

    return prompt


def load_and_prepare_data(data_path: str, tokenizer, max_length: int):
    """Charge et prépare les données d'entraînement."""
    print(f"Chargement des données: {data_path}")

    # Chargement des données JSONL
    with open(data_path, "r", encoding="utf-8") as f:
        data = [json.loads(line) for line in f]

    print(f"Nombre d'exemples: {len(data)}")

    # Formatage des prompts
    formatted_data = []
    for example in data:
        formatted_text = format_prompt(example)
        formatted_data.append({"text": formatted_text})

    # Création du dataset
    dataset = Dataset.from_list(formatted_data)

    # Tokenisation
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding="max_length",
            return_tensors=None
        )

    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text"],
        desc="Tokenisation"
    )

    return tokenized_dataset


def train(args):
    """Fonction principale d'entraînement."""
    print("=" * 60)
    print("ANSTAT AI - Fine-tuning LoRA de Phi-3.5-mini")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modèle de base: {args.model_name}")
    print(f"Données: {args.data_path}")
    print(f"Sortie: {args.output_dir}")
    print("=" * 60)

    # Chargement du tokenizer et du modèle
    tokenizer = load_tokenizer(args.model_name)
    model = load_model(args.model_name, args.use_4bit, args.use_8bit)

    # Configuration et application de LoRA
    lora_config = create_lora_config(args)
    model = get_peft_model(model, lora_config)

    # Affichage des paramètres entraînables
    model.print_trainable_parameters()

    # Gradient checkpointing
    if args.gradient_checkpointing:
        print("Activation du gradient checkpointing")
        model.gradient_checkpointing_enable()

    # Chargement des données
    train_dataset = load_and_prepare_data(args.data_path, tokenizer, args.max_length)

    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False
    )

    # Configuration de l'entraînement
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        learning_rate=args.learning_rate,
        weight_decay=0.01,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        logging_steps=10,
        save_steps=100,
        save_total_limit=3,
        fp16=False,
        bf16=True,
        optim="paged_adamw_8bit" if (args.use_4bit or args.use_8bit) else "adamw_torch",
        report_to="none",
        gradient_checkpointing=args.gradient_checkpointing,
        max_grad_norm=0.3,
        group_by_length=True,
        dataloader_num_workers=4
    )

    # Création du Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer
    )

    # Entraînement
    print("\nDémarrage de l'entraînement...")
    trainer.train()

    # Sauvegarde du modèle LoRA
    print(f"\nSauvegarde du modèle LoRA: {args.output_dir}")
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    # Sauvegarde de la configuration
    config_path = os.path.join(args.output_dir, "training_config.json")
    with open(config_path, "w") as f:
        json.dump(vars(args), f, indent=2)

    print("\nEntraînement terminé avec succès!")
    print(f"Modèle LoRA sauvegardé dans: {args.output_dir}")

    return model, tokenizer


if __name__ == "__main__":
    args = parse_args()
    train(args)
