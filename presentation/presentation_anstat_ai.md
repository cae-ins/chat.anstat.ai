# ANSTAT AI
## Plateforme d'Intelligence Artificielle pour l'Agence Nationale de la Statistique

---

# Sommaire

1. Vue d'ensemble
2. Qu'est-ce qu'ANSTAT AI ?
3. Architecture simplifiée
4. Fonctionnalités clés
5. Cas d'usage concrets
6. Sécurité et confidentialité
7. Infrastructure technique
8. Avantages de la solution
9. Calendrier et prochaines étapes

---

# 1. Vue d'ensemble

## Le contexte

- L'ANSTAT produit et gère d'importants volumes de **données statistiques**
- Besoin croissant d'**accéder rapidement** aux informations
- Nécessité de **démocratiser l'accès** aux connaissances internes

## La solution

**ANSTAT AI** : Un assistant conversationnel intelligent, accessible via navigateur web, capable de répondre aux questions sur les documents statistiques de l'agence.

---

# 2. Qu'est-ce qu'ANSTAT AI ?

## Un assistant intelligent privé

| Caractéristique | Description |
|-----------------|-------------|
| **Interface** | Chat simple et intuitif (similaire à ChatGPT) |
| **Accès** | Via navigateur web à l'adresse `chat.anstat.ci` |
| **Langue** | Interface et réponses en français |
| **Spécialité** | Documents et données statistiques ANSTAT |

## Ce que l'utilisateur voit

- Une interface de conversation moderne
- Des réponses précises avec **citations des sources**
- Un historique de ses conversations sauvegardé
- Une personnalisation aux couleurs de l'ANSTAT

---

# 3. Architecture simplifiée

## Comment ça fonctionne ?

```
┌─────────────────────────────────────────────────────────┐
│                    UTILISATEUR                          │
│              (Navigateur web)                           │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                 ANSTAT AI                               │
│         Interface de conversation                       │
│         (chat.anstat.ci)                                │
└─────────────────────┬───────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────┐     ┌─────────────────────────────────┐
│   ASSISTANT     │     │   BASE DE CONNAISSANCES         │
│   GÉNÉRAL       │     │   (Documents statistiques)      │
│                 │     │                                 │
│ Questions       │     │ Recherche dans les documents    │
│ générales       │     │ officiels de l'ANSTAT           │
└─────────────────┘     └─────────────────────────────────┘
```

## Les trois modes de fonctionnement

| Mode | Usage | Technologie | Source |
|------|-------|-------------|--------|
| **Conversation générale** | Questions générales | LLM de base | Connaissances du modèle |
| **Méthodologies ANSTAT** | Procédures et méthodes statistiques | Fine-tuning | Intégré au modèle |
| **Rapports et documents** | Données chiffrées, publications | RAG | Recherche vectorielle |

## Deux approches complémentaires

### RAG (Retrieval-Augmented Generation) - Pour les rapports

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Question   │ ──▶ │  Recherche  │ ──▶ │   Réponse    │
│ utilisateur  │     │ vectorielle │     │   sourcée    │
└──────────────┘     └─────────────┘     └──────────────┘
```

- **Contenu** : Rapports statistiques, publications, données chiffrées
- **Avantage** : Réponses avec citations précises (document, page)
- **Mise à jour** : Ajout de nouveaux documents sans réentraînement

### Fine-tuning - Pour les méthodologies

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Question   │ ──▶ │   Modèle    │ ──▶ │   Réponse    │
│ utilisateur  │     │  spécialisé │     │  naturelle   │
└──────────────┘     └─────────────┘     └──────────────┘
```

- **Contenu** : Méthodologies, procédures, normes statistiques ANSTAT
- **Avantage** : Réponses fluides et naturelles, sans recherche
- **Résultat** : L'IA "connaît" les méthodes comme un expert ANSTAT

### Comparaison des approches

