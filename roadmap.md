# Roadmap GitFlow - Bot Telegram Marketplace de Campagnes

## Vue d'ensemble

Ce roadmap détaille le développement from scratch du bot Telegram marketplace de campagnes selon les spécifications du devbook.md. Le développement suit un workflow GitFlow classique avec des commits groupés par étape majeure de développement et spécifie exactement quels fichiers créer à chaque étape.

## Structure GitFlow

```
main (production)
├── develop (développement principal)
├── feature/phase-1-infrastructure (Phase 1)
├── feature/phase-2-participation (Phase 2)
├── feature/phase-3-parrainage-trx (Phase 3)
├── feature/phase-4-finalisation (Phase 4)
└── hotfix/* (corrections urgentes)
```

---

## Phase 1: Infrastructure + Gestion des Campagnes
**Branche:** `feature/phase-1-infrastructure`
**Durée estimée:** 1 semaine

### Objectifs
- Configuration de l'environnement et base de données
- Modèles de données et migrations
- Bot Telegram de base avec authentification
- CRUD des campagnes (création, recharge, pause/reprise)
- Interface bot pour gestion des campagnes

### Commits Suggérés

#### Commit 1: Setup initial du projet
```
feat: initialize marketplace project structure

Fichiers à créer:
├── marketplace_bot/
│   ├── main.py                 # Point d'entrée principal (vide pour l'instant)
│   ├── config.py              # Configuration et variables d'environnement
│   ├── requirements.txt       # Dépendances Python
│   ├── .env.template         # Template des variables d'environnement
│   ├── .gitignore            # Ignorer .env, __pycache__, etc.
│   ├── README.md             # Documentation du projet
│   └── database/
│       └── __init__.py       # Package database
```

#### Commit 2: Configuration base de données PostgreSQL
```
feat: setup PostgreSQL database foundation

Fichiers à créer:
├── database/
│   ├── database.py           # Configuration connexion PostgreSQL
│   ├── base.py              # Classes de base SQLAlchemy
│   └── migrations/
│       ├── __init__.py      # Package migrations
│       └── env.py           # Configuration Alembic
```

#### Commit 3: Modèles de données core (Users, Campaigns, Wallets)
```
feat: implement core data models

Fichiers à créer:
├── database/
│   ├── models.py            # Tous les modèles SQLAlchemy
│   └── migrations/versions/
│       └── 001_initial_models.py  # Migration initiale
```

Modèles à implémenter dans models.py:
- Users (id, telegram_id, username, referral_code, sponsor_id, earn_balance, ad_balance, total_earned, total_spent, created_at, updated_at)
- Campaigns (id, owner_id, title, bot_link, bot_username, amount_per_referral, balance, referral_count, is_active, created_at, updated_at)
- User_Wallets (id, user_id, address, private_key_encrypted, created_at)

#### Commit 4: Bot Telegram de base
```
feat: implement basic Telegram bot infrastructure

Fichiers à créer:
├── bot/
│   ├── __init__.py          # Package bot
│   ├── bot.py              # Initialisation du bot Telegram
│   ├── keyboards.py        # Claviers inline et reply
│   ├── utils.py           # Utilitaires bot (formatage, validation)
│   └── handlers/
│       ├── __init__.py     # Package handlers
│       ├── start.py        # Handler /start et inscription
│       └── common.py       # Handlers communs (/help, /cancel)
```

#### Commit 5: Service de gestion des campagnes
```
feat: implement campaign management service

Fichiers à créer:
├── services/
│   ├── __init__.py         # Package services
│   ├── campaign_service.py # Logique métier campagnes
│   └── user_service.py     # Logique métier utilisateurs
```

#### Commit 6: Interface bot pour gestion des campagnes
```
feat: add bot interface for campaign management

Fichiers à créer/modifier:
├── bot/handlers/
│   └── campaigns.py        # Handlers /create_campaign, /my_campaigns
└── main.py                # Point d'entrée avec démarrage du bot
```

---

## Phase 2: Participation aux Campagnes + Validation
**Branche:** `feature/phase-2-participation`
**Durée estimée:** 1 semaine

### Objectifs
- Interface de découverte des campagnes (/browse_bots)
- Système de validation des forwards
- Génération et traitement des liens de validation
- Logique de paiement des participants
- Gestion des reports de campagnes

### Commits Suggérés

