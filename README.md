# Bot Telegram Marketplace de Campagnes MVP - TRON Only

## Description

Bot Telegram de marketplace de campagnes permettant aux annonceurs de créer des campagnes de parrainage et aux participants de gagner des TRX en validant des tâches. Le système intègre un mécanisme de parrainage à 1 niveau et utilise exclusivement la blockchain TRON.

## Fonctionnalités Principales

### Pour les Annonceurs
- **Gestion des campagnes** : création, recharge, pause/reprise
- **Financement** : dépôt de TRX vers ad_balance
- **Suivi** : statistiques et performances des campagnes
- **Contrôle** : gestion du statut actif/inactif

### Pour les Participants
- **Découverte** : navigation des campagnes disponibles via /browse_bots
- **Participation** : validation de tâches par forward de message
- **Gains** : réception automatique de TRX dans earn_balance
- **Retrait** : transfert vers portefeuille externe

### Système de Parrainage
- **Commission automatique** : 10% sur les gains, 5% sur les dépenses
- **1 niveau** : parrainage simplifié
- **Distribution** : paiement automatique en TRX

## Architecture Technique

### Stack Technologique
- **Backend** : Python avec python-telegram-bot
- **Base de données** : PostgreSQL avec SQLAlchemy
- **Blockchain** : TRON (TRX natif uniquement)
- **Chiffrement** : Cryptography pour les clés privées
- **Logging** : Loguru avec rotation automatique

### Structure du Projet
```
bot-marketplace/
├── bot/                    # Interface Telegram
├── services/              # Logique métier
├── models/                # Modèles de données
├── utils/                 # Utilitaires
├── logs/                  # Fichiers de log
├── requirements.txt       # Dépendances Python
├── .env.template         # Template variables d'environnement
└── README.md             # Documentation
```

## Installation

### Prérequis
- Python 3.8+
- PostgreSQL 12+
- Compte Telegram Bot (via @BotFather)
- Accès API TRON

### Configuration

1. **Cloner le projet**
   ```bash
   git clone <repository-url>
   cd bot-marketplace
   ```

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration environnement**
   ```bash
   cp .env.template .env
   # Éditer .env avec vos configurations
   ```

4. **Base de données**
   ```bash
   # Créer la base de données PostgreSQL
   createdb bot_marketplace
   
   # Lancer les migrations (à venir dans Phase 1 - Commit 2)
   # alembic upgrade head
   ```

## Variables d'Environnement

### Bot Telegram
- `TELEGRAM_BOT_TOKEN` : Token du bot Telegram
- `TELEGRAM_ADMIN_ID` : ID Telegram de l'administrateur
- `TELEGRAM_ADMIN_USERNAME` : Username de l'administrateur

### Base de Données
- `DATABASE_URL` : URL complète de connexion PostgreSQL
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` : Paramètres individuels

### TRON Network
- `TRON_NETWORK` : mainnet ou testnet
- `TRON_API_KEY` : Clé API pour les services TRON
- `TRON_PRIVATE_KEY` : Clé privée maître pour les transactions

### Sécurité
- `ENCRYPTION_KEY` : Clé de chiffrement 32 bytes pour les clés privées

### Configuration Business
- `MIN_DEPOSIT_TRX` : Montant minimum de dépôt (défaut: 1 TRX)
- `MIN_WITHDRAWAL_TRX` : Montant minimum de retrait (défaut: 1 TRX)
- `REFERRAL_COMMISSION_RATE` : Taux de commission parrainage (défaut: 0.10)
- `SPONSOR_COMMISSION_RATE` : Taux de commission sponsor (défaut: 0.05)

## Roadmap de Développement

### Phase 1: Infrastructure + Gestion des Campagnes (1 semaine)
- ✅ **Commit 1** : Setup initial du projet
- ⏳ **Commit 2** : Configuration base de données PostgreSQL
- ⏳ **Commit 3** : Modèles de données utilisateurs et campagnes
- ⏳ **Commit 4** : Bot Telegram de base
- ⏳ **Commit 5** : Service de gestion des campagnes
- ⏳ **Commit 6** : Interface bot pour gestion des campagnes

### Phase 2: Participation aux Campagnes + Validation (1 semaine)
- ⏳ Système de découverte des campagnes
- ⏳ Validation des forwards et liens
- ⏳ Paiement automatique des participants

### Phase 3: Parrainage + Intégration TRX (1 semaine)
- ⏳ Client TRON et gestion des portefeuilles
- ⏳ Surveillance des dépôts blockchain
- ⏳ Système de parrainage et commissions

### Phase 4: Tests + Optimisation + Déploiement (1 semaine)
- ⏳ Système de retraits
- ⏳ Tests d'intégration complets
- ⏳ Optimisation et sécurisation

## Métriques de Performance Cibles

- **Réponse bot** : < 2 secondes pour les commandes simples
- **Détection dépôts** : < 1 minute après confirmation blockchain
- **Validation participations** : < 30 secondes pour le processus complet
- **Uptime** : 99.9% de disponibilité

## Sécurité

- **Chiffrement** : Toutes les clés privées sont chiffrées en base
- **Validation** : Vérification obligatoire des forwards de message
- **Audit** : Logs complets de toutes les opérations critiques
- **Isolation** : Séparation des balances earn_balance et ad_balance

## Support

Pour toute question ou problème, consultez la documentation technique dans `devbook.md` ou le plan de développement dans `roadmap.md`.

## Licence

[À définir]