| Critère | RAG (Rapports) | Fine-tuning (Méthodologies) |
|---------|----------------|----------------------------|
| **Type de contenu** | Données évolutives | Connaissances stables |
| **Réponse** | Avec citations | Naturelle, intégrée |
| **Mise à jour** | Ajout de documents | Réentraînement du modèle |
| **Latence** | Légèrement plus lente | Rapide |
| **Cas d'usage** | "Quel est le PIB 2024 ?" | "Comment calcule-t-on l'IPC ?" |

---

# 4. Fonctionnalités clés

## Pour les utilisateurs

| Fonctionnalité | Bénéfice |
|----------------|----------|
| **Chat en langage naturel** | Posez vos questions comme à un collègue |
| **Réponses sourcées** | Chaque réponse cite le document et la page |
| **Historique personnel** | Retrouvez vos conversations précédentes |
| **Multi-utilisateurs** | Chaque collaborateur a son propre compte |

## Pour l'organisation

| Fonctionnalité | Bénéfice |
|----------------|----------|
| **Données privées** | Aucune donnée ne quitte les serveurs ANSTAT |
| **Personnalisation** | Interface aux couleurs de l'agence |
| **Gestion des accès** | Validation des nouveaux comptes par un admin |
| **Filigrane** | Réponses identifiées "Généré par ANSTAT AI" |

---

# 5. Cas d'usage concrets

## Exemples de questions possibles

### Recherche documentaire
> "Quels sont les indicateurs démographiques principaux du dernier recensement ?"

### Analyse de données
> "Comment a évolué le taux de chômage ces 5 dernières années ?"

### Méthodologie
> "Quelle méthodologie est utilisée pour calculer l'indice des prix à la consommation ?"

### Support interne
> "Où trouver les données sur l'agriculture dans les rapports 2024 ?"

## Valeur ajoutée

- **Gain de temps** : Réponses instantanées vs recherche manuelle
- **Cohérence** : Réponses basées sur les documents officiels
- **Accessibilité** : Disponible 24h/24, 7j/7

---

# 6. Sécurité et confidentialité

## Principes fondamentaux

| Aspect | Garantie |
|--------|----------|
| **Hébergement** | Serveurs internes ANSTAT (aucun cloud externe) |
| **Données** | Les documents restent sur l'infrastructure interne |
| **Connexion** | Chiffrée (HTTPS) avec certificat de sécurité |
| **Authentification** | Compte personnel avec validation admin |

## Protection des données

```
┌─────────────────────────────────────────┐
│           PÉRIMÈTRE ANSTAT              │
│  ┌───────────────────────────────────┐  │
│  │  Serveur ANSTAT AI                │  │
│  │  ─────────────────                │  │
│  │  • Modèle d'IA                    │  │
│  │  • Documents statistiques         │  │
│  │  • Données utilisateurs           │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ✓ Aucune donnée envoyée à l'extérieur  │
│  ✓ Pas de dépendance cloud (OpenAI, etc)│
└─────────────────────────────────────────┘
```

## Gestion des accès

- **Inscription** : Les nouveaux utilisateurs s'inscrivent
- **Validation** : Un administrateur approuve chaque compte
- **Rôles** : Admin / Utilisateur standard
- **Audit** : Historique des conversations conservé

---

# 7. Infrastructure technique

## Vue simplifiée

| Composant | Rôle | Technologie |
|-----------|------|-------------|
| **Interface utilisateur** | Chat web | Open WebUI |
| **Moteur d'IA** | Génération des réponses | Phi-3.5 (Microsoft) |
| **Base documentaire** | Recherche intelligente | Système RAG |
| **Serveur** | Hébergement | Serveur GPU interne |

## Ressources matérielles

- **Serveur** : `srv-datalab` (serveur interne ANSTAT)
- **Processeur graphique** : GPU NVIDIA pour l'IA
- **Stockage** : Disques locaux sécurisés
- **Accès web** : Domaine `chat.anstat.ci`

## Modèle d'IA utilisé

**Phi-3.5 Mini Instruct** (Microsoft)
- Modèle compact et performant
- Optimisé pour les réponses en français
- Fonctionne entièrement en local
- Aucun envoi de données vers Microsoft

---

# 8. Avantages de la solution

## Comparaison avec les alternatives

