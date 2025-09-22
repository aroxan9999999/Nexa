import os
import logging
from logging.handlers import RotatingFileHandler

plinko_data = logging.getLogger("plinko_data-xx")
plinko_data.setLevel(logging.INFO)

handler = RotatingFileHandler("[specter]/plinko_data.log", maxBytes=10 * 1024 * 1024, backupCount=2)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
plinko_data.addHandler(handler)