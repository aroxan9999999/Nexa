import logging

lxx = logging.getLogger('lxx')
lxx.setLevel(logging.INFO)
handler = logging.handlers.RotatingFileHandler(
    '[specter]/lxx_info.log', maxBytes=15 * 1024 * 1024, backupCount=5
)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
lxx.addHandler(handler)