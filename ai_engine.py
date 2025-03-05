import random
import itertools
from collections import defaultdict, Counter
import numpy as np
import pickle
import logging
from typing import List, Dict, Tuple, Optional, Union, Set, Any

# Настройка логирования
logger = logging.getLogger(__name__)

# Константы (можно вынести в config.py)
SAVE_INTERVAL = 100  # Как часто сохранять прогресс

class Card:
    RANKS: List[str] = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    SUITS: List[str] = ["♥", "♦", "♣", "♠"]
    RANK_MAP: Dict[str, int] = {rank: i for i, rank in enumerate(RANKS)}
    SUIT_MAP: Dict[str, int] = {suit: i for i, suit in enumerate(SUITS)}

    def __init__(self, rank: str, suit: str):
        if rank not in self.RANKS:
            raise ValueError(f"Invalid rank: {rank}. Rank must be one of: {self.RANKS}")
        if suit not in self.SUITS:
            raise ValueError(f"Invalid suit: {suit}. Suit must be one of: {self.SUITS}")
        self.rank = rank
        self.suit = suit

    def __repr__(self) -> str:
        return f"{self.rank}{self.suit}"

    def __eq__(self, other: Union["Card", Dict]) -> bool:
        if isinstance(other, dict):
            return self.rank == other.get("rank") and self.suit == other.get("suit")
        return isinstance(other, Card) and self.rank == other.rank and self.suit == other.suit

    def __hash__(self) -> int:
        return hash((self.rank, self.suit))

    def to_dict(self) -> Dict[str, str]:
        return {"rank": self.rank, "suit": self.suit}

    @staticmethod
    def from_dict(card_dict: Dict[str, str]) -> "Card":
        return Card(card_dict["rank"], card_dict["suit"])

    @staticmethod
    def get_all_cards() -> List["Card"]:
        return [Card(rank, suit) for rank in Card.RANKS for suit in Card.SUITS]

    def to_numeric(self) -> Tuple[int, int]:
        """Преобразует карту в числовое представление (индексы ранга и масти)."""
        return Card.RANK_MAP[self.rank], Card.SUIT_MAP[self.suit]

    @staticmethod
    def from_numeric(rank_index: int, suit_index: int) -> "Card":
        """Создает карту из числового представления."""
        return Card(Card.RANKS[rank_index], Card.SUITS[suit_index])


class Hand:
    def __init__(self, cards: Optional[List[Card]] = None):
        self.cards: List[Card] = cards if cards is not None else []

    def add_card(self, card: Card) -> None:
        if not isinstance(card, Card):
            raise TypeError("card must be an instance of Card")
        self.cards.append(card)

    def remove_card(self, card: Card) -> None:
        if not isinstance(card, Card):
            raise TypeError("card must be an instance of Card")
        try:
            self.cards.remove(card)
        except ValueError:
            logger.warning(f"Card {card} not found in hand: {self.cards}")

    def __repr__(self) -> str:
        return ", ".join(map(str, self.cards))

    def __len__(self) -> int:
        return len(self.cards)

    def __iter__(self) -> Any:  # Исправлено на Any
        return iter(self.cards)

    def __getitem__(self, index: int) -> Card:
        return self.cards[index]

    def to_numeric(self) -> List[Tuple[int, int]]:
        """Преобразует руку в числовое представление."""
        return [card.to_numeric() for card in self.cards]


class Board:
    def __init__(self):
        self.top: List[Card] = []
        self.middle: List[Card] = []
        self.bottom: List[Card] = []

    def place_card(self, line: str, card: Card) -> None:
        if line == "top":
            if len(self.top) >= 3:
                raise ValueError("Top line is full")
            self.top.append(card)
        elif line == "middle":
            if len(self.middle) >= 5:
                raise ValueError("Middle line is full")
            self.middle.append(card)
        elif line == "bottom":
            if len(self.bottom) >= 5:
                raise ValueError("Bottom line is full")
            self.bottom.append(card)
        else:
            raise ValueError(f"Invalid line: {line}. Line must be one of: 'top', 'middle', 'bottom'")

    def is_full(self) -> bool:
        return len(self.top) == 3 and len(self.middle) == 5 and len(self.bottom) == 5

    def clear(self) -> None:
        self.top = []
        self.middle = []
        self.bottom = []

    def __repr__(self) -> str:
        return f"Top: {self.top}\nMiddle: {self.middle}\nBottom: {self.bottom}"

    def get_cards(self, line: str) -> List[Card]:
        if line == "top":
            return self.top
        elif line == "middle":
            return self.middle
        elif line == "bottom":
            return self.bottom
        else:
            raise ValueError("Invalid line specified")

    def to_numeric(self) -> Dict[str, List[Tuple[int, int]]]:
        """Преобразует доску в числовое представление."""
        return {
            "top": [card.to_numeric() for card in self.top],
            "middle": [card.to_numeric() for card in self.middle],
            "bottom": [card.to_numeric() for card in self.bottom],
        }