#### Commit 1: Modèles de données pour participations et reports
```
feat: implement participation and reporting data models

Fichiers à créer/modifier:
├── database/
│   ├── models.py            # Ajouter nouveaux modèles
│   └── migrations/versions/
│       └── 002_participation_models.py  # Migration participations
```

Nouveaux modèles à ajouter dans models.py:
- Campaign_Participations (id, campaign_id, user_id, forward_message_id, validation_link, amount_earned, commission_paid, status, created_at, validated_at)
- Campaign_Reports (id, campaign_id, reporter_id, reason, description, status, created_at, reviewed_at)

#### Commit 2: Service de découverte et participation aux campagnes
```
feat: implement campaign discovery and participation service

Fichiers à créer:
├── services/
│   ├── participation_service.py  # Logique métier participations
│   └── validation_service.py     # Validation des forwards et liens
```

#### Commit 3: Interface bot pour découverte des campagnes
```
feat: add bot interface for campaign discovery

Fichiers à créer:
├── bot/handlers/
│   ├── participation.py     # Handler /browse_bots et participation
│   └── reports.py          # Handler reports de campagnes
```

#### Commit 4: Système de validation des participations
```
feat: implement participation validation system

Fichiers à créer:
├── utils/
│   ├── __init__.py         # Package utils
│   ├── validators.py       # Validateurs de données
│   └── link_generator.py   # Génération liens de validation
```

#### Commit 5: Système de paiement des participants
```
feat: implement participant payment system

Fichiers à créer:
├── services/
│   └── payment_service.py  # Logique de paiement et commissions
```

---

## Phase 3: Système de Parrainage + Intégration TRX
**Branche:** `feature/phase-3-parrainage-trx`
**Durée estimée:** 1 semaine

### Objectifs
- Implémentation du client TRON (développement from scratch)
- Génération automatique des portefeuilles TRON
- Système de surveillance des dépôts TRX
- Calcul et distribution automatique des commissions
- Interface de gestion des balances

### Commits Suggérés

#### Commit 1: Client TRON et gestion des portefeuilles
```
feat: implement TRON blockchain client from scratch

Fichiers à créer:
├── utils/
│   ├── tron_client.py      # Client TRON avec connexion réseau
│   └── crypto.py          # Chiffrement/déchiffrement AES-256
├── services/
│   └── wallet_service.py   # Génération et gestion des portefeuilles
```

#### Commit 2: Modèles de données pour blockchain et transactions
```
feat: implement blockchain and transaction data models

Fichiers à créer/modifier:
├── database/
│   ├── models.py           # Ajouter nouveaux modèles
│   └── migrations/versions/
│       └── 003_blockchain_models.py  # Migration blockchain
```

Nouveaux modèles à ajouter dans models.py:
- Deposits (id, user_id, wallet_id, tx_hash, amount_trx, confirmations, status, created_at, confirmed_at)
- Withdrawals (id, user_id, amount_trx, to_address, tx_hash, status, created_at, processed_at)
- Referral_Commissions (id, user_id, referred_user_id, participation_id, deposit_id, type, amount_trx, percentage, created_at)
- Transactions (id, user_id, type, amount_trx, balance_type, reference_id, description, created_at)

#### Commit 3: Système de surveillance des dépôts TRON
```
feat: implement TRON deposit monitoring system

Fichiers à créer:
├── services/
│   └── blockchain_monitor.py  # Surveillance blockchain TRON
├── workers/
│   ├── __init__.py         # Package workers
│   └── deposit_monitor.py  # Worker surveillance dépôts
```

#### Commit 4: Système de parrainage simplifié (1 niveau)
```
feat: implement simplified referral system

Fichiers à créer:
├── services/
│   └── referral_service.py # Calcul et distribution des commissions
├── bot/handlers/
│   └── referral.py        # Handler codes de parrainage
```

#### Commit 5: Interface bot pour gestion des balances TRX
```
feat: add bot interface for TRX balance management

Fichiers à créer:
├── bot/handlers/
│   └── wallet.py          # Handlers /balance, /deposit, /withdraw
```

---

## Phase 4: Tests + Optimisation + Déploiement
**Branche:** `feature/phase-4-finalisation`
**Durée estimée:** 1 semaine

### Objectifs
- Système de retraits avec validation des limites
- Tests complets de tous les flux
- Optimisation des performances
- Sécurisation et chiffrement des données sensibles
- Documentation et déploiement

