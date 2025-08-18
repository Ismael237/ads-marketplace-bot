# Telegram Bot Campaign Marketplace MVP - TRON Only

## Description

A Telegram bot marketplace for campaigns that allows advertisers to create referral campaigns and participants to earn TRX by completing task validations. The system integrates a 1-level referral mechanism and exclusively uses the TRON blockchain.

## Key Features

### For Advertisers
- **Campaign Management**: creation, recharge, pause/resume
- **Funding**: TRX deposits to ad_balance
- **Tracking**: campaign statistics and performance monitoring
- **Control**: active/inactive status management

### For Participants
- **Discovery**: browse available campaigns via /browse_bots
- **Participation**: task validation through message forwarding
- **Earnings**: automatic TRX reception in earn_balance
- **Withdrawal**: transfer to external wallet

### Referral System
- **Automatic Commission**: 10% on earnings, 5% on expenses
- **1 Level**: simplified referral structure
- **Distribution**: automatic TRX payments

## Technical Architecture

### Technology Stack
- **Backend**: Python with python-telegram-bot
- **Database**: PostgreSQL with SQLAlchemy
- **Blockchain**: TRON (native TRX only)
- **Encryption**: Cryptography for private keys
- **Logging**: Loguru with automatic rotation

### Project Structure
```
bot-marketplace/
├── bot/                    # Telegram Interface
├── services/              # Business Logic
├── models/                # Data Models
├── utils/                 # Utilities
├── logs/                  # Log Files
├── requirements.txt       # Python Dependencies
├── .env.template         # Environment Variables Template
└── README.md             # Documentation
```

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Telegram Bot Account (via @BotFather)
- TRON API Access

### Setup

1. **Clone the project**
   ```bash
   git clone <repository-url>
   cd bot-marketplace
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment configuration**
   ```bash
   cp .env.template .env
   # Edit .env with your configurations
   ```

4. **Database setup**
   ```bash
   # Create PostgreSQL database
   createdb bot_marketplace
   
   # Run migrations (coming in Phase 1 - Commit 2)
   # alembic upgrade head
   ```

## Environment Variables

### Telegram Bot
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_ADMIN_ID`: Administrator's Telegram ID
- `TELEGRAM_ADMIN_USERNAME`: Administrator's username

### Database
- `DATABASE_URL`: Complete PostgreSQL connection URL
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Individual parameters

### TRON Network
- `TRON_NETWORK`: mainnet or testnet
- `TRON_API_KEY`: API key for TRON services
- `TRON_PRIVATE_KEY`: Master private key for transactions

### Security
- `ENCRYPTION_KEY`: 32-byte encryption key for private keys

### Business Configuration
- `MIN_DEPOSIT_TRX`: Minimum deposit amount (default: 1 TRX)
- `MIN_WITHDRAWAL_TRX`: Minimum withdrawal amount (default: 1 TRX)
- `REFERRAL_COMMISSION_RATE`: Referral commission rate (default: 0.10)
- `SPONSOR_COMMISSION_RATE`: Sponsor commission rate (default: 0.05)

## Development Roadmap

### Phase 1: Infrastructure + Campaign Management (1 week)
- ✅ **Commit 1**: Initial project setup
- ⏳ **Commit 2**: PostgreSQL database configuration
- ⏳ **Commit 3**: User and campaign data models
- ⏳ **Commit 4**: Basic Telegram bot
- ⏳ **Commit 5**: Campaign management service
- ⏳ **Commit 6**: Bot interface for campaign management

### Phase 2: Campaign Participation + Validation (1 week)
- ⏳ Campaign discovery system
- ⏳ Forward and link validation
- ⏳ Automatic participant payments

### Phase 3: Referral System + TRX Integration (1 week)
- ⏳ TRON client and wallet management
- ⏳ Blockchain deposit monitoring
- ⏳ Referral system and commissions

### Phase 4: Testing + Optimization + Deployment (1 week)
- ⏳ Withdrawal system
- ⏳ Complete integration testing
- ⏳ Optimization and security hardening

## Target Performance Metrics

- **Bot Response**: < 2 seconds for simple commands
- **Deposit Detection**: < 1 minute after blockchain confirmation
- **Participation Validation**: < 30 seconds for complete process
- **Uptime**: 99.9% availability

## Security

- **Encryption**: All private keys are encrypted in database
- **Validation**: Mandatory verification of message forwards
- **Audit**: Complete logs of all critical operations
- **Isolation**: Separation of earn_balance and ad_balance

## Version

- Current version: 1.0.2
- Release type: Minor

## Changelog

### 1.0.2 — Minor

• Feature: Earn-to-Ads Internal Transfer (integer-only, min 1 TRX, presets, MAX)
• UX: Confirmation shows amount, 0.5% fee, net, and irreversibility note
• Wallet Service: apply fee and credit net to ads, return updated balances
• History: new filter "Transfers Only" with 🔁 emoji
• Config: add TRANSFER_FEE_RATE, MIN_TRANSFER_TRX, TRANSFER_INTEGER_ONLY
• Migration: extend TransactionType enum with `internal_transfer`

Upgrade steps:
1. Ensure new env vars exist (see `.env.template`).
2. Apply DB migration: `alembic upgrade head`.
3. Restart the bot.

## Support

For any questions or issues, consult the technical documentation in `devbook.md` or the development plan in `roadmap.md`.

## License

[To be defined]