class GameState:
    def __init__(
        self,
        selected_cards: Optional[List[Card]] = None,
        board: Optional[Board] = None,
        discarded_cards: Optional[List[Card]] = None,
        ai_settings: Optional[Dict] = None,
        deck: Optional[List[Card]] = None,
    ):
        self.selected_cards: Hand = Hand(selected_cards) if selected_cards is not None else Hand()
        self.board: Board = board if board is not None else Board()
        self.discarded_cards: List[Card] = discarded_cards if discarded_cards is not None else []
        self.ai_settings: Dict = ai_settings if ai_settings is not None else {}
        self.current_player: int = 0  # Всегда 0, так как игрок один
        self.deck: List[Card] = deck if deck is not None else self.create_deck()

    def create_deck(self) -> List[Card]:
        """Creates a standard deck of 52 cards."""
        return [Card(rank, suit) for rank in Card.RANKS for suit in Card.SUITS]

    def get_current_player(self) -> int:
        return self.current_player

    def is_terminal(self) -> bool:
        """Checks if the game is in a terminal state (all lines are full)."""
        return self.board.is_full()

    def get_available_cards(self) -> List[Card]:
        """Returns a list of cards that are still available in the deck."""
        used_cards = set(self.discarded_cards + self.selected_cards.cards + self.board.top + self.board.middle + self.board.bottom)
        available_cards = [card for card in self.deck if card not in used_cards]
        return available_cards

    def get_actions(self) -> List[Dict[str, List[Card]]]:
        """Returns the valid actions for the current state."""
        logger.debug("get_actions - START")
        if self.is_terminal():
            logger.debug("get_actions - Game is terminal, returning empty actions")
            return []

        num_cards = len(self.selected_cards)
        if num_cards == 0:
            return []

        free_slots = self._get_free_slots()
        total_free_slots = sum(len(slots) for slots in free_slots.values())

        if self.ai_settings.get("fantasyMode", False):
            actions = self._get_fantasy_actions()
        elif num_cards == 3:
            actions = self._get_three_card_actions()
        elif num_cards > total_free_slots:
            actions = self._get_excess_cards_actions(total_free_slots)
        else:
            actions = self._get_standard_actions()

        logger.debug(f"Generated {len(actions)} actions")
        logger.debug("get_actions - END")
        return actions

    def _get_free_slots(self) -> Dict[str, List[int]]:
        """Возвращает словарь свободных слотов по линиям."""
        return {
            "top": [i for i in range(3) if i >= len(self.board.top)],
            "middle": [i for i in range(5) if i >= len(self.board.middle)],
            "bottom": [i for i in range(5) if i >= len(self.board.bottom)],
        }

    def _generate_placements(self, cards: List[Card], free_slots: Dict[str, List[int]]) -> List[Dict[str, List[Card]]]:
        """Генерирует все возможные размещения карт по свободным слотам (без учета правил)."""
        placements: List[Dict[str, List[Card]]] = []
        num_cards = len(cards)

        if num_cards == 0:  # Добавлено для обработки случая, когда карт нет
            return [{"top": [], "middle": [], "bottom": []}]

        def backtrack(index: int, current_placement: Dict[str, List[Card]]):
            if index == num_cards:
                placements.append({
                    "top": current_placement["top"][:],
                    "middle": current_placement["middle"][:],
                    "bottom": current_placement["bottom"][:]
                })
                return

            for line in ["top", "middle", "bottom"]:
                if len(current_placement[line]) < len(free_slots[line]):
                    current_placement[line].append(cards[index])
                    backtrack(index + 1, current_placement)
                    current_placement[line].pop()  # Backtrack

        backtrack(0, {"top": [], "middle": [], "bottom": []})
        return placements

    def _filter_valid_placements(self, placements: List[Dict[str, List[Card]]]) -> List[Dict[str, List[Card]]]:
        """Фильтрует размещения, оставляя только те, которые не приводят к мертвой руке."""
        valid_placements = []
        for placement in placements:
            temp_board = Board()
            temp_board.top = self.board.top + placement["top"]
            temp_board.middle = self.board.middle + placement["middle"]
            temp_board.bottom = self.board.bottom + placement["bottom"]
            temp_state = GameState(board=temp_board, ai_settings=self.ai_settings)
            if not temp_state.is_dead_hand():
                valid_placements.append(placement)
        return valid_placements

    def _placements_to_actions(self, placements: List[Dict[str, List[Card]]], discarded: List[Card]) -> List[Dict[str, List[Card]]]:
        """Преобразует размещения в формат действий."""
        return [
            {
                "top": p["top"],
                "middle": p["middle"],
                "bottom": p["bottom"],
                "discarded": discarded,
            }
            for p in placements
        ]

    def _get_fantasy_actions(self) -> List[Dict[str, List[Card]]]:
        """Генерирует действия для режима фантазии."""
        valid_fantasy_repeats = []
        for p in itertools.permutations(self.selected_cards.cards):
            action = {
                "top": list(p[:3]),
                "middle": list(p[3:8]),
                "bottom": list(p[8:13]),
                "discarded": list(p[13:]),
            }
            if self.is_valid_fantasy_repeat(action):
                valid_fantasy_repeats.append(action)

        if valid_fantasy_repeats:
            return sorted(
                valid_fantasy_repeats,
                key=lambda a: self.calculate_action_royalty(a),
                reverse=True,
            )
        else:
            return sorted(
                [
                    {
                        "top": list(p[:3]),
                        "middle": list(p[3:8]),
                        "bottom": list(p[8:13]),
                        "discarded": list(p[13:]),
                    }
                    for p in itertools.permutations(self.selected_cards.cards)
                ],
                key=lambda a: self.calculate_action_royalty(a),
                reverse=True,
            )

    def _get_three_card_actions(self) -> List[Dict[str, List[Card]]]:
        """Генерирует действия для случая, когда выбрано ровно 3 карты."""
        actions = []
        free_slots = self._get_free_slots()
        for discarded_index in range(3):
            remaining_cards = [
                card for i, card in enumerate(self.selected_cards.cards) if i != discarded_index
            ]
            placements = self._generate_placements(remaining_cards, free_slots)
            valid_placements = self._filter_valid_placements(placements)
            discarded = [self.selected_cards.cards[discarded_index]]
            actions.extend(self._placements_to_actions(valid_placements, discarded))
        return actions

    def _get_excess_cards_actions(self, total_free_slots: int) -> List[Dict[str, List[Card]]]:
        """Генерирует действия для случая, когда карт больше, чем свободных слотов."""
        actions = []
        free_slots = self._get_free_slots()
        for cards_to_place in itertools.combinations(self.selected_cards.cards, total_free_slots):
            cards_to_discard = [card for card in self.selected_cards.cards if card not in cards_to_place]
            placements = self._generate_placements(list(cards_to_place), free_slots)
            valid_placements = self._filter_valid_placements(placements)
            actions.extend(self._placements_to_actions(valid_placements, cards_to_discard))
        return actions

    def _get_standard_actions(self) -> List[Dict[str, List[Card]]]:
        """Генерирует действия для стандартного случая."""
        free_slots = self._get_free_slots()
        placements = self._generate_placements(self.selected_cards.cards, free_slots)
        valid_placements = self._filter_valid_placements(placements)
        return self._placements_to_actions(valid_placements, [])

    def is_valid_fantasy_entry(self, action: Dict[str, List[Card]]) -> bool:
        """Checks if an action leads to a valid fantasy mode entry."""
        new_board = Board()
        new_board.top = self.board.top + action.get("top", [])
        new_board.middle = self.board.middle + action.get("middle", [])
        new_board.bottom = self.board.bottom + action.get("bottom", [])

        temp_state = GameState(board=new_board, ai_settings=self.ai_settings)
        if temp_state.is_dead_hand():
            return False

        top_rank, _ = temp_state.evaluate_hand(new_board.top)
        return top_rank <= 8 and new_board.top[0].rank in ["Q", "K", "A"]

    def is_valid_fantasy_repeat(self, action: Dict[str, List[Card]]) -> bool:
        """Checks if an action leads to a valid fantasy mode repeat."""
        new_board = Board()
        new_board.top = self.board.top + action.get("top", [])
        new_board.middle = self.board.middle + action.get("middle", [])
        new_board.bottom = self.board.bottom + action.get("bottom", [])

        temp_state = GameState(board=new_board, ai_settings=self.ai_settings)
        if temp_state.is_dead_hand():
            return False

        top_rank, _ = temp_state.evaluate_hand(new_board.top)
        bottom_rank, _ = temp_state.evaluate_hand(new_board.bottom)

        if top_rank == 7:  # Set on top
            return True
        if bottom_rank <= 3:  # Four of a kind or better on bottom
            return True

        return False

    def calculate_action_royalty(self, action: Dict[str, List[Card]]) -> int:
        """Calculates the royalty for a given action."""
        new_board = Board()
        new_board.top = self.board.top + action.get("top", [])
        new_board.middle = self.board.middle + action.get("middle", [])
        new_board.bottom = self.board.bottom + action.get("bottom", [])

        temp_state = GameState(board=new_board, ai_settings=self.ai_settings)
        royalties = temp_state.calculate_royalties()
        return sum(royalties.values())

    def apply_action(self, action: Dict[str, List[Card]]) -> "GameState":
        """Applies an action to the current state and returns the new state."""
        new_board = Board()
        new_board.top = self.board.top + action.get("top", [])
        new_board.middle = self.board.middle + action.get("middle", [])
        new_board.bottom = self.board.bottom + action.get("bottom", [])

        new_discarded_cards = self.discarded_cards[:]
        if "discarded" in action and action["discarded"]:
            new_discarded_cards.extend(action["discarded"])

        new_game_state = GameState(
            selected_cards=Hand(),
            board=new_board,
            discarded_cards=new_discarded_cards,
            ai_settings=self.ai_settings,
            deck=self.deck[:],  # Копия колоды
        )

        return new_game_state

    def get_information_set(self) -> str:
        """Returns a string representation of the current information set."""
        def card_to_string(card: Card) -> str:
            return str(card)

        def sort_cards(cards: List[Card]) -> List[Card]:
            return sorted(cards, key=lambda card: (Card.RANK_MAP[card.rank], Card.SUIT_MAP[card.suit]))

        top_str = ",".join(map(card_to_string, sort_cards(self.board.top)))
        middle_str = ",".join(map(card_to_string, sort_cards(self.board.middle)))
        bottom_str = ",".join(map(card_to_string, sort_cards(self.board.bottom)))
        discarded_str = ",".join(map(card_to_string, sort_cards(self.discarded_cards)))
        selected_str = ",".join(map(card_to_string, sort_cards(self.selected_cards.cards)))

        return f"T:{top_str}|M:{middle_str}|B:{bottom_str}|D:{discarded_str}|S:{selected_str}"

    def get_payoff(self) -> int:
        """Calculates the payoff for the current state."""
        if not self.is_terminal():
            raise ValueError("Game is not in a terminal state")

        if self.is_dead_hand():
            return -sum(self.calculate_royalties().values())

        return sum(self.calculate_royalties().values())

    def is_dead_hand(self) -> bool:
        """Checks if the hand is a dead hand (invalid combination order)."""
        if not self.board.is_full():
            return False

        top_rank, _ = self.evaluate_hand(self.board.top)
        middle_rank, _ = self.evaluate_hand(self.board.middle)
        bottom_rank, _ = self.evaluate_hand(self.board.bottom)

        return top_rank > middle_rank or middle_rank > bottom_rank

    def _calculate_line_royalty(self, cards: List[Card]) -> int:
        """Вычисляет роялти для одной линии."""
        if not cards:
            return 0

        rank, _ = self.evaluate_hand(cards)
        num_cards = len(cards)

        if num_cards == 3:  # Top
            if rank == 7:  # Three of a Kind
                return 10 + Card.RANK_MAP[cards[0].rank]
            elif rank == 8:  # One Pair
                return max(0, Card.RANK_MAP[cards[0].rank] - 4)  # Пара 66 и выше
            else:
                return 0
        elif num_cards == 5:  # Middle and Bottom
            royalty_map = {
                1: 50,  # Royal Flush
                2: 30,  # Straight Flush
                3: 20,  # Four of a Kind
                4: 12,  # Full House
                5: 8,   # Flush
                6: 4,   # Straight
                7: 2,   # Three of a Kind
            }
            return royalty_map.get(rank, 0) * (2 if num_cards == 5 and rank <=7 else 1)  # x2 for middle
        else:
            return 0

    def calculate_royalties(self) -> Dict[str, int]:
        """Calculates royalties for all lines."""
        if self.is_dead_hand():
            return {"top": 0, "middle": 0, "bottom": 0}

        return {
            "top": self._calculate_line_royalty(self.board.top),
            "middle": self._calculate_line_royalty(self.board.middle),
            "bottom": self._calculate_line_royalty(self.board.bottom),
        }

    def evaluate_hand(self, cards: List[Card]) -> Tuple[int, float]:
        """Evaluates the hand and returns a rank (lower is better) and a score."""
        if not cards:
            return 11, 0.0

        num_cards = len(cards)
        if num_cards not in (3, 5):
            return 11, 0.0

        is_flush = self.is_flush(cards)
        is_straight = self.is_straight(cards)

        if num_cards == 5:
            if is_flush and cards[0].rank == "10":  # Royal Flush
                return 1, 25.0
            if is_straight and is_flush:  # Straight Flush
                return 2, 15.0 + Card.RANK_MAP[cards[4].rank] / 100.0
            if self.is_four_of_a_kind(cards):  # Four of a Kind
                rank = [card.rank for card in cards if [card.rank for card in cards].count(card.rank) == 4][0]
                return 3, 10.0 + Card.RANK_MAP[rank] / 100.0
            if self.is_full_house(cards):  # Full House
                rank = [card.rank for card in cards if [card.rank for card in cards].count(card.rank) == 3][0]
                return 4, 6.0 + Card.RANK_MAP[rank] / 100.0
            if is_flush:  # Flush
                return 5, 4.0 + sum(Card.RANK_MAP[card.rank] for card in cards) / 1000.0
            if is_straight:  # Straight
                return 6, 2.0 + sum(Card.RANK_MAP[card.rank] for card in cards) / 1000.0
            if self.is_three_of_a_kind(cards):  # Three of a Kind
                rank = [card.rank for card in cards if [card.rank for card in cards].count(card.rank) == 3][0]
                return 7, 2.0 + Card.RANK_MAP[rank] / 100.0
            if self.is_two_pair(cards):  # Two Pair
                ranks = sorted([Card.RANK_MAP[card.rank] for card in cards if [card.rank for card in cards].count(card.rank) == 2], reverse=True)
                return 8, sum(ranks) / 1000.0
            if self.is_one_pair(cards):  # One Pair
                rank = [card.rank for card in cards if [card.rank for card in cards].count(card.rank) == 2][0]
                return 9, Card.RANK_MAP[rank] / 100.0
            return 10, sum(Card.RANK_MAP[card.rank] for card in cards) / 10000.0  # High Card

        elif num_cards == 3:
            if self.is_three_of_a_kind(cards):  # Three of a Kind
                return 7, 10.0 + Card.RANK_MAP[cards[0].rank]
            if self.is_one_pair(cards):  # One Pair
                rank = [card.rank for card in cards if [card.rank for card in cards].count(card.rank) == 2][0]
                return 8, max(0, Card.RANK_MAP[rank] - 4)  # Pair bonus (66 and higher)
            return 9, 0.0  # High card - no bonus in this implementation

        return 11, 0.0

    def is_royal_flush(self, cards: List[Card]) -> bool:
        if not self.is_flush(cards):
            return False
        ranks = sorted([Card.RANK_MAP[card.rank] for card in cards])
        return ranks == [8, 9, 10, 11, 12]

    def is_straight_flush(self, cards: List[Card]) -> bool:
        return self.is_straight(cards) and self.is_flush(cards)

    def is_four_of_a_kind(self, cards: List[Card]) -> bool:
        ranks = [card.rank for card in cards]
        return any(ranks.count(r) == 4 for r in ranks)

    def is_full_house(self, cards: List[Card]) -> bool:
        ranks = [card.rank for card in cards]
        return any(ranks.count(r) == 3 for r in ranks) and any(ranks.count(r) == 2 for r in ranks)

    def is_flush(self, cards: List[Card]) -> bool:
        suits = [card.suit for card in cards]
        return len(set(suits)) == 1

    def is_straight(self, cards: List[Card]) -> bool:
        ranks = sorted([Card.RANK_MAP[card.rank] for card in cards])
        # Обработка случая "A-2-3-4-5"
        if ranks == [0, 1, 2, 3, 12]:
            return True
        return all(ranks[i + 1] - ranks[i] == 1 for i in range(len(ranks) - 1))

    def is_three_of_a_kind(self, cards: List[Card]) -> bool:
        ranks = [card.rank for card in cards]
        return any(ranks.count(r) == 3 for r in ranks)

    def is_two_pair(self, cards: List[Card]) -> bool:
        ranks = [card.rank for card in cards]
        pairs = [r for r in set(ranks) if ranks.count(r) == 2]
        return len(pairs) == 2

    def is_one_pair(self, cards: List[Card]) -> bool:
        ranks = [card.rank for card in cards]
        return any(ranks.count(r) == 2 for r in ranks)

    def get_fantasy_bonus(self) -> int:
        """Calculates the bonus for fantasy mode (simplified)."""
        #  Реализация опущена, так как используется calculate_royalties

        return 0