### Commits Suggérés

#### Commit 1: Système de retraits TRX
```
feat: implement TRX withdrawal system

Fichiers à créer:
├── services/
│   └── withdrawal_service.py  # Logique de retrait TRX
├── workers/
│   └── withdrawal_processor.py # Worker traitement retraits
```

#### Commit 2: Tests complets et validation
```
test: implement comprehensive testing suite

Fichiers à créer:
├── tests/
│   ├── __init__.py         # Package tests
│   ├── conftest.py        # Configuration pytest
│   ├── test_models.py     # Tests modèles de données
│   ├── test_services.py   # Tests services métier
│   ├── test_bot_handlers.py # Tests handlers bot
│   ├── test_blockchain.py # Tests intégration blockchain
│   └── test_flows.py      # Tests flux end-to-end
├── pytest.ini            # Configuration pytest
```

#### Commit 3: Optimisation et sécurisation
```
perf: optimize performance and enhance security

Fichiers à créer/modifier:
├── database/
│   └── migrations/versions/
│       └── 004_add_indexes.py  # Migration indexes performance
├── utils/
│   ├── cache.py           # Système de cache Redis/Memory
│   └── rate_limiter.py    # Rate limiting et anti-abuse
├── config.py              # Amélioration configuration sécurité
```

#### Commit 4: Documentation et déploiement
```
docs: complete documentation and deployment setup

Fichiers à créer:
├── docs/
│   ├── README.md          # Documentation complète
│   ├── API.md            # Documentation API
│   ├── DEPLOYMENT.md     # Guide de déploiement
│   └── TROUBLESHOOTING.md # Guide de dépannage
├── docker/
│   ├── Dockerfile        # Image Docker
│   ├── docker-compose.yml # Orchestration services
│   └── .dockerignore     # Fichiers à ignorer
├── scripts/
│   ├── setup.sh          # Script d'installation
│   ├── backup.sh         # Script de sauvegarde DB
│   └── deploy.sh         # Script de déploiement
```

#### Commit 5: Monitoring et logging avancé
```
feat: implement advanced monitoring and logging

Fichiers à créer:
├── utils/
│   ├── logger.py         # Configuration logging avancé
│   └── metrics.py        # Métriques de performance
├── monitoring/
│   ├── __init__.py       # Package monitoring
│   ├── health_check.py   # Health check endpoints
│   └── alerts.py         # Système d'alertes
```

---

## Workflow GitFlow

### Processus de Développement

1. **Initialisation du projet**
   ```bash
   git init
   git checkout -b main
   git checkout -b develop
   ```

