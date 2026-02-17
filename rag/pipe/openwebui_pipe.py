"""
title: RAG ANSTAT
description: Recherche documentaire sur les publications statistiques ANSTAT avec RAG
author: ANSTAT
version: 2.2
"""

from pydantic import BaseModel, Field
from typing import Optional, Union, Generator
import requests
import json
import re


class Pipe:
    """
    Pipe OpenWebUI pour le RAG ANSTAT.
    Fait la recherche dans les documents, construit le prompt avec contexte,
    et streame la reponse depuis Qwen2.5 directement via OpenWebUI.
    """

    class Valves(BaseModel):
        RAG_SEARCH_URL: str = Field(
            default="http://rag-search-service:8084/search",
            description="URL du service de recherche RAG",
        )
        LLM_API_URL: str = Field(
            default="http://qwen25-service:8000/v1",
            description="URL de l'API LLM (vLLM)",
        )
        LLM_MODEL: str = Field(
            default="Qwen/Qwen2.5-7B-Instruct-AWQ",
            description="Nom du modele LLM",
        )
        LLM_MAX_TOKENS: int = Field(
            default=1000,
            description="Nombre max de tokens generes",
        )
        LLM_TEMPERATURE: float = Field(
            default=0.1,
            description="Temperature du LLM",
        )
        TOP_K_RERANK: int = Field(
            default=3,
            description="Nombre de sources a envoyer au LLM",
        )
        REQUEST_TIMEOUT: int = Field(
            default=90,
            description="Timeout en secondes pour les appels HTTP",
        )

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self):
        return [
            {"id": "rag-anstat", "name": "RAG ANSTAT"},
        ]

    def _search(self, query: str) -> list:
        """Appelle le service de recherche RAG."""
        try:
            resp = requests.post(
                self.valves.RAG_SEARCH_URL,
                json={
                    "query": query,
                    "top_k_rerank": self.valves.TOP_K_RERANK,
                },
                timeout=self.valves.REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json().get("results", [])
            print(f"[RAG] Search error (status {resp.status_code}): {resp.text}")
            return []
        except Exception as e:
            print(f"[RAG] Search failed: {e}")
            return []

    def _extract_key_sentences(self, text: str) -> str:
        """
        Extrait les phrases contenant des chiffres/pourcentages/donnees.
        Cela aide le LLM a trouver les informations dans un texte dense.
        """
        # Decouper en phrases (par point, point-virgule, retour a la ligne)
        sentences = re.split(r'(?<=[.;])\s+|\n+', text)

        key_sentences = []
        other_sentences = []

        for s in sentences:
            s = s.strip()
            if not s or len(s) < 15:
                continue
            # Une phrase est "cle" si elle contient un chiffre
            if re.search(r'\d', s):
                key_sentences.append(s)
            else:
                other_sentences.append(s)

        # Construire le texte : phrases avec chiffres en premier, puis contexte
        result = ""
        if key_sentences:
            result += "DONNEES CHIFFREES :\n"
            result += "\n".join(f"  - {s}" for s in key_sentences)
        if other_sentences:
            result += "\n\nCONTEXTE :\n"
            result += " ".join(other_sentences[:5])  # Max 5 phrases de contexte

        return result if result else text[:1500]

    def _build_prompt(self, question: str, sources: list) -> str:
        """Construit le prompt RAG avec les sources."""
        context = ""
        for i, s in enumerate(sources, 1):
            extracted = self._extract_key_sentences(s["content"])
            context += (
                f"--- SOURCE {i} : {s['doc']} (page {s['page']}) ---\n"
                f"{extracted}\n\n"
            )

        prompt = (
            f"EXTRAITS DE DOCUMENTS OFFICIELS ANSTAT :\n\n"
            f"{context}"
            f"QUESTION : {question}\n\n"
            f"Reponds en utilisant les donnees ci-dessus. "
            f"Donne les chiffres exacts, puis explique et contextualise. "
            f"Indique le document et la page pour chaque information."
        )

        return prompt

    def _format_sources(self, sources: list) -> str:
        """Formate les sources pour les ajouter a la fin de la reponse."""
        text = "\n\n---\n**Sources consultees :**\n"
        for i, s in enumerate(sources, 1):
            text += f"{i}. {s['doc']} - page {s['page']}\n"
        return text

    def pipe(self, body: dict) -> Union[str, Generator]:
        """
        Pipeline RAG complet :
        1. Recherche dans les documents (FAISS + reranking)
        2. Extraction des phrases cles avec chiffres
        3. Construction du prompt
        4. Streaming depuis Qwen2.5
        """
        messages = body.get("messages", [])
        if not messages:
            return "Aucun message fourni."

        question = messages[-1].get("content", "")
        if not question.strip():
            return "Veuillez poser une question."

        print(f"[RAG Pipe] Question: {question[:100]}...")

        # 1. Recherche documentaire
        sources = self._search(question)
        print(f"[RAG Pipe] {len(sources)} sources trouvees")

        if not sources:
            return (
                "Je n'ai pas pu effectuer la recherche dans les documents. "
                "Le service de recherche est peut-etre indisponible."
            )

        # 2. Construire le prompt avec contexte
        rag_prompt = self._build_prompt(question, sources)
        sources_text = self._format_sources(sources)

        # 3. Appeler Qwen2.5 en streaming
        system_message = (
            "Tu es l'assistant documentaire de l'ANSTAT "
            "(Agence Nationale de la Statistique de Cote d'Ivoire). "
            "On te fournit des extraits de documents officiels. "
            "Reponds en francais de maniere claire et structuree. "
            "Donne les chiffres exacts trouves dans les extraits, "
            "puis explique et contextualise les donnees pour aider l'utilisateur a comprendre. "
            "Tu peux comparer des periodes, souligner des tendances, "
            "et mettre en perspective les resultats. "
            "Cite toujours le document et la page."
        )

        def stream_response():
            try:
                resp = requests.post(
                    f"{self.valves.LLM_API_URL}/chat/completions",
                    json={
                        "model": self.valves.LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": rag_prompt},
                        ],
                        "max_tokens": self.valves.LLM_MAX_TOKENS,
                        "temperature": self.valves.LLM_TEMPERATURE,
                        "stream": True,
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=self.valves.REQUEST_TIMEOUT,
                    stream=True,
                )

                if resp.status_code != 200:
                    yield f"Erreur LLM (status {resp.status_code})"
                    return

                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue

                # Ajouter les sources a la fin
                yield sources_text

            except Exception as e:
                print(f"[RAG Pipe] Stream error: {e}")
                yield f"\n\nErreur lors de la generation: {e}"

        return stream_response()
