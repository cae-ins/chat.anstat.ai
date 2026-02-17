#!/usr/bin/env python3
"""
Script de fusion des poids LoRA avec le modèle de base
ANSTAT AI - Création du modèle Phi-3.5-mini-ANSTAT

Ce script fusionne les adaptateurs LoRA entraînés avec le modèle de base
pour créer un modèle complet prêt pour le déploiement.
"""

import os
import argparse
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel


def parse_args():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Fusion des poids LoRA avec le modèle de base"
    )
    parser.add_argument(
        "--base_model",
        type=str,
        default="microsoft/Phi-3.5-mini-instruct",
        help="Nom ou chemin du modèle de base"
    )
    parser.add_argument(
        "--lora_path",
        type=str,
        required=True,
        help="Chemin vers les poids LoRA entraînés"
    )
    parser.add_argument(
        "--output_path",
        type=str,
        required=True,
        help="Chemin de sortie pour le modèle fusionné"
    )
    parser.add_argument(
        "--push_to_hub",
        action="store_true",
        help="Pousser le modèle vers HuggingFace Hub"
    )
    parser.add_argument(
        "--hub_model_id",
        type=str,
        default=None,
        help="ID du modèle sur HuggingFace Hub (requis si --push_to_hub)"
    )
    parser.add_argument(
        "--save_safetensors",
        action="store_true",
        default=True,
        help="Sauvegarder en format safetensors (recommandé)"
    )
    return parser.parse_args()


def merge_lora(args):
    """Fusionne les poids LoRA avec le modèle de base."""
    print("=" * 60)
    print("ANSTAT AI - Fusion des poids LoRA")
    print("=" * 60)
    print(f"Modèle de base: {args.base_model}")
    print(f"Poids LoRA: {args.lora_path}")
    print(f"Sortie: {args.output_path}")
    print("=" * 60)

    # Chargement du tokenizer
    print("\n[1/5] Chargement du tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        args.base_model,
        trust_remote_code=True
    )

    # Chargement du modèle de base
    print("\n[2/5] Chargement du modèle de base...")
    base_model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )

    # Chargement des adaptateurs LoRA
    print("\n[3/5] Chargement des adaptateurs LoRA...")
    model = PeftModel.from_pretrained(
        base_model,
        args.lora_path,
        torch_dtype=torch.bfloat16
    )

    # Fusion des poids
    print("\n[4/5] Fusion des poids LoRA avec le modèle de base...")
    model = model.merge_and_unload()

    # Sauvegarde du modèle fusionné
    print(f"\n[5/5] Sauvegarde du modèle fusionné: {args.output_path}")
    os.makedirs(args.output_path, exist_ok=True)

    model.save_pretrained(
        args.output_path,
        safe_serialization=args.save_safetensors
    )
    tokenizer.save_pretrained(args.output_path)

    # Sauvegarde des métadonnées
    metadata = {
        "base_model": args.base_model,
        "lora_path": args.lora_path,
        "model_name": "Phi-3.5-mini-ANSTAT",
        "description": "Phi-3.5-mini fine-tuné sur les méthodologies statistiques ANSTAT",
        "organization": "ANSTAT - Agence Nationale de la Statistique",
        "language": "fr"
    }

    import json
    with open(os.path.join(args.output_path, "anstat_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\nModèle fusionné sauvegardé avec succès!")
    print(f"Chemin: {args.output_path}")

    # Push vers HuggingFace Hub si demandé
    if args.push_to_hub:
        if not args.hub_model_id:
            print("\nErreur: --hub_model_id requis pour --push_to_hub")
            return

        print(f"\nPush vers HuggingFace Hub: {args.hub_model_id}")
        model.push_to_hub(args.hub_model_id, safe_serialization=args.save_safetensors)
        tokenizer.push_to_hub(args.hub_model_id)
        print("Push terminé avec succès!")

    return model, tokenizer


def test_model(model, tokenizer):
    """Test rapide du modèle fusionné."""
    print("\n" + "=" * 60)
    print("Test du modèle fusionné")
    print("=" * 60)

    test_prompts = [
        "Comment calcule-t-on l'IPC à l'ANSTAT ?",
        "Quelle est la méthodologie du RGPH ?",
        "Comment mesure-t-on le taux de chômage ?"
    ]

    for prompt in test_prompts:
        print(f"\nQuestion: {prompt}")
        print("-" * 40)

        # Format Phi-3
        formatted = f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n"

        inputs = tokenizer(formatted, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=200,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id
            )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Extraire uniquement la réponse
        if "<|assistant|>" in response:
            response = response.split("<|assistant|>")[-1].strip()

        print(f"Réponse: {response[:500]}...")


if __name__ == "__main__":
    args = parse_args()
    model, tokenizer = merge_lora(args)

    # Test optionnel
    test_response = input("\nVoulez-vous tester le modèle ? (o/n): ")
    if test_response.lower() == 'o':
        test_model(model, tokenizer)