class CFRNode:
    def __init__(self, actions: List[Dict[str, List[Card]]]):
        self.regret_sum: Dict[Any, float] = defaultdict(lambda: 0.0)  # Исправлено
        self.strategy_sum: Dict[Any, float] = defaultdict(lambda: 0.0)  # Исправлено
        self.actions: List[Dict[str, List[Card]]] = actions

    def get_strategy(self, realization_weight: float) -> Dict[Any, float]:  # Исправлено
        """Вычисляет текущую стратегию, основываясь на сумме регретов."""
        normalizing_sum = 0.0
        strategy: Dict[Any, float] = defaultdict(lambda: 0.0)  # Исправлено

        for a in self.actions:
            a_tuple = tuple((k, tuple(v)) for k, v in a.items()) # Преобразование в кортеж
            strategy[a_tuple] = max(self.regret_sum[a_tuple], 0.0)
            normalizing_sum += strategy[a_tuple]

        for a in self.actions:
            a_tuple = tuple((k, tuple(v)) for k, v in a.items())
            if normalizing_sum > 0.0:
                strategy[a_tuple] /= normalizing_sum
            else:
                strategy[a_tuple] = 1.0 / len(self.actions)
            self.strategy_sum[a_tuple] += realization_weight * strategy[a_tuple]

        return strategy

    def get_average_strategy(self) -> Dict[Any, float]:  # Исправлено
        """Вычисляет среднюю стратегию за все итерации."""
        avg_strategy: Dict[Any, float] = defaultdict(lambda: 0.0)  # Исправлено
        normalizing_sum = sum(self.strategy_sum.values())

        if normalizing_sum > 0.0:
            for a in self.actions:
                a_tuple = tuple((k, tuple(v)) for k, v in a.items())
                avg_strategy[a_tuple] = self.strategy_sum[a_tuple] / normalizing_sum
        else:
            for a in self.actions:
                a_tuple = tuple((k, tuple(v)) for k, v in a.items())
                avg_strategy[a_tuple] = 1.0 / len(self.actions)
        return avg_strategy


