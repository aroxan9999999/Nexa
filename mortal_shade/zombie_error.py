import logging

zombie = logging.getLogger('zombie_error')
zombie.setLevel(logging.ERROR)
handler = logging.handlers.RotatingFileHandler(
    '[specter]/zombie_error.log', maxBytes=15 * 1024 * 1024, backupCount=5
)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
zombie.addHandler(handler)
