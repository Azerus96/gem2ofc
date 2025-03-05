from flask import Flask, render_template, jsonify, session, request
import os
import ai_engine
from ai_engine import CFRAgent, RandomAgent, Card
import github_utils
import time
import json
from threading import Thread, Event
import logging
from typing import Dict, Optional, List, Any, Union

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Секретный ключ для сессий Flask

# Глобальные переменные (лучше так не делать, но для простоты пока оставим)
game_manager: Optional["GameManager"] = None  # Используем Optional

class GameManager:
    """Управляет состоянием игры и взаимодействием с AI."""

    def __init__(self):
        self.game_state: ai_engine.GameState = ai_engine.GameState()
        self.ai_settings: Dict[str, Any] = {  # Значения по умолчанию
            "fantasyType": "normal",
            "fantasyMode": False,
            "aiTime": 60,
            "iterations": CFRAgent().iterations,  # Берем из CFRAgent
            "stopThreshold": 0.0001,
            "aiType": "mccfr",
        }
        self.ai_agent: Union[CFRAgent, RandomAgent, None] = None
        self.previous_ai_settings: Dict[str, Any] = {}  # Для отслеживания изменений

    def initialize_ai(self, ai_settings: Optional[Dict[str, Any]] = None) -> None:
        """Инициализирует AI агента (CFR или Random) на основе настроек."""
        if ai_settings:
            self.ai_settings.update(ai_settings)  # Обновляем настройки
            self.previous_ai_settings = ai_settings.copy()

        logger.info(f"Инициализация AI агента с настройками: {self.ai_settings}")

        if self.ai_settings["aiType"] == "mccfr":
            self.ai_agent = CFRAgent(
                iterations=int(self.ai_settings["iterations"]),
                stop_threshold=float(self.ai_settings["stopThreshold"]),
            )
            logger.info(f"AI агент MCCFR инициализирован: {self.ai_agent}")

            if os.environ.get("AI_PROGRESS_TOKEN"):  # Если задан токен GitHub
                try:
                    # Загрузка с GitHub
                    logger.info("Попытка загрузить прогресс AI с GitHub...")
                    if github_utils.load_ai_progress_from_github():
                        data = self.ai_agent.load_progress()  # Загружаем, используя метод агента
                        if data:
                            logger.info("Прогресс AI успешно загружен и применен к агенту.")
                        else:
                            logger.warning("Прогресс AI с GitHub загружен, но данные повреждены/пусты.")
                    else:
                        logger.warning("Не удалось загрузить прогресс AI с GitHub.")

                except Exception as e:
                    logger.error(f"Ошибка загрузки прогресса AI: {e}")
            else:
                logger.info("AI_PROGRESS_TOKEN не установлен. Загрузка прогресса отключена.")
        else:
            self.ai_agent = RandomAgent()
            logger.info("Используется случайный AI агент.")

    def update_state(self, new_state: Dict[str, Any]) -> None:
        """Обновляет состояние игры."""
        logger.debug(f"Обновление состояния игры: {new_state}")

        if "ai_settings" in new_state:
            # Реинициализация AI агента при изменении настроек
            if new_state["ai_settings"] != self.previous_ai_settings:
                logger.info("Настройки AI изменились, реинициализация агента")
                self.initialize_ai(new_state["ai_settings"])

        if "board" in new_state:
            # Обновление доски
            new_board = ai_engine.Board()
            for line in ["top", "middle", "bottom"]:
                if line in new_state["board"]:
                    for card_data in new_state["board"][line]:
                        if card_data:
                            new_board.place_card(line, ai_engine.Card.from_dict(card_data))
            self.game_state.board = new_board

        if "selected_cards" in new_state:
            self.game_state.selected_cards = ai_engine.Hand(
                [ai_engine.Card.from_dict(card_data) for card_data in new_state["selected_cards"]]
            )

        if "discarded_cards" in new_state:
            self.game_state.discarded_cards = [
                ai_engine.Card.from_dict(card_data) for card_data in new_state["discarded_cards"]
            ]
        if "removed_cards" in new_state:
            removed_cards = [
                ai_engine.Card.from_dict(card) if isinstance(card, dict) else card
                for card in new_state["removed_cards"]
            ]
            # Добавляем в discarded_cards, если еще нет
            for card in removed_cards:
                if card not in self.game_state.discarded_cards:
                    self.game_state.discarded_cards.append(card)

            # Удаляем из selected_cards
            self.game_state.selected_cards.cards = [
                card for card in self.game_state.selected_cards.cards
                if card not in removed_cards
            ]

    def get_ai_move(self) -> Dict[str, Any]:
        """Получает ход от AI агента."""
        logger.debug("Запрос хода AI")
        if self.ai_agent is None:
            raise ValueError("AI агент не инициализирован")

        timeout_event = Event()
        result: Dict[str, Any] = {"move": None}

        # ИСПРАВЛЕННАЯ СТРОКА (без self):
        ai_thread = Thread(
            target=self.ai_agent.get_move,
            args=(self.game_state, timeout_event, result)
        )
        ai_thread.start()
        ai_thread.join(timeout=int(self.ai_settings["aiTime"]))

        if ai_thread.is_alive():
            timeout_event.set()
            ai_thread.join()
            logger.warning("Время ожидания хода AI истекло")
            return {"error": "AI move timed out"}

        move = result["move"]
        logger.debug(f"Получен ход AI: {move}")

        if move is None or "error" in move:
            error_message = move.get("error", "Unknown error") if move else "Unknown error"
            logger.error(f"Ошибка хода AI: {error_message}")
            return {"error": error_message}
        return {"move": move}

    def reset_game(self) -> None:
        """Сбрасывает состояние игры."""
        self.game_state = ai_engine.GameState()
        logger.info("Состояние игры сброшено")

    def get_game_state(self) -> Dict[str, Any]:
        """Возвращает текущее состояние игры (для отображения)."""
        return {
            "selected_cards": [card.to_dict() for card in self.game_state.selected_cards.cards],
            "board": {
                "top": [card.to_dict() if card else None for card in self.game_state.board.top],
                "middle": [card.to_dict() if card else None for card in self.game_state.board.middle],
                "bottom": [card.to_dict() if card else None for card in self.game_state.board.bottom],
            },
            "discarded_cards": [card.to_dict() for card in self.game_state.discarded_cards],
            "ai_settings": self.ai_settings,
        }

    def serialize_move(self, move: Dict[str, List[ai_engine.Card]]) -> Dict[str, Any]:
        """Преобразует действие (move) в словарь (для JSON)."""
        logger.debug(f"Сериализация хода: {move}")
        serialized = {
            key: [card.to_dict() for card in cards] if isinstance(cards, list) else card.to_dict()
            for key, cards in move.items()
        }
        logger.debug(f"Сериализованный ход: {serialized}")
        return serialized