| Critère | ChatGPT/Claude | ANSTAT AI |
|---------|----------------|-----------|
| **Confidentialité** | Données envoyées aux USA | Données 100% locales |
| **Coût** | Abonnement mensuel | Infrastructure existante |
| **Personnalisation** | Limitée | Totale (branding, documents) |
| **Documents internes** | Non accessible | Intégrés et consultables |
| **Disponibilité** | Dépend du fournisseur | Contrôle total |

## Bénéfices stratégiques

### Souveraineté numérique
- Indépendance vis-à-vis des fournisseurs étrangers
- Contrôle total sur les données sensibles

### Efficacité opérationnelle
- Réduction du temps de recherche documentaire
- Disponibilité permanente de l'information

### Innovation
- Positionnement de l'ANSTAT comme acteur moderne
- Valorisation du patrimoine documentaire

---

# 9. Calendrier et prochaines étapes

## Feuille de route du déploiement

## Phase 0 : Préparation technique (Août 2025 - Janvier 2026)

| Livrable | Description |
|----------|-------------|
| **Préparation backend** | Mise en place de l'infrastructure Kubernetes et des services |
| **Maîtrise de vLLM** | Apprentissage et configuration du moteur d'inférence vLLM |
| **Tests de modèles** | Évaluation de différents modèles IA (Phi-3, Mistral, Llama, Gemma) |
| **Benchmarks** | Tests de performance et de qualité des réponses |

**Objectif** : Acquérir l'expertise technique et identifier la configuration optimale pour le déploiement.

## Phase 1 : Chat Plain Text (Février 2026)

| Livrable | Description |
|----------|-------------|
| **Interface de chat** | Accès via `chat.anstat.ci` |
| **Assistant général** | Réponses aux questions générales |
| **Gestion des utilisateurs** | Création de comptes et authentification |
| **Personnalisation ANSTAT** | Interface aux couleurs de l'agence |

**Objectif** : Permettre aux utilisateurs de dialoguer avec l'IA pour des questions générales.

## Phase 2 : Version RAG (Avril 2026)

| Livrable | Description |
|----------|-------------|
| **Base documentaire** | Intégration des documents statistiques ANSTAT |
| **Recherche intelligente** | Consultation automatique des sources |
| **Réponses sourcées** | Citations avec références précises |
| **Mode documentation** | Accès aux connaissances internes |

**Objectif** : Permettre à l'IA de répondre en s'appuyant sur les documents officiels de l'ANSTAT.

## Phase 3 : Fine-tuning (Juin 2026)

| Livrable | Description |
|----------|-------------|
| **Spécialisation du modèle** | Entraînement sur les méthodologies statistiques ANSTAT |
| **Intégration des procédures** | Calcul IPC, RGPH, comptes nationaux, enquêtes ménages |
| **Validation métier** | Tests avec les statisticiens experts |
| **Déploiement modèle spécialisé** | Mise en production du modèle fine-tuné |

**Objectif** : L'IA répond naturellement aux questions méthodologiques comme un statisticien ANSTAT expérimenté.

![plan_provisionnel](plan_provisionnel.png)

## Conditionnalités : Passage à l'échelle

### Contexte
- **Effectif ANSTAT** : ~800 employés
- **Usage simultané estimé** : 10-20% soit **80-160 utilisateurs** en même temps

### Capacité selon l'infrastructure GPU

| Configuration | Capacité Chat | Capacité RAG | Couverture ANSTAT |
|---------------|---------------|--------------|-------------------|
| **2x T4** (actuel) | 20-40 users | 15-30 users | 2-5% ⚠️ |
| **2x A100** (cible) | 100-200 users | 70-150 users | 12-25% ✓ |
| **4x A100** (extension) | 200-400 users | 150-300 users | 25-50% ✓✓ |

> **Note** : Avec 4x A100, la couverture atteint 50% des effectifs en simultané, permettant un déploiement complet à l'échelle de l'ANSTAT avec une marge confortable.

### Modèles Open Source supportés selon l'infrastructure

#### Configuration actuelle : 2x NVIDIA T4 (32 Go VRAM)

