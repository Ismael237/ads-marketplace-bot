"""
Configuration module for Bot Marketplace
Handles environment variables and application settings
"""
import os
from dotenv import load_dotenv
from os.path import join, dirname

# Load environment variables
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path, override=True)

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_ADMIN_ID = os.getenv('TELEGRAM_ADMIN_ID')
TELEGRAM_ADMIN_USERNAME = os.getenv('TELEGRAM_ADMIN_USERNAME')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost:5432/bot_marketplace')

# TRON Network Configuration
TRON_API_URL = os.getenv('TRON_API_URL', 'https://api.trongrid.io')
TRON_PRIVATE_KEY = os.getenv('TRON_PRIVATE_KEY')
TRON_EXPLORER_URL = os.getenv('TRON_EXPLORER_URL', 'https://tronscan.org')

# Security Configuration
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

# Business Logic Configuration
MIN_DEPOSIT_TRX = float(os.getenv('MIN_DEPOSIT_TRX', '1'))
MIN_WITHDRAWAL_TRX = float(os.getenv('MIN_WITHDRAWAL_TRX', '1'))
AMOUNT_PER_REFERRAL = float(os.getenv('AMOUNT_PER_REFERRAL', '10.0'))
REFERRAL_COMMISSION_RATE = float(os.getenv('REFERRAL_COMMISSION_RATE', '0.10'))
DEPOSIT_COMMISSION_RATE = float(os.getenv('DEPOSIT_COMMISSION_RATE', '0.05'))
DEPOSIT_TO_MAIN_WALLET_RATE = float(os.getenv('DEPOSIT_TO_MAIN_WALLET_RATE', '0.9'))
WITHDRAWAL_FEE_RATE = float(os.getenv('WITHDRAWAL_FEE_RATE', '0.01'))
HISTORY_PAGE_SIZE = int(os.getenv('HISTORY_PAGE_SIZE', '10'))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/bot_marketplace.log')
ERROR_LOG_FILE = os.getenv('ERROR_LOG_FILE', 'logs/errors.log')