# Devbook: Bot Telegram Marketplace de Campagnes MVP - TRON Only

## 1. Introduction

Ce document décrit l'architecture et les spécifications pour développer un bot Telegram de marketplace de campagnes permettant aux annonceurs de créer des campagnes de parrainage et aux participants de gagner des TRX en validant des tâches. Le système intègre un mécanisme de parrainage à 1 niveau et utilise exclusivement la blockchain TRON.

## 2. Objectifs du MVP

### 2.1 Fonctionnalités Principales
- **Gestion des campagnes** : création, recharge, pause/reprise par les annonceurs
- **Participation aux campagnes** : découverte et validation de tâches par les participants
- **Système de parrainage** : commissions automatiques (10% gains, 5% dépenses) en TRX
- **Intégration wallet TRX** : dépôts/retraits automatiques avec adresses individuelles
- **Gestion des balances** : earn_balance et ad_balance séparées
- **Interface Telegram** : bot complet pour toutes les opérations

### 2.2 Cryptomonnaie Supportée
- **TRX** : TRON natif uniquement

## 3. Architecture Simplifiée

### 3.1 Structure Monolithique
L'application est un service Python unique intégrant :
- **Bot Telegram** : interface utilisateur principale
- **Gestionnaire de campagnes** : CRUD et validation des campagnes
- **Système de validation** : vérification des forwards et liens de parrainage
- **Gestionnaire de portefeuilles** : génération et gestion des adresses TRON
- **Moniteur blockchain** : surveillance des dépôts sur TRON
- **Système de parrainage** : calcul et distribution des commissions
- **Gestionnaire de retraits** : traitement des demandes de retrait

### 3.2 Base de Données
PostgreSQL comme unique source de données pour :
- Utilisateurs et authentification
- Campagnes et leur statut
- Participations et validations
- Portefeuilles et transactions
- Système de parrainage
- Historique des opérations

## 4. Modèle de Données

### 4.1 Utilisateurs
```
Users
- id (Primary Key)
- telegram_id (Unique)
- username
- referral_code (Unique, généré automatiquement)
- sponsor_id (Foreign Key -> Users.id, nullable)
- earn_balance (Decimal, TRX gagné via participations)
- ad_balance (Decimal, TRX pour financer campagnes)
- total_earned (Decimal, TRX total gagné)
- total_spent (Decimal, TRX total dépensé en campagnes)
- created_at (Timestamp)
- updated_at (Timestamp)
```

### 4.2 Campagnes
```
Campaigns
- id (Primary Key)
- owner_id (Foreign Key -> Users.id)
- title (String, titre de la campagne)
- bot_link (String, lien de parrainage du bot cible)
- bot_username (String, nom d'utilisateur du bot cible)
- amount_per_referral (Decimal, montant fixe par validation en TRX)
- balance (Decimal, solde disponible de la campagne en TRX)
- referral_count (Integer, nombre de validations effectuées)
- is_active (Boolean, statut actif/inactif)
- created_at (Timestamp)
- updated_at (Timestamp)
```

### 4.3 Participations aux Campagnes
```
Campaign_Participations
- id (Primary Key)
- campaign_id (Foreign Key -> Campaigns.id)
- user_id (Foreign Key -> Users.id)
- forward_message_id (String, ID du message forwardé)
- validation_link (String, lien de validation généré)
- amount_earned (Decimal, montant gagné en TRX)
- commission_paid (Decimal, commission versée au parrain en TRX)
- status (Enum: 'pending', 'validated', 'failed')
- created_at (Timestamp)
- validated_at (Timestamp, nullable)
```

### 4.4 Portefeuilles Utilisateurs
```
User_Wallets
- id (Primary Key)
- user_id (Foreign Key -> Users.id)
- address (String, adresse TRON publique)
- private_key_encrypted (String, clé privée chiffrée)
- created_at (Timestamp)
```

### 4.5 Dépôts
```
Deposits
- id (Primary Key)
- user_id (Foreign Key -> Users.id)
- wallet_id (Foreign Key -> User_Wallets.id)
- tx_hash (String, hash de transaction)
- amount_trx (Decimal, montant en TRX)
- confirmations (Integer, nombre de confirmations)
- status (Enum: 'pending', 'confirmed', 'failed')
- created_at (Timestamp)
- confirmed_at (Timestamp, nullable)
```