2. **Création de feature branch par phase**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/phase-1-infrastructure
   ```

3. **Développement et commits par étape majeure**
   ```bash
   git add .
   git commit -m "feat: initialize marketplace project from scratch"
   git push origin feature/phase-1-infrastructure
   ```

4. **Merge vers develop à la fin de chaque phase**
   ```bash
   git checkout develop
   git merge feature/phase-1-infrastructure
   git push origin develop
   ```

5. **Release vers main après toutes les phases**
   ```bash
   git checkout main
   git merge develop
   git tag v1.0.0
   git push origin main --tags
   ```

### Convention de Nommage des Commits

- `feat:` Nouvelle fonctionnalité
- `fix:` Correction de bug
- `perf:` Amélioration des performances
- `docs:` Documentation
- `refactor:` Refactoring de code
- `test:` Ajout de tests

---

## Structure Finale du Projet

### Arborescence Complète
```
marketplace_bot/
├── main.py                     # Point d'entrée principal
├── config.py                   # Configuration et variables d'environnement
├── requirements.txt            # Dépendances Python
├── .env.template              # Template variables d'environnement
├── .gitignore                 # Fichiers à ignorer Git
├── README.md                  # Documentation du projet
├── pytest.ini                # Configuration pytest
│
├── database/                  # Package base de données
│   ├── __init__.py
│   ├── database.py           # Configuration connexion PostgreSQL
│   ├── base.py              # Classes de base SQLAlchemy
│   ├── models.py            # Tous les modèles SQLAlchemy
│   └── migrations/          # Scripts de migration Alembic
│       ├── __init__.py
│       ├── env.py           # Configuration Alembic
│       └── versions/
│           ├── 001_initial_models.py
│           ├── 002_participation_models.py
│           ├── 003_blockchain_models.py
│           └── 004_add_indexes.py
│
├── bot/                      # Package bot Telegram
│   ├── __init__.py
│   ├── bot.py               # Initialisation du bot Telegram
│   ├── keyboards.py         # Claviers inline et reply
│   ├── utils.py            # Utilitaires bot
│   └── handlers/           # Handlers des commandes
│       ├── __init__.py
│       ├── start.py        # Handler /start et inscription
│       ├── common.py       # Handlers communs (/help, /cancel)
│       ├── campaigns.py    # Handlers /create_campaign, /my_campaigns
│       ├── participation.py # Handler /browse_bots et participation
│       ├── reports.py      # Handler reports de campagnes
│       ├── referral.py     # Handler codes de parrainage
│       └── wallet.py       # Handlers /balance, /deposit, /withdraw
│
├── services/                 # Services métier
│   ├── __init__.py
│   ├── user_service.py      # Logique métier utilisateurs
│   ├── campaign_service.py  # Logique métier campagnes
│   ├── participation_service.py # Logique métier participations
│   ├── validation_service.py # Validation des forwards et liens
│   ├── payment_service.py   # Logique de paiement et commissions
│   ├── wallet_service.py    # Génération et gestion des portefeuilles
│   ├── blockchain_monitor.py # Surveillance blockchain TRON
│   ├── referral_service.py  # Calcul et distribution des commissions
│   └── withdrawal_service.py # Logique de retrait TRX
│
├── workers/                  # Workers asynchrones
│   ├── __init__.py
│   ├── deposit_monitor.py   # Worker surveillance dépôts
│   └── withdrawal_processor.py # Worker traitement retraits
│
├── utils/                    # Utilitaires généraux
│   ├── __init__.py
│   ├── validators.py        # Validateurs de données
│   ├── link_generator.py    # Génération liens de validation
│   ├── tron_client.py       # Client TRON avec connexion réseau
│   ├── crypto.py           # Chiffrement/déchiffrement AES-256
│   ├── cache.py            # Système de cache Redis/Memory
│   ├── rate_limiter.py     # Rate limiting et anti-abuse
│   ├── logger.py           # Configuration logging avancé
│   └── metrics.py          # Métriques de performance
│
├── monitoring/               # Monitoring et alertes
│   ├── __init__.py
│   ├── health_check.py     # Health check endpoints
│   └── alerts.py           # Système d'alertes
│
├── tests/                    # Tests unitaires et d'intégration
│   ├── __init__.py
│   ├── conftest.py         # Configuration pytest
│   ├── test_models.py      # Tests modèles de données
│   ├── test_services.py    # Tests services métier
│   ├── test_bot_handlers.py # Tests handlers bot
│   ├── test_blockchain.py  # Tests intégration blockchain
│   └── test_flows.py       # Tests flux end-to-end
│
├── docs/                     # Documentation
│   ├── README.md           # Documentation complète
│   ├── API.md             # Documentation API
│   ├── DEPLOYMENT.md      # Guide de déploiement
│   └── TROUBLESHOOTING.md # Guide de dépannage
│
├── docker/                   # Configuration Docker
│   ├── Dockerfile         # Image Docker
│   ├── docker-compose.yml # Orchestration services
│   └── .dockerignore      # Fichiers à ignorer
│
└── scripts/                  # Scripts utilitaires
    ├── setup.sh            # Script d'installation
    ├── backup.sh           # Script de sauvegarde DB
    └── deploy.sh           # Script de déploiement
