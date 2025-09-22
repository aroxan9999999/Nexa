import logging

aiogram_logging = logging.getLogger('aiogram')
aiogram_logging.setLevel(logging.INFO)

aiogram_handler = logging.FileHandler('[specter]/aiogram.log', mode='w', encoding='utf-8')
aiogram_handler.setLevel(logging.INFO)


aiogram_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
aiogram_handler.setFormatter(aiogram_formatter)

aiogram_logging.addHandler(aiogram_handler)

aiogram_logging.propagate = False
