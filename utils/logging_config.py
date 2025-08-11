"""
Configuration du système de logging pour le bot marketplace
"""
import os
import sys
from loguru import logger
from pathlib import Path


def setup_logging():
    """Configure le système de logging avec loguru"""
    
    # Créer le dossier logs s'il n'existe pas
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Supprimer la configuration par défaut de loguru
    logger.remove()
    
    # Configuration du niveau de log depuis l'environnement
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE", "logs/bot_marketplace.log")
    
    # Format de log personnalisé
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Logger pour la console (stdout)
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Logger pour le fichier
    logger.add(
        log_file,
        format=log_format,
        level=log_level,
        rotation="10 MB",  # Rotation à 10MB
        retention="30 days",  # Garder 30 jours d'historique
        compression="zip",  # Compresser les anciens logs
        backtrace=True,
        diagnose=True
    )
    
    # Logger spécifique pour les erreurs critiques
    logger.add(
        "logs/errors.log",
        format=log_format,
        level="ERROR",
        rotation="5 MB",
        retention="60 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    logger.info("Système de logging initialisé")
    return logger


def get_logger(name: str = None):
    """Retourne une instance du logger avec un nom spécifique"""
    if name:
        return logger.bind(name=name)
    return logger
