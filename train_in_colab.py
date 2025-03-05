# train_in_colab.py

import ai_engine
import config
import github_utils
import logging
import time
from google.colab import userdata  # Импортируем userdata

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def train_and_save():
    """Тренирует CFRAgent и сохраняет прогресс на GitHub."""

    # 1. Инициализация CFRAgent
    agent = ai_engine.CFRAgent(
        iterations=config.ITERATIONS, stop_threshold=config.STOP_THRESHOLD
    )

    # 2. Загрузка существующего прогресса (если есть)
    try:
        if github_utils.load_ai_progress_from_github(filename=config.AI_PROGRESS_FILENAME):
            agent.load_progress(filename=config.AI_PROGRESS_FILENAME)
            logger.info("Loaded existing AI progress from GitHub.")
        else:
            logger.info("No existing AI progress found on GitHub.")
    except Exception as e:
        logger.error(f"Error loading progress from GitHub: {e}")
        # Не прерываем выполнение, продолжаем обучение с нуля

    # 3. Запуск обучения
    start_time = time.time()
    logger.info(f"Starting training for {config.ITERATIONS} iterations...")
    agent.train()
    end_time = time.time()
    logger.info(f"Training complete. Elapsed time: {end_time - start_time:.2f} seconds")

    # 4. Сохранение прогресса (локально и на GitHub)
    agent.save_progress(filename=config.AI_PROGRESS_FILENAME)  # Локально

    # Получаем токен из userdata
    try:
        token = userdata.get('AI_PROGRESS_TOKEN')  # 'AI_PROGRESS_TOKEN' - имя вашего секрета
    except userdata.SecretNotFoundError:
        logger.error("AI_PROGRESS_TOKEN not found in Colab secrets.  Make sure you have added it.")
        token = ""  # Или запросите ввод токена, если не нашли

    if token:
        if github_utils.save_ai_progress_to_github(filename=config.AI_PROGRESS_FILENAME):
            logger.info("AI progress saved to GitHub.")
        else:
            logger.error("Failed to save AI progress to GitHub.")
    else:
        logger.warning("AI_PROGRESS_TOKEN not set. Progress not saved to GitHub.")

if __name__ == "__main__":
    train_and_save()