| Modèle | Paramètres | Qualité | Utilisateurs Chat | Utilisateurs RAG |
|--------|------------|---------|-------------------|------------------|
| **Phi-3.5 Mini** (actuel) | 3.8B | ★★★☆☆ | 20-40 | 15-30 |
| **Mistral 7B** | 7B | ★★★☆☆ | 15-30 | 10-25 |
| **Llama 3.1 8B** | 8B | ★★★☆☆ | 15-30 | 10-25 |
| **Gemma 2 9B** | 9B | ★★★★☆ | 10-25 | 8-20 |
| **GPT-OSS** (quantifié) | 20B | ★★★★☆ | 5-10 | 3-8 |

#### Configuration cible : 2x NVIDIA A100 (80 Go VRAM)

| Modèle | Paramètres | Qualité | Utilisateurs Chat | Utilisateurs RAG |
|--------|------------|---------|-------------------|------------------|
| **Llama 3.1 8B** | 8B | ★★★☆☆ | 100-200 | 70-150 |
| **Mistral Nemo 12B** | 12B | ★★★★☆ | 80-160 | 60-120 |
| **GPT-OSS** | 20B | ★★★★☆ | 60-120 | 40-90 |
| **Qwen 2.5 32B** | 32B | ★★★★☆ | 50-100 | 40-80 |
| **Mixtral 8x7B** | 47B | ★★★★☆ | 40-80 | 30-60 |
| **Llama 3.1 70B** (quantifié) | 70B | ★★★★★ | 30-60 | 20-50 |

#### Configuration extension : 4x NVIDIA A100 (160 Go VRAM)

| Modèle | Paramètres | Qualité | Utilisateurs Chat | Utilisateurs RAG |
|--------|------------|---------|-------------------|------------------|
| **Llama 3.1 8B** | 8B | ★★★☆☆ | 200-400 | 150-300 |
| **GPT-OSS** | 20B | ★★★★☆ | 120-240 | 90-180 |
| **Qwen 2.5 32B** | 32B | ★★★★☆ | 150-300 | 100-200 |
| **Llama 3.1 70B** (pleine précision) | 70B | ★★★★★ | 80-160 | 60-120 |
| **Qwen 2.5 72B** | 72B | ★★★★★ | 70-140 | 50-100 |
| **Mixtral 8x22B** | 141B | ★★★★★ | 40-80 | 30-60 |
| **DeepSeek-V2** (quantifié) | 236B | ★★★★★ | 20-40 | 15-30 |

> **Avantage clé** : Avec 4x A100, l'ANSTAT pourra utiliser des modèles de classe "frontier" (70B+) avec des performances comparables à GPT-4, tout en gardant les données 100% locales.

### Plan d'acquisition matérielle

![architecture](evolution_infrastructure.png)

### Stratégie de déploiement progressif

| Phase | Période | Infrastructure | Public cible | Utilisateurs |
|-------|---------|----------------|--------------|--------------|
| **1** | Fév. 2026 | 2x T4 | Groupe pilote | ~40 personnes |
| **2** | Avr. 2026 | 2x T4 | Pilote élargi + RAG | ~30 personnes |
| **3** | Déc. 2026 | 2x A100 | Déploiement ANSTAT | ~200 personnes |
| **4** | 2027+ | 4x A100 | Couverture totale | ~400 personnes |

### Conditions d'acquisition

> **Phase 3 - Acquisition de 2 cartes NVIDIA A100 (fin 2026) :**
> - Passer de 40 à 200 utilisateurs simultanés
> - Supporter la charge du RAG à grande échelle
> - **Permettre le fine-tuning sur les méthodologies ANSTAT**
> - Permettre le déploiement à l'ensemble des départements ANSTAT

> **Phase 4 - Acquisition de 2 cartes A100 supplémentaires (2027+, optionnel) :**
> - Doubler la capacité à 400 utilisateurs simultanés
> - Garantir une couverture de 50% des effectifs en pic d'usage
> - Permettre l'utilisation de modèles IA plus performants (70B+)
> - **Fine-tuning avancé avec modèles de grande taille**