### 4.6 Retraits
```
Withdrawals
- id (Primary Key)
- user_id (Foreign Key -> Users.id)
- amount_trx (Decimal, montant en TRX)
- to_address (String, adresse de destination TRON)
- tx_hash (String, hash de transaction, nullable)
- status (Enum: 'pending', 'processing', 'completed', 'failed')
- created_at (Timestamp)
- processed_at (Timestamp, nullable)
```

### 4.7 Commissions de Parrainage
```
Referral_Commissions
- id (Primary Key)
- user_id (Foreign Key -> Users.id, bénéficiaire)
- referred_user_id (Foreign Key -> Users.id, celui qui génère la commission)
- participation_id (Foreign Key -> Campaign_Participations.id, nullable)
- deposit_id (Foreign Key -> Deposits.id, nullable)
- type (Enum: 'task_completion', 'deposit')
- amount_trx (Decimal, montant de la commission en TRX)
- percentage (Decimal, pourcentage appliqué)
- created_at (Timestamp)
```

### 4.8 Historique des Transactions
```
Transactions
- id (Primary Key)
- user_id (Foreign Key -> Users.id)
- type (Enum: 'deposit', 'withdrawal', 'task_reward', 'campaign_spend', 'referral_commission')
- amount_trx (Decimal, montant en TRX)
- balance_type (Enum: 'earn_balance', 'ad_balance')
- reference_id (String, ID de référence selon le type)
- description (String, description de la transaction)
- created_at (Timestamp)
```

### 4.9 Reports de Campagnes
```
Campaign_Reports
- id (Primary Key)
- campaign_id (Foreign Key -> Campaigns.id)
- reporter_id (Foreign Key -> Users.id)
- reason (Enum: 'bot_inactive', 'spam', 'dead_link', 'other')
- description (Text, description du problème)
- status (Enum: 'pending', 'reviewed', 'resolved')
- created_at (Timestamp)
- reviewed_at (Timestamp, nullable)
```

## 5. Flux Fonctionnels

### 5.1 Flux d'Inscription
1. **Commande /start** : Vérification du code de parrainage optionnel
2. **Création utilisateur** : Génération du referral_code unique
3. **Liaison parrainage** : Association avec le parrain si code fourni
4. **Génération portefeuille** : Création automatique d'une adresse TRON
5. **Message de bienvenue** : Instructions et présentation des fonctionnalités

### 5.2 Flux de Création de Campagne
1. **Commande /create_campaign** : Démarrage du processus
2. **Saisie lien bot** : Validation du format du lien de parrainage
3. **Vérification bot** : Forward d'un message récent pour validation
4. **Configuration** : Titre et montant par referral
5. **Création** : Campagne initialisée avec balance = 0, is_active = true

### 5.3 Flux de Dépôt
1. **Commande /deposit** : Affichage de l'adresse de dépôt TRON
2. **Affichage adresse** : Présentation de l'adresse avec QR code
3. **Surveillance** : Monitoring automatique des transactions TRX entrantes
4. **Confirmation** : Validation après 19 confirmations sur TRON
5. **Crédit** : Ajout du montant TRX à l'ad_balance
6. **Commission parrain** : Versement de 5% au parrain si applicable

### 5.4 Flux de Participation à une Campagne
1. **Commande /browse_bots** : Affichage des campagnes actives
2. **Sélection campagne** : Boutons [Message Bot] [Skip] [Report]
3. **Action "Message Bot"** : Demande de forward d'un message récent
4. **Validation forward** : Vérification de forward_from.id
5. **Génération lien** : Création du lien de validation unique
6. **Validation** : Clic sur le lien et traitement automatique
7. **Paiement** : Distribution des TRX (participant + commission parrain)

### 5.5 Flux de Retrait
1. **Commande /withdraw** : Saisie du montant TRX à retirer
2. **Saisie montant** : Validation du montant disponible dans earn_balance
3. **Saisie adresse** : Validation du format d'adresse TRON
4. **Vérification** : Contrôle des limites et du solde
5. **Création transaction** : Génération de la transaction TRON
6. **Traitement** : Envoi sur la blockchain et mise à jour du statut

## 6. Règles Métier

### 6.1 Gestion des Campagnes
- **Balance minimum** : Campagne automatiquement désactivée si balance < amount_per_referral
- **Recharge** : Débit de l'ad_balance pour créditer la campagne
- **Limite** : Un utilisateur ne peut participer qu'une fois par campagne

