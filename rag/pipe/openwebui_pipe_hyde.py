"""
title: RAG ANSTAT - HyDE
description: RAG avec HyDE (Hypothetical Document Embeddings) - meilleure recherche semantique
author: ANSTAT
version: 1.0
"""

from pydantic import BaseModel, Field
from typing import Union, Generator
import requests
import json
import re


class Pipe:
    """
    Pipe OpenWebUI pour le RAG ANSTAT avec HyDE.
    Avant de chercher dans FAISS, genere une reponse hypothetique via le LLM
    et l'utilise comme query de recherche (meilleure correspondance semantique).
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
        HYDE_MAX_TOKENS: int = Field(
            default=100,
            description="Tokens max pour la reponse hypothetique HyDE",
        )
        REQUEST_TIMEOUT: int = Field(
            default=90,
            description="Timeout en secondes pour les appels HTTP",
        )

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self):
        return [
            {"id": "rag-anstat-hyde", "name": "RAG ANSTAT - HyDE"},
        ]

    def _generate_hyde_query(self, question: str) -> str:
        """
        HyDE : genere une reponse hypothetique a la question.
        Cette reponse est utilisee comme query FAISS au lieu de la question brute,
        car elle ressemble semantiquement bien plus aux vrais documents.
        En cas d'echec, retourne la question originale (fallback transparent).
        """
        try:
            resp = requests.post(
                f"{self.valves.LLM_API_URL}/chat/completions",
                json={
                    "model": self.valves.LLM_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Tu es un expert en statistiques de Cote d'Ivoire. "
                                "Redige un court passage (2-3 phrases) dans le style d'un rapport "
                                "statistique officiel, qui decrirait le contexte et les concepts "
                                "lies a la question. "
                                "N'invente aucun chiffre ni pourcentage precis. "
                                "Concentre-toi sur le vocabulaire technique et thematique "
                                "qui permettrait de retrouver les bons documents."
                            ),
                        },
                        {"role": "user", "content": question},
                    ],
                    "max_tokens": self.valves.HYDE_MAX_TOKENS,
                    "temperature": 0.5,
                    "stream": False,
                },
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if resp.status_code == 200:
                hyde_text = resp.json()["choices"][0]["message"]["content"].strip()
                print(f"[HyDE] Reponse hypothetique : {hyde_text[:80]}...")
                return hyde_text
        except Exception as e:
            print(f"[HyDE] Erreur, fallback sur question brute : {e}")
        return question

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
        sentences = re.split(r'(?<=[.;])\s+|\n+', text)
        key_sentences = []
        other_sentences = []

        for s in sentences:
            s = s.strip()
            if not s or len(s) < 15:
                continue
            if re.search(r'\d', s):
                key_sentences.append(s)
            else:
                other_sentences.append(s)

        result = ""
        if key_sentences:
            result += "DONNEES CHIFFREES :\n"
            result += "\n".join(f"  - {s}" for s in key_sentences)
        if other_sentences:
            result += "\n\nCONTEXTE :\n"
            result += " ".join(other_sentences[:5])

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

    _CONVERSATIONAL_PATTERNS = re.compile(
        r"^\s*(bonjour|bonsoir|salut|hello|hi|coucou|hey|"
        r"merci|merci beaucoup|au revoir|bonne journee|bonne nuit|"
        r"ok|oui|non|d'accord|super|parfait|bien|"
        r"qui es-?tu|qu['\u2019]est[- ]ce que tu (fais|es)|"
        r"comment (tu t['\u2019]appelles|vas-tu|ca va)|ca va)\s*[!?.]*\s*$",
        re.IGNORECASE,
    )

    def _is_conversational(self, question: str) -> bool:
        """Detecte les messages conversationnels qui ne necessitent pas de RAG."""
        q = question.strip()
        if len(q.split()) <= 3 and not re.search(r'\d|combien|quel|quelle|comment|pourquoi|quand|ou ', q, re.IGNORECASE):
            return True
        return bool(self._CONVERSATIONAL_PATTERNS.match(q))

    def _stream_direct(self, question: str) -> Generator:
        """Appelle le LLM sans contexte RAG pour les messages conversationnels."""
        system_message = (
            "Tu es l'assistant documentaire de l'ANSTAT "
            "(Agence Nationale de la Statistique de Cote d'Ivoire). "
            "Reponds de maniere courte et amicale en francais. "
            "Si l'utilisateur pose une vraie question sur des donnees statistiques, "
            "invite-le a reformuler pour que tu puisses chercher dans les documents."
        )
        try:
            with requests.post(
                f"{self.valves.LLM_API_URL}/chat/completions",
                json={
                    "model": self.valves.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": question},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.7,
                    "stream": True,
                },
                headers={"Content-Type": "application/json"},
                timeout=self.valves.REQUEST_TIMEOUT,
                stream=True,
            ) as resp:
                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        token = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield "Bonjour ! Comment puis-je vous aider ?"

    def pipe(self, body: dict) -> Union[str, Generator]:
        """
        Pipeline RAG + HyDE :
        1. Detection conversationnelle (bypass RAG)
        2. Generation d'une reponse hypothetique (HyDE)
        3. Recherche FAISS avec la reponse hypothetique
        4. Construction du prompt avec les sources
        5. Streaming de la reponse finale depuis Qwen2.5
        """
        messages = body.get("messages", [])
        if not messages:
            return "Aucun message fourni."

        question = messages[-1].get("content", "")
        if not question.strip():
            return "Veuillez poser une question."

        print(f"[HyDE Pipe] Question: {question[:100]}...")

        # 1. Bypass RAG pour les messages conversationnels
        if self._is_conversational(question):
            print(f"[HyDE Pipe] Message conversationnel, pas de RAG")
            return self._stream_direct(question)

        # 2. HyDE : generer une reponse hypothetique pour ameliorer la recherche
        search_query = self._generate_hyde_query(question)

        # 3. Recherche documentaire avec la query HyDE
        sources = self._search(search_query)
        print(f"[HyDE Pipe] {len(sources)} sources trouvees")

        if not sources:
            return (
                "Je n'ai pas pu effectuer la recherche dans les documents. "
                "Le service de recherche est peut-etre indisponible."
            )

        # 4. Construire le prompt avec la question originale (pas la query HyDE)
        rag_prompt = self._build_prompt(question, sources)
        sources_text = self._format_sources(sources)

        # 5. Streaming depuis Qwen2.5
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
                with requests.post(
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
                ) as resp:
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

                # Ajouter les sources a la fin (connexion deja fermee)
                yield sources_text

            except Exception as e:
                print(f"[HyDE Pipe] Stream error: {e}")
                yield f"\n\nErreur lors de la generation: {e}"

        return stream_response()