# Обработчики Flask
@app.route("/")
def home():
    """Главная страница (не используется)."""
    logger.debug("Обработка запроса главной страницы")
    return render_template("index.html")  # Предполагается, что есть index.html


@app.route("/training")
def training():
    """Страница тренировки."""
    global game_manager
    logger.debug("Обработка запроса страницы тренировки")

    if game_manager is None:
        game_manager = GameManager()
        game_manager.initialize_ai()  # Инициализируем AI при первом обращении

    return render_template("training.html", game_state=game_manager.get_game_state())


@app.route("/update_state", methods=["POST"])
def update_state():
    """Обновление состояния игры (вызывается из JavaScript)."""
    global game_manager
    logger.debug("Обработка запроса обновления состояния - START")

    if not request.is_json:
        logger.error("Ошибка: Запрос не в формате JSON")
        return jsonify({"error": "Content type must be application/json"}), 400

    try:
        new_state = request.get_json()
        logger.debug(f"Получено обновление состояния: {new_state}")

        if game_manager is None:
            game_manager = GameManager()
            game_manager.initialize_ai()

        game_manager.update_state(new_state)

        logger.debug("Обработка запроса обновления состояния - END")
        return jsonify({"status": "success"})

    except Exception as e:
        logger.exception(f"Ошибка в update_state: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/ai_move", methods=["POST"])
def ai_move():
    """Получение хода AI и обновление состояния игры."""
    global game_manager
    logger.debug("Обработка запроса хода AI - START")

    if game_manager is None:
        return jsonify({"error": "Game manager not initialized"}), 500

    try:
        ai_move_result = game_manager.get_ai_move()
        if "error" in ai_move_result:
            return jsonify(ai_move_result), 400 if ai_move_result["error"] != "AI move timed out" else 504

        move = ai_move_result["move"]
        # Применяем ход
        game_manager.game_state = game_manager.game_state.apply_action(move)

        # Проверяем, завершена ли игра
        if game_manager.game_state.is_terminal():
            royalties = game_manager.game_state.calculate_royalties()
            total_royalty = sum(royalties.values())
            logger.info(f"Игра окончена. Роялти: {royalties}, Всего: {total_royalty}")

            # Сохранение прогресса AI (для MCCFR)
            if game_manager.ai_settings["aiType"] == "mccfr" and game_manager.ai_agent:
                try:
                    game_manager.ai_agent.save_progress()
                    logger.info("Прогресс AI сохранен локально.")
                    if github_utils.save_ai_progress_to_github():
                        logger.info("Прогресс AI сохранен на GitHub.")
                    else:
                        logger.warning("Не удалось сохранить прогресс AI на GitHub.")
                except Exception as e:
                    logger.error(f"Ошибка сохранения прогресса AI: {e}")

            return jsonify({
                "move": game_manager.serialize_move(move),
                "royalties": royalties,
                "total_royalty": total_royalty,
                "game_over": True
            })
        else:
            return jsonify({
                "move": game_manager.serialize_move(move),
                "royalties": {},  # Пустой словарь, если игра не завершена
                "total_royalty": 0,
                "game_over": False
            })

    except Exception as e:
        logger.exception(f"Ошибка в ai_move: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/reset_training", methods=["POST"])
def reset_training():
    """Сброс состояния обучения AI."""
    global game_manager
    if game_manager and game_manager.ai_settings["aiType"] == "mccfr" and game_manager.ai_agent:
        game_manager.ai_agent.reset_training()
        # Также сбрасываем игру
        game_manager.reset_game()
        return jsonify({"status": "success"})
    else:
        return jsonify({"error": "Cannot reset training: AI type is not MCCFR or agent not initialized"}), 400

@app.route("/training_progress", methods=["GET"])
def training_progress():
    """Возвращает прогресс обучения AI."""
    global game_manager
    if game_manager and game_manager.ai_settings["aiType"] == "mccfr" and game_manager.ai_agent:
        progress = game_manager.ai_agent.get_training_progress()
        return jsonify({"progress": progress})
    else:
        return jsonify({"progress": 0.0})

if __name__ == "__main__":
    app.run(debug=True, port=10000)