### 6.2 Système de Parrainage
- **Commission tâches** : 10% des gains du filleul versés au parrain
- **Commission dépôts** : 5% des dépôts du filleul versés au parrain
- **Niveau unique** : Système à 1 niveau (parrain direct uniquement)

### 6.3 Surveillance Blockchain
- **Méthode** : Polling périodique des adresses utilisateurs TRON
- **Réseau** : Worker pour blockchain TRON uniquement
- **Confirmations** : Attente de 19 confirmations sur TRON
- **Notification** : Alerte utilisateur en temps réel

### 6.4 Gestion des Retraits
- **Source** : Uniquement depuis earn_balance
- **Limite** : Pas de limite journalière (contrairement au devbook TRON)
- **Traitement** : Automatique via smart contract ou transaction directe

## 7. Configuration Technique

### 7.1 Variables d'Environnement
```
# Bot Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ADMIN_ID=your_admin_id
TELEGRAM_ADMIN_USERNAME=your_admin_username

# Base de données
DATABASE_URL=postgresql://user:password@localhost:5432/marketplace_bot

# TRON
TRON_API_KEY=your_tron_api_key
TRON_NETWORK=mainnet
TRON_PRIVATE_KEY=your_main_wallet_private_key

# Sécurité
ENCRYPTION_KEY=your_encryption_key_32_bytes

# Configuration métier
AMOUNT_PER_REFERRAL=10.0
REFERRAL_COMMISSION_RATE=0.10
DEPOSIT_COMMISSION_RATE=0.05
```

### 7.2 Structure du Projet
```
marketplace_bot/
├── main.py                 # Point d'entrée principal
├── config.py              # Configuration et variables d'environnement
├── database/
│   ├── models.py          # Modèles SQLAlchemy
│   ├── database.py        # Configuration base de données
│   └── migrations/        # Scripts de migration
├── bot/
│   ├── handlers/          # Handlers des commandes Telegram
│   │   ├── campaigns.py   # Gestion des campagnes
│   │   ├── participation.py # Participation aux campagnes
│   │   ├── wallet.py      # Gestion des portefeuilles
│   │   └── referral.py    # Système de parrainage
│   ├── keyboards.py       # Claviers inline Telegram
│   └── utils.py          # Utilitaires bot
├── services/
│   ├── campaign_service.py # Logique métier campagnes
│   ├── wallet_service.py   # Gestion des portefeuilles TRON
│   ├── blockchain_monitor.py # Surveillance blockchain
│   └── referral_service.py # Calcul des commissions
├── workers/
│   ├── deposit_monitor.py  # Worker surveillance dépôts
│   └── withdrawal_processor.py # Worker traitement retraits
└── utils/
    ├── crypto.py          # Chiffrement/déchiffrement
    ├── tron_client.py     # Client TRON
    └── validators.py      # Validateurs de données
```

## 8. Sécurité

### 8.1 Protection des Clés Privées
- **Chiffrement** : AES-256 avec clé maître
- **Stockage** : Clés privées jamais en clair en base
- **Accès** : Déchiffrement uniquement lors des retraits
- **Rotation** : Génération de nouvelles adresses périodiquement

### 8.2 Validation des Données
- **Adresses** : Vérification du format TRON
- **Montants** : Validation des limites et format décimal TRX
- **Forwards** : Vérification de l'authenticité via forward_from.id
- **Liens** : Validation des liens de parrainage

### 8.3 Prévention des Abus
- **Unicité** : Un utilisateur ne peut participer qu'une fois par campagne
- **Validation** : Vérification obligatoire du forward de message
- **Reports** : Système de signalement des campagnes problématiques

## 9. Plan de Développement

### 9.1 Phase 1 : Infrastructure + Gestion des Campagnes (1 semaine)
- Configuration de l'environnement et base de données
- Modèles de données et migrations
- Bot Telegram de base avec authentification
- CRUD des campagnes (création, recharge, pause/reprise)
- Interface bot pour gestion des campagnes

### 9.2 Phase 2 : Participation aux Campagnes + Validation (1 semaine)
- Interface de découverte des campagnes (/browse_bots)
- Système de validation des forwards
- Génération et traitement des liens de validation
- Logique de paiement des participants
- Gestion des reports de campagnes