class CFRAgent:
    def __init__(self, iterations: int = 500000, stop_threshold: float = 0.001):
        self.nodes: Dict[str, CFRNode] = {}
        self.iterations: int = iterations
        self.stop_threshold: float = stop_threshold
        self.current_iteration: int = 0
        self.save_interval: int = SAVE_INTERVAL

    def cfr(self, game_state: GameState, p0: float, p1: float) -> float:
        """Итеративная реализация MCCFR."""
        if game_state.is_terminal():
            return game_state.get_payoff()

        player = game_state.get_current_player()
        info_set = game_state.get_information_set()

        if info_set not in self.nodes:
            actions = game_state.get_actions()
            if not actions:
                return 0.0
            self.nodes[info_set] = CFRNode(actions)
        node = self.nodes[info_set]

        strategy = node.get_strategy(p0 if player == 0 else p1)
        util = defaultdict(float)
        node_util = 0.0

        action_items = list(node.actions)
        strategy_items = list(strategy.items())

        for a_tuple, a in zip(strategy_items, action_items):
            action_prob = a_tuple[1]  # Исправлено: Извлекаем вероятность из кортежа
            next_state = game_state.apply_action(a)
            if player == 0:
                util[a_tuple[0]] = -self.cfr(next_state, p0 * action_prob, p1)
            else:
                util[a_tuple[0]] = -self.cfr(next_state, p0, p1 * action_prob)
            node_util += action_prob * util[a_tuple[0]]

        if player == 0:
            for a_tuple, a in zip(strategy_items, action_items):
                node.regret_sum[a_tuple[0]] += p1 * (util[a_tuple[0]] - node_util)
        else:
            for a_tuple, a in zip(strategy_items, action_items):
                node.regret_sum[a_tuple[0]] += p0 * (util[a_tuple[0]] - node_util)

        return node_util

    def train(self, timeout_event: Optional[Any] = None) -> None:
        """Обучает агента MCCFR."""
        for i in range(self.iterations):
            self.current_iteration = i + 1
            if timeout_event and timeout_event.is_set():
                logger.info(f"Training interrupted after {i} iterations due to timeout.")
                break

            all_cards = Card.get_all_cards()
            random.shuffle(all_cards)
            game_state = GameState(deck=all_cards)
            game_state.selected_cards = Hand(all_cards[:5])  # Первые 5 карт
            self.cfr(game_state, 1.0, 1.0)

            if (i + 1) % self.save_interval == 0:
                logger.info(f"Iteration {i+1} of {self.iterations} complete. Saving progress...")
                self.save_progress()
                if self.check_convergence():
                    logger.info(f"CFR agent converged after {i + 1} iterations.")
                    break

    def check_convergence(self) -> bool:
        """Проверяет сходимость стратегии."""
        for node in self.nodes.values():
            avg_strategy = node.get_average_strategy()
            for _, prob in avg_strategy.items():
                if abs(prob - 1.0 / len(node.actions)) > self.stop_threshold:
                    return False
        return True

    def get_move(self, game_state: GameState, timeout_event: Optional[Any] = None) -> Optional[Dict[str, List[Card]]]:
        """Выбирает действие на основе обученной стратегии или эвристики."""
        logger.debug("Inside get_move")
        actions = game_state.get_actions()
        logger.debug(f"Available actions: {actions}")

        if not actions:
            logger.debug("No actions available, returning None.")
            return None

        info_set = game_state.get_information_set()
        logger.debug(f"Info set: {info_set}")

        if info_set in self.nodes:
            strategy = self.nodes[info_set].get_average_strategy()
            logger.debug(f"Strategy: {strategy}")
            if strategy:
                # Выбираем действие с наибольшей вероятностью
                best_move_tuple = max(strategy.items(), key=lambda item: item[1])[0]
                # Преобразуем обратно в словарь
                best_move = dict(best_move_tuple)
                return best_move
            else:
                logger.debug("Empty strategy, falling back to baseline evaluation.")
                return self.baseline_move(game_state, actions) # Используем baseline
        else:
            logger.debug("Info set not found in nodes, using baseline evaluation.")
            return self.baseline_move(game_state, actions) # Используем baseline

    def baseline_move(self, game_state: GameState, actions: List[Dict[str, List[Card]]]) -> Dict[str, List[Card]]:
        """Выбирает действие на основе эвристической оценки."""
        best_action = None
        best_score = float('-inf')

        for action in actions:
            score = self.baseline_evaluation(game_state.apply_action(action))
            if score > best_score:
                best_score = score
                best_action = action
        return best_action


    def baseline_evaluation(self, state: GameState) -> float:
        """Улучшенная эвристическая оценка состояния игры."""
        if state.is_dead_hand():
            return -1000.0

        total_score = 0.0

        # Оценка для каждой линии
        for line in ["top", "middle", "bottom"]:
            cards = getattr(state.board, line)
            if cards:
                line_score = self._evaluate_line_strength(cards, line)
                total_score += line_score

        # Штраф за неправильный порядок линий
        if not self._check_row_strength_rule(state):
            total_score -= 100.0

        return total_score

    def _evaluate_line_strength(self, cards: List[Card], line: str) -> float:
        """Оценивает силу линии."""
        if not cards:
            return 0.0

        rank, _ = self.evaluate_hand(cards)
        score = 0.0

        if line == "top":
            if rank == 7:  # Three of a Kind
                score = 15.0 + Card.RANK_MAP[cards[0].rank] * 0.1
            elif rank == 8:  # One Pair
                score = 5.0 + max(0, Card.RANK_MAP[cards[0].rank] - 4)  # Пара 66 и выше
            elif rank == 9:  # High Card
                score = 1.0
        elif line == "middle":
            if rank == 1:  # Royal Flush
                score = 150.0
            elif rank == 2:  # Straight Flush
                score = 100.0 + Card.RANK_MAP[cards[-1].rank] * 0.1
            elif rank == 3:  # Four of a Kind
                score = 80.0 + Card.RANK_MAP[cards[1].rank] * 0.1
            elif rank == 4:  # Full House
                score = 60.0 + Card.RANK_MAP[cards[2].rank] * 0.1
            elif rank == 5:  # Flush
                score = 40.0 + Card.RANK_MAP[cards[-1].rank] * 0.1
            elif rank == 6:  # Straight
                score = 20.0 + Card.RANK_MAP[cards[-1].rank] * 0.1
            elif rank == 7:  # Three of a Kind
                score = 10.0 + Card.RANK_MAP[cards[0].rank] * 0.1
            elif rank == 8:  # Two Pair
                score = 5.0 + Card.RANK_MAP[cards[1].rank] * 0.01 + Card.RANK_MAP[cards[3].rank] * 0.001
            elif rank == 9:  # One Pair
                score = 2.0 + Card.RANK_MAP[cards[1].rank] * 0.01
            elif rank == 10:  # High Card
                score = Card.RANK_MAP[cards[-1].rank] * 0.001
        elif line == "bottom":
            if rank == 1:  # Royal Flush
                score = 120.0
            elif rank == 2:  # Straight Flush
                score = 80.0 + Card.RANK_MAP[cards[-1].rank] * 0.1
            elif rank == 3:  # Four of a Kind
                score = 60.0 + Card.RANK_MAP[cards[1].rank] * 0.1
            elif rank == 4:  # Full House
                score = 40.0 + Card.RANK_MAP[cards[2].rank] * 0.1
            elif rank == 5:  # Flush
                score = 30.0 + Card.RANK_MAP[cards[-1].rank] * 0.1
            elif rank == 6:  # Straight
                score = 15.0 + Card.RANK_MAP[cards[-1].rank] * 0.1
            elif rank == 7:  # Three of a Kind
                score = 8.0 + Card.RANK_MAP[cards[0].rank] * 0.1
            elif rank == 8:  # Two Pair
                score = 4.0 + Card.RANK_MAP[cards[1].rank] * 0.01 + Card.RANK_MAP[cards[3].rank] * 0.001
            elif rank == 9:  # One Pair
                score = 1.0 + Card.RANK_MAP[cards[1].rank] * 0.01
            elif rank == 10:  # High Card
                score = Card.RANK_MAP[cards[-1].rank] * 0.001

        return score

    def _check_row_strength_rule(self, state: GameState) -> bool:
        """Проверяет правило силы рядов (bottom >= middle >= top)."""
        if not state.board.is_full():
            return True

        top_rank, _ = self.evaluate_hand(state.board.top)
        middle_rank, _ = self.evaluate_hand(state.board.middle)
        bottom_rank, _ = self.evaluate_hand(state.board.bottom)

        return bottom_rank <= middle_rank <= top_rank

    def save_progress(self, filename: str = "cfr_data.pkl") -> None:
        """Saves AI progress to a local file."""
        data = {
            "nodes": self.nodes,
            "iterations": self.iterations,
            "current_iteration": self.current_iteration,
            "stop_threshold": self.stop_threshold,
        }
        try:
            with open(filename, "wb") as f:
                pickle.dump(data, f)
            logger.info(f"AI progress saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving AI progress: {e}")

    def load_progress(self, filename: str = "cfr_data.pkl") -> None:
        """Loads AI progress from a local file."""
        try:
            with open(filename, "rb") as f:
                data = pickle.load(f)
            self.nodes = data["nodes"]
            self.iterations = data["iterations"]
            self.current_iteration = data.get("current_iteration", 0)  # Добавлено
            self.stop_threshold = data.get("stop_threshold", 0.001)
            logger.info(f"AI progress loaded from {filename}")
        except FileNotFoundError:
            logger.info(f"No progress file found at {filename}")
        except Exception as e:
            logger.error(f"Error loading AI progress: {e}")

    def get_training_progress(self) -> float:
        """Возвращает процент завершенности обучения."""
        if self.iterations == 0:
            return 0.0
        return min(1.0, self.current_iteration / self.iterations)  # Ограничиваем 1.0

    def reset_training(self) -> None:
        """Сбрасывает состояние обучения."""
        self.nodes = {}
        self.current_iteration = 0
        logger.info("AI training progress reset.")


class RandomAgent:  # Упрощенный RandomAgent
    def get_move(self, game_state: GameState, timeout_event: Optional[Any] = None) -> Optional[Dict[str, List[Card]]]:
        """Chooses a random valid move."""
        actions = game_state.get_actions()
        return random.choice(actions) if actions else None