### Fine-tuning : Intégration des méthodologies ANSTAT

Le fine-tuning permettra d'intégrer directement les méthodologies statistiques dans le modèle IA :

| Méthodologie | Description | Bénéfice |
|--------------|-------------|----------|
| **Calcul de l'IPC** | Indice des Prix à la Consommation | Réponses expertes sur l'inflation |
| **Méthodologie RGPH** | Recensement Général de la Population | Expertise démographique |
| **Comptes nationaux** | PIB, agrégats économiques | Analyse économique précise |
| **Enquêtes ménages** | Procédures d'échantillonnage | Méthodologie d'enquête |
| **Normes SDMX** | Standards de diffusion statistique | Conformité internationale |

> **Avantage clé** : L'IA répondra naturellement aux questions méthodologiques comme un statisticien ANSTAT expérimenté, sans recherche dans les documents.

### Prérequis GPU pour le fine-tuning

| Configuration | Fine-tuning possible | Taille modèle max |
|---------------|---------------------|-------------------|
| 2x T4 (32 Go) | Limité (LoRA uniquement) | ~7B paramètres |
| 2x A100 (80 Go) | **Oui** | ~30B paramètres |
| 4x A100 (160 Go) | **Oui (avancé)** | ~70B paramètres |

## Évolutions futures envisageables

### Après le déploiement initial
- [ ] Finalisation de la fonctionnalité RAG pour les rapports
- [ ] Amélioration de la vitesse de réponse de la fonctionnalité RAG
- [ ] Possibilité de changement de modèles IA pour amélioration des performances
- [ ] Formation des utilisateurs pilotes
- [ ] Collecte des retours d'expérience
- [ ] Ajout progressif de nouveaux documents

### Moyen terme (avec A100)
- [ ] **Fine-tuning sur les méthodologies principales ANSTAT**
- [ ] Extension à d'autres départements
- [ ] Enrichissement continu de la base documentaire RAG
- [ ] Ajout de fonctionnalités (export PDF, partage)

### Long terme (avec 4x A100)
- [ ] **Fine-tuning avancé avec modèles 70B+**
- [ ] Intégration avec d'autres systèmes ANSTAT
- [ ] Analyse automatique de nouveaux rapports
- [ ] Tableaux de bord analytiques

---

# Résumé

## ANSTAT AI en 5 points

1. **Assistant IA privé** accessible via `chat.anstat.ci`

2. **Spécialisé** dans les documents statistiques ANSTAT

3. **100% local** : aucune donnée ne quitte l'infrastructure

4. **Sourcé** : chaque réponse cite ses références

5. **Sécurisé** : authentification et validation des accès

---

# Questions ?

## Contacts

- **Équipe technique** : Centre de Calul CAE & DataLab ANSTAT 
- **Administration** : cae@stat.plan.gouv.ci

## Ressources

- Accès : https://chat.anstat.ci
- Documentation : Disponible sur demande

---

# Annexe : Glossaire

| Terme | Définition simple |
|-------|-------------------|
| **IA / Intelligence Artificielle** | Programme informatique capable de comprendre et générer du texte |
| **LLM (Large Language Model)** | Type d'IA spécialisé dans le langage naturel |
| **RAG** | Technologie permettant à l'IA de consulter des documents pour répondre |
| **Fine-tuning** | Entraînement spécialisé d'un modèle IA sur des données métier pour le rendre expert dans un domaine |
| **GPU** | Processeur spécialisé pour les calculs d'IA |
| **Open Source** | Logiciel dont le code est public et gratuit |
| **Phi-3** | Nom du modèle d'IA de Microsoft utilisé |
| **Kubernetes** | Système de gestion automatique des serveurs |

---

# Annexe : Captures d'écran

## Interface de login
![Interface de chat](login.png)

## Interface de chat
![Interface de chat](capture_chat_base.png)

## Exemple de réponse 
![Interface de chat](capture_chat_base_resultats.png)

## Exemple de réponse sourcée
![Interface de chat](image.png)

## Exemple de réponse sourcée
![Interface de chat](erreur_dans_du_code.png)
---