### 9.3 Phase 3 : Système de Parrainage + Intégration TRX (1 semaine)
- Implémentation du client TRON (réutilisation du code existant)
- Génération automatique des portefeuilles TRON
- Système de surveillance des dépôts TRX
- Calcul et distribution automatique des commissions
- Interface de gestion des balances

### 9.4 Phase 4 : Tests + Optimisation + Déploiement (1 semaine)
- Système de retraits avec validation des limites
- Tests complets de tous les flux
- Optimisation des performances
- Sécurisation et chiffrement des données sensibles
- Documentation et déploiement

## 10. Gestion des Erreurs

### 10.1 Erreurs Blockchain
- **Timeout** : Retry automatique avec backoff exponentiel
- **Nœud TRON indisponible** : Basculement vers nœud de secours
- **Transaction échouée** : Notification utilisateur et rollback
- **Confirmations insuffisantes** : Attente et re-vérification

### 10.2 Erreurs Utilisateur
- **Solde TRX insuffisant** : Message d'erreur explicite avec solde actuel
- **Campagne inactive** : Redirection vers campagnes disponibles
- **Adresse TRON invalide** : Validation et suggestion de correction
- **Participation déjà effectuée** : Information et redirection

### 10.3 Erreurs Système
- **Base de données** : Retry avec circuit breaker
- **API TRON** : Fallback et cache des données
- **Bot Telegram** : Reconnexion automatique
- **Validation** : Logs d'audit et vérifications multiples

## 11. Métriques de Performance

### 11.1 Objectifs de Performance
- **Réponse bot** : < 2 secondes pour les commandes simples
- **Détection dépôts** : < 1 minute après confirmation blockchain
- **Traitement retraits** : < 5 minutes pour les retraits standard
- **Validation participations** : < 30 secondes pour le processus complet

### 11.2 Disponibilité
- **Uptime** : 99.9% de disponibilité cible
- **Récupération** : Redémarrage automatique en cas d'erreur
- **Monitoring** : Vérification continue des services critiques
- **Alertes** : Notification immédiate des dysfonctionnements

## 12. Cas d'Usage Principaux

### 12.1 Annonceur (Créateur de Campagne)
1. Inscription avec code de parrainage optionnel
2. Dépôt de TRX vers son ad_balance
3. Création d'une campagne avec lien de bot
4. Recharge périodique de la campagne
5. Suivi des performances et statistiques
6. Retrait des gains vers son portefeuille externe

### 12.2 Participant
1. Inscription avec code de parrainage
2. Découverte des campagnes disponibles
3. Participation via forward de message
4. Validation et réception des TRX
5. Accumulation dans earn_balance
6. Retrait vers portefeuille externe

### 12.3 Parrain
1. Génération de liens de parrainage
2. Invitation de filleuls
3. Réception automatique des commissions
4. Suivi des performances de parrainage
5. Optimisation de la stratégie de recrutement

## 13. Validation et Tests

### 13.1 Tests Unitaires
- Validation des modèles de données
- Test des services métier
- Vérification des calculs de commissions
- Test du client TRON

### 13.2 Tests d'Intégration
- Flux complet de création de campagne
- Processus de participation end-to-end
- Cycle de dépôt et retrait
- Système de parrainage complet

### 13.3 Tests de Sécurité
- Chiffrement/déchiffrement des clés
- Validation des adresses TRON
- Prévention des participations multiples
- Validation des forwards authentiques

## 14. Migration depuis le Projet TRON

### 14.1 Composants Réutilisables
- **Client TRON** : Réutilisation directe du code existant
- **Gestion des portefeuilles** : Adaptation des modèles existants
- **Surveillance blockchain** : Modification pour les nouveaux besoins
- **Système de chiffrement** : Réutilisation complète

### 14.2 Adaptations Nécessaires
- **Modèles de données** : Nouveaux modèles pour campagnes et participations
- **Logique métier** : Remplacement des investissements par les campagnes
- **Interface bot** : Nouveaux handlers pour les fonctionnalités marketplace
- **Système de parrainage** : Simplification à 1 niveau

Cette documentation fournit une base complète pour le développement d'un bot Telegram de marketplace de campagnes MVP basé sur l'architecture TRON existante. L'approche de réutilisation du code existant permettra un développement accéléré tout en maintenant la robustesse et la sécurité du système.