```

## Validation et Tests par Phase

### Phase 1: Tests d'infrastructure
- ✅ Configuration base de données PostgreSQL
- ✅ Modèles de données (Users, Campaigns, User_Wallets)
- ✅ Bot Telegram de base (/start, /help)
- ✅ Interface de gestion des campagnes (/create_campaign, /my_campaigns)

### Phase 2: Tests de participation
- ✅ Découverte des campagnes (/browse_bots)
- ✅ Modèles Campaign_Participations et Campaign_Reports
- ✅ Système de validation des forwards
- ✅ Génération et traitement des liens de validation
- ✅ Paiement automatique des participants

### Phase 3: Tests TRX et parrainage
- ✅ Client TRON et génération de portefeuilles
- ✅ Modèles Deposits, Withdrawals, Referral_Commissions, Transactions
- ✅ Surveillance des dépôts blockchain
- ✅ Système de parrainage à 1 niveau
- ✅ Gestion des balances (earn_balance, ad_balance)

### Phase 4: Tests finaux
- ✅ Système de retraits TRX
- ✅ Tests d'intégration complets
- ✅ Optimisation des performances et sécurité
- ✅ Documentation et déploiement

---

## Métriques de Performance Cibles

### Objectifs Techniques
- **Réponse bot** : < 2 secondes pour les commandes simples
- **Détection dépôts** : < 1 minute après confirmation blockchain
- **Validation participations** : < 30 secondes pour le processus complet
- **Uptime** : 99.9% de disponibilité

### Métriques Métier
- Nombre de campagnes créées par jour
- Taux de participation aux campagnes
- Volume de TRX traité (dépôts/retraits)
- Nombre d'utilisateurs actifs
- Efficacité du système de parrainage

---

## Notes de Développement

### Spécificités du Projet From Scratch
- **Développement complet** : Aucune réutilisation de code existant
- **Architecture moderne** : Structure modulaire et maintenable
- **Sécurité prioritaire** : Chiffrement des clés privées dès le début
- **Scalabilité** : Conception pour la montée en charge

### Technologies Principales
- **Backend** : Python avec python-telegram-bot
- **Base de données** : PostgreSQL avec migrations
- **Blockchain** : Client TRON custom
- **Chiffrement** : Cryptographie pour les clés privées
- **Monitoring** : Logging et métriques intégrés

---

## Résumé des Fichiers par Commit

### Phase 1 - Infrastructure (6 commits)
**Total: 17 fichiers**
- Commit 1 (7 fichiers): Structure projet + config
- Commit 2 (4 fichiers): Base de données PostgreSQL
- Commit 3 (2 fichiers): Modèles core + migration
- Commit 4 (6 fichiers): Bot Telegram de base
- Commit 5 (3 fichiers): Services campagnes/utilisateurs
- Commit 6 (2 fichiers): Interface bot campagnes

### Phase 2 - Participation (5 commits)  
**Total: 8 fichiers**
- Commit 1 (2 fichiers): Modèles participations/reports + migration
- Commit 2 (2 fichiers): Services participation/validation
- Commit 3 (2 fichiers): Interface bot découverte/reports
- Commit 4 (3 fichiers): Système validation + utils
- Commit 5 (1 fichier): Service paiement

### Phase 3 - TRX & Parrainage (5 commits)
**Total: 9 fichiers**
- Commit 1 (3 fichiers): Client TRON + crypto + wallet service
- Commit 2 (2 fichiers): Modèles blockchain + migration
- Commit 3 (3 fichiers): Surveillance dépôts + worker
- Commit 4 (2 fichiers): Service parrainage + handler
- Commit 5 (1 fichier): Interface wallet

### Phase 4 - Finalisation (5 commits)
**Total: 25 fichiers**
- Commit 1 (2 fichiers): Service retraits + worker
- Commit 2 (8 fichiers): Tests complets + configuration
- Commit 3 (4 fichiers): Optimisation + sécurité
- Commit 4 (10 fichiers): Documentation + déploiement
- Commit 5 (5 fichiers): Monitoring + logging

### Total Final: 59 fichiers organisés en 21 commits

---

## Points Clés pour le Développement

### Dépendances Principales (requirements.txt)
```
python-telegram-bot==20.7
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
cryptography==41.0.8
requests==2.31.0
python-dotenv==1.0.0
pytest==7.4.3
redis==5.0.1
```

### Variables d'Environnement Essentielles (.env.template)
```
# Bot Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ADMIN_ID=your_admin_id

# Base de données
DATABASE_URL=postgresql://user:password@localhost:5432/marketplace_bot

# TRON
TRON_API_KEY=your_tron_api_key
TRON_NETWORK=mainnet
TRON_PRIVATE_KEY=your_main_wallet_private_key

# Sécurité
ENCRYPTION_KEY=your_encryption_key_32_bytes

# Configuration métier
REFERRAL_COMMISSION_RATE=0.10
DEPOSIT_COMMISSION_RATE=0.05
```

Cette roadmap GitFlow assure un développement structuré et méthodique du bot marketplace de campagnes avec une approche from scratch, garantissant la qualité et la maintenabilité du code. Chaque commit est précisément défini avec les fichiers à créer, facilitant le suivi et l'implémentation progressive.
