class Card {
    constructor(rank, suit, element) {
        this.rank = rank;
        this.suit = suit;
        this.element = element || this.createCardElement();
        this.addEventListeners();
    }

    createCardElement() {
        const card = document.createElement('div');
        card.className = 'card';
        card.dataset.rank = this.rank;
        card.dataset.suit = this.suit;
        card.textContent = `${this.rank}${this.suit}`;
        if (this.suit === '♥' || this.suit === '♦') {
            card.style.color = '#e44145';
        }
        card.draggable = true;
        return card;
    }

    addEventListeners() {
        this.element.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', '');
            e.dataTransfer.setData('card', JSON.stringify({ rank: this.rank, suit: this.suit }));
            this.element.style.opacity = '0.5';
        });

        this.element.addEventListener('dragend', (e) => {
            this.element.style.opacity = '1';
        });

        this.element.addEventListener('dblclick', () => {
            if (this.element.parentNode.classList.contains('combination-slot')) {
                game.handleDoubleClick({ rank: this.rank, suit: this.suit, source: 'combination' });
            }
        });
    }
    getCardKey() {
        return `${this.rank}${this.suit}`;
    }
}

class Slot {
    constructor(type, rowElement, index) {
        this.type = type; // 'combination' or 'board'
        this.rowElement = rowElement;
        this.index = index;
        this.element = this.createSlotElement();
        this.card = null; // Initially, the slot is empty
        this.addEventListeners();
    }

    createSlotElement() {
        const slot = document.createElement('div');
        slot.className = this.type === 'combination' ? 'combination-slot' : 'card-slot';
        if (this.type === 'board') {
            slot.style.position = 'relative';
            const royaltyAnimation = document.createElement('div');
            royaltyAnimation.classList.add('royalty-animation');
            slot.appendChild(royaltyAnimation);
        }
        return slot;
    }

    addEventListeners() {
        this.element.addEventListener('dragover', (e) => e.preventDefault());
        this.element.addEventListener('drop', (e) => {
            if (this.type === 'combination') {
                game.handleCombinationSlotDrop(e, this);
            } else {
                game.handleDrop(e, this);
            }
        });
    }

    setCard(card) {
        if (this.card) {
            this.card.element.remove(); // Remove the old card element
        }
        this.card = card;
        if (card) {
            this.element.appendChild(card.element);
            this.element.classList.add('taken');
        } else {
            this.element.classList.remove('taken');
        }
    }
    getCard() {
        return this.card;
    }

    clear() {
        this.setCard(null);
    }
    showRoyalty(value) {
        if (this.type === 'board' && value > 0) {
            const royaltyAnimation = this.element.querySelector('.royalty-animation');
            if (royaltyAnimation) {
                royaltyAnimation.textContent = `+${value}`;
                royaltyAnimation.classList.remove('show');
                requestAnimationFrame(() => {
                    royaltyAnimation.classList.add('show');
                });
                setTimeout(() => {
                    royaltyAnimation.classList.remove('show');
                }, 3000);
            }
        }
    }
}

class Board {
    constructor() {
        this.rows = {}; // 'top', 'middle', 'bottom'
        this.slots = []; // Store all slots for easy access
        this.init();
    }

    init() {
        const rows = ['top', 'middle', 'bottom'];
        const numCards = [3, 5, 5];

        rows.forEach((rowName, rowIndex) => {
            const rowElement = document.getElementById(`${rowName}-row`);
            rowElement.innerHTML = ''; // Clear existing content
            this.rows[rowName] = [];

            for (let i = 0; i < numCards[rowIndex]; i++) {
                const slot = new Slot('board', rowElement, i);
                this.rows[rowName].push(slot);
                this.slots.push(slot); // Add to the slots array
                rowElement.appendChild(slot.element);
            }
        });
    }
    getSlot(rowName, index) {
        return this.rows[rowName][index];
    }

    clear() {
        this.slots.forEach(slot => slot.clear());
    }
    placeCards(moveData) {
        const lines = ['top', 'middle', 'bottom'];

        lines.forEach(line => {
            const row = this.rows[line]; // Access the row directly

            if (moveData && moveData[line]) {
                moveData[line].forEach((cardData, index) => {
                    if (!cardData) return;

                    const slot = row[index]; // Get the slot directly
                    if (slot && !slot.getCard()) {
                        const card = new Card(cardData.rank, cardData.suit);
                        slot.setCard(card);
                        game.unavailableCards.add(card.getCardKey());
                        game.discardedCards.add(card.getCardKey()); // Add to discardedCards
                    }
                });
            }
        });
        // Add all cards on the board to discardedCards
        this.slots.forEach(slot => {
            const card = slot.getCard();
            if(card){
                game.discardedCards.add(card.getCardKey());
            }
        });
    }
    getRoyalties() {
        const royalties = {};
        for (const rowName in this.rows) {
            royalties[rowName] = 0; // Initialize to 0
            const row = this.rows[rowName];
            const cardsInRow = row.map(slot => slot.getCard()).filter(card => card !== null);
            if (cardsInRow.length > 0) {
                // No need to convert to simple objects, server handles this
                royalties[rowName] = 0; // Server will calculate
            }
        }
        return royalties;
    }
    displayRoyalties(royalties) {
        for (const rowName in royalties) {
            const royaltyValue = royalties[rowName];
            if (royaltyValue > 0) { // Will be 0 if game is not over
                const row = this.rows[rowName];
                const lastSlot = row[row.length - 1]; // Get the last slot
                lastSlot.showRoyalty(royaltyValue);
            }
        }
    }
}

class Game {
    constructor() {
        this.board = new Board();
        this.combinationSlots = [];
        this.selectedRank = null;
        this.selectedSuit = null;
        this.unavailableCards = new Set();
        this.discardedCards = new Set();
        this.menuOpen = false;
        this.totalRoyalty = 0;
    }

    init() {
        this.setupCombinationArea();
        this.addGlobalEventListeners();
        this.updateSelectorAvailability();
        this.updateTrainingProgress(); // Initial progress update
    }

    setupCombinationArea() {
        const combinationArea = document.getElementById('combination-area');
        combinationArea.innerHTML = ''; // Clear existing slots
        this.combinationSlots = [];

        for (let i = 0; i < 17; i++) {
            const slot = new Slot('combination', combinationArea, i);
            this.combinationSlots.push(slot);
            combinationArea.appendChild(slot.element);
        }
    }

    addGlobalEventListeners() {
        // Event listeners for selectors (ranks and suits)
        document.querySelectorAll('.selector-item').forEach(item => {
            item.addEventListener('click', () => this.handleCardSelection(item));
        });

        ['aiTime', 'iterations', 'stopThreshold'].forEach(id => {
            const slider = document.getElementById(id);
            const value = document.getElementById(`${id}Value`);
            slider.addEventListener('input', (e) => {
                value.textContent = e.target.value;
            });
        });

        document.addEventListener('click', (e) => {
            const menu = document.querySelector('.menu-panel');
            const menuToggle = document.querySelector('.menu-toggle');
            if (this.menuOpen && !menu.contains(e.target) && !menuToggle.contains(e.target)) {
                this.toggleMenu();
            }
        });
    }


    handleCardSelection(element) {
        if (element.classList.contains('unavailable')) {
            return;
        }

        if (element.dataset.rank) {
            if (this.selectedRank === element.dataset.rank) {
                this.selectedRank = null;
                element.classList.remove('selected');
            } else {
                document.querySelectorAll('[data-rank]').forEach(el => el.classList.remove('selected'));
                this.selectedRank = element.dataset.rank;
                element.classList.add('selected');
            }
        } else if (element.dataset.suit) {
            if (this.selectedSuit === element.dataset.suit) {
                this.selectedSuit = null;
                element.classList.remove('selected');
            } else {
                document.querySelectorAll('[data-suit]').forEach(el => el.classList.remove('selected'));
                this.selectedSuit = element.dataset.suit;
                element.classList.add('selected');
            }
        }

        if (this.selectedRank && this.selectedSuit) {
            const cardKey = `${this.selectedRank}${this.selectedSuit}`;
            if (!this.unavailableCards.has(cardKey) && !this.discardedCards.has(cardKey)) {
                const emptySlot = this.combinationSlots.find(slot => !slot.getCard());
                if (emptySlot) {
                    const card = new Card(this.selectedRank, this.selectedSuit);
                    emptySlot.setCard(card);
                    this.unavailableCards.add(cardKey);

                    this.selectedRank = null;
                    this.selectedSuit = null;
                    document.querySelectorAll('.selector-item').forEach(el => el.classList.remove('selected'));
                    this.updateSelectorAvailability();
                }
            }
        }
    }

    handleCombinationSlotDrop(e, slot) {
        e.preventDefault();
        const cardData = JSON.parse(e.dataTransfer.getData('card'));
        const cardKey = `${cardData.rank}${cardData.suit}`;

        if (!this.unavailableCards.has(cardKey) && !this.discardedCards.has(cardKey) && !slot.getCard()) {
            const card = new Card(cardData.rank, cardData.suit);
            slot.setCard(card);
            this.unavailableCards.add(cardKey);
            document.querySelectorAll('.selector-item').forEach(item => item.classList.remove('selected'));
            this.selectedRank = null;
            this.selectedSuit = null;
            this.updateSelectorAvailability();
        }
    }

    handleDrop(e, slot) {
        e.preventDefault();
        const cardData = JSON.parse(e.dataTransfer.getData('card'));
        const cardKey = `${cardData.rank}${cardData.suit}`;

        if (!this.unavailableCards.has(cardKey) && !this.discardedCards.has(cardKey) && !slot.getCard()) {
            const card = new Card(cardData.rank, cardData.suit);
            slot.setCard(card);
            this.unavailableCards.add(cardKey);
            document.querySelectorAll('.selector-item').forEach(item => item.classList.remove('selected'));
            this.selectedRank = null;
            this.selectedSuit = null;
            this.updateSelectorAvailability();
        }
    }

    handleDoubleClick(cardData) {
        const cardKey = `${cardData.rank}${cardData.suit}`;
        if (this.unavailableCards.has(cardKey) && cardData.source === 'combination') {
            this.unavailableCards.delete(cardKey);
            this.updateSelectorAvailability();

            // Find and remove the card from the combination slot
            let removedSlotIndex = -1;
            for (let i = 0; i < this.combinationSlots.length; i++) {
                const slot = this.combinationSlots[i];
                const card = slot.getCard();
                if (card && card.rank === cardData.rank && card.suit === cardData.suit) {
                    slot.clear();
                    removedSlotIndex = i;
                    break;
                }
            }

            // Shift cards to fill the empty slot
            if (removedSlotIndex !== -1) {
                const filledSlots = this.combinationSlots.filter(slot => slot.getCard() !== null);
                const emptySlots = this.combinationSlots.filter(slot => slot.getCard() === null);

                // Clear all slots
                this.combinationSlots.forEach(slot => slot.clear());

                // Refill slots in the correct order
                filledSlots.forEach((slot, index) => {
                    const card = slot.getCard();
                    if (card) {
                        this.combinationSlots[index].setCard(card);
                    }
                });
            }

            // No need to add to discardedCards, as double-click doesn't remove the card from the deck
            this.updateGameStateAndSend();
        }
    }

    updateSelectorAvailability() {
        const cardAvailability = {};
        ['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2'].forEach(rank => {
            ['♥', '♦', '♣', '♠'].forEach(suit => {
                const cardKey = `${rank}${suit}`;
                cardAvailability[cardKey] = true;
            });
        });

        this.unavailableCards.forEach(cardKey => {
            if (cardAvailability.hasOwnProperty(cardKey)) {
                cardAvailability[cardKey] = false;
            }
        });

        this.discardedCards.forEach(cardKey => {
            if (cardAvailability.hasOwnProperty(cardKey)) {
                cardAvailability[cardKey] = false;
            }
        });

        document.querySelectorAll('.selector-item[data-rank]').forEach(item => {
            const rank = item.dataset.rank;
            const hasAvailableCard = ['♥', '♦', '♣', '♠'].some(suit => cardAvailability[`${rank}${suit}`]);
            item.classList.toggle('unavailable', !hasAvailableCard);
        });

        document.querySelectorAll('.selector-item[data-suit]').forEach(item => {
            const suit = item.dataset.suit;
            const hasAvailableCard = ['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2'].some(rank =>
                cardAvailability[`${rank}${suit}`]
            );
            item.classList.toggle('unavailable', !hasAvailableCard);
        });
    }

    getGameStateFromDOM() {
        const selectedCards = this.combinationSlots
            .map(slot => slot.getCard())
            .filter(card => card !== null)
            .map(card => ({ rank: card.rank, suit: card.suit }));

        const board = { top: [], middle: [], bottom: [] };
        ['top', 'middle', 'bottom'].forEach(rowName => {
            board[rowName] = this.board.rows[rowName]
                .map(slot => slot.getCard())
                .filter(card => card !== null)
                .map(card => ({ rank: card.rank, suit: card.suit }));
        });

        const discardedCardsArray = Array.from(this.discardedCards).map(cardKey => {
            const [rank, suit] = cardKey.match(/([0-9JQKA]+)([♥♦♣♠])/).slice(1);
            return { rank, suit };
        });

        return {
            selected_cards: selectedCards,
            board: board,
            discarded_cards: discardedCardsArray
        };
    }

    updateGameStateAndSend() {
        const gameState = this.getGameStateFromDOM();
        const aiSettings = this.getAiSettings();

        fetch('/update_state', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...gameState, ai_settings: aiSettings })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error("Error updating game state:", data.error);
                alert("Error updating game state: " + data.error);
            }
        })
        .catch(error => {
            console.error('Error updating game state:', error);
            alert('An error occurred while updating the game state.');
        });
    }

    getAiSettings() {
        return {
            fantasyType: document.getElementById('fantasyType').value,
            fantasyMode: document.getElementById('fantasyMode').checked,
            aiTime: document.getElementById('aiTime').value,
            iterations: document.getElementById('iterations').value,
            stopThreshold: document.getElementById('stopThreshold').value,
            aiType: document.getElementById('aiType').value,
            placementMode: 'standard' // This is internal logic, not a setting
        };
    }

    distributeCards() {
        const gameState = this.getGameStateFromDOM();
        const numCards = gameState.selected_cards.length;

        if (numCards > 0) {
            const aiSettings = this.getAiSettings();
            const requestData = JSON.stringify({
                selected_cards: gameState.selected_cards,
                board: gameState.board,
                discarded_cards: gameState.discarded_cards,
                ai_settings: aiSettings
            });

            fetch('/ai_move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: requestData
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        throw new Error(`HTTP error! status: ${response.status}, text: ${text}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    return;
                }

                // Add all cards from the move to discardedCards
                if (data.move) {
                    for (const line in data.move) {
                        if (Array.isArray(data.move[line])) {
                            data.move[line].forEach(card => {
                                if (card) {
                                    this.discardedCards.add(`${card.rank}${card.suit}`);
                                }
                            });
                        }
                    }
                }
                this.board.placeCards(data.move);

                // Check if the game is over
                if (data.game_over) {
                    // Display royalties only at the end of the game
                    this.board.displayRoyalties(data.royalties);
                    this.displayTotalRoyalty(data.total_royalty);

                    // Show game over message
                    setTimeout(() => {
                        alert(`Game over! Total Royalty: ${data.total_royalty}`);
                    }, 500);
                } else {
                    // If the game is not over, clear the combination area and hide royalties
                    this.resetCombinationArea();
                    document.querySelectorAll('.royalty-animation').forEach(el => {
                        el.classList.remove('show');
                        el.textContent = '';
                    });
                    document.getElementById('total-royalty').textContent = '';
                }

                this.updateGameStateAndSend();
                gameState.selected_cards = []; // Clear selected_cards
                this.updateSelectorAvailability();
                this.updateTrainingProgress(); // Update progress after each move
            })
            .catch(error => {
                console.error('Error getting AI move:', error);
                alert('An error occurred while getting the AI move.');
            });
        } else {
            alert('Please select cards to add.');
        }
    }

    removeSelectedCards() {
        const removedCards = [];
        let slotsChanged = false;

        // Iterate over a copy to avoid issues with modifying the array during iteration
        const slotsCopy = [...this.combinationSlots];
        slotsCopy.forEach(slot => {
            const card = slot.getCard();
            if (card) {
                const cardKey = card.getCardKey();
                if (this.unavailableCards.has(cardKey)) {
                    this.unavailableCards.delete(cardKey);
                }
                this.discardedCards.add(cardKey); // Add to discardedCards
                removedCards.push({ rank: card.rank, suit: card.suit });
                slot.clear();
                slotsChanged = true;
            }
        });

        // Redistribute cards in slots after removal
        if (slotsChanged) {
            const filledSlots = this.combinationSlots.filter(slot => slot.getCard() !== null);
            this.combinationSlots.forEach(slot => slot.clear()); // Clear all
            filledSlots.forEach((slot, index) => {
                this.combinationSlots[index].setCard(slot.getCard()); // Refill
            });
        }

        this.updateSelectorAvailability();

        if (slotsChanged && removedCards.length > 0) {
            const gameState = this.getGameStateFromDOM();
            fetch('/update_state', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...gameState,
                    removed_cards: removedCards,
                    ai_settings: this.getAiSettings()
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    console.error("Error updating state:", data.error);
                    alert("Error updating state: " + data.error);
                }
            })
            .catch(error => {
                console.error('Error updating state:', error);
            });
        }
    }

    resetCombinationArea() {
        this.combinationSlots.forEach(slot => slot.clear());
        this.unavailableCards.clear();
        // this.discardedCards.clear(); // Don't clear discardedCards here
        this.updateSelectorAvailability();
    }

    resetTraining() {
        this.board.clear();
        this.resetCombinationArea();
        this.unavailableCards.clear();
        this.discardedCards.clear(); // Clear discardedCards on reset
        this.selectedRank = null;
        this.selectedSuit = null;
        document.querySelectorAll('.selector-item').forEach(el => el.classList.remove('selected', 'unavailable'));
        document.querySelectorAll('.royalty-animation').forEach(el => {
            el.classList.remove('show');
            el.textContent = '';
        });
        document.getElementById('total-royalty').textContent = '';

        this.updateGameStateAndSend(); // Send reset state to server
    }

    displayTotalRoyalty(totalRoyalty) {
        const totalRoyaltyElement = document.getElementById('total-royalty');
        totalRoyaltyElement.textContent = `Total Royalty: +${totalRoyalty}`;
    }

    saveSettings() {
        const aiSettings = this.getAiSettings();
        fetch('/update_state', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                selected_cards: [],
                board: { top: [], middle: [], bottom: [] },
                discarded_cards: [],
                removed_cards: [],
                ai_settings: aiSettings
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                alert('Настройки сохранены!');
                this.toggleMenu();
            } else {
                alert('Ошибка при сохранении настроек.');
            }
        })
        .catch(error => {
            console.error('Error saving settings:', error);
            alert('An error occurred while saving settings.');
        });
    }

    toggleMenu() {
        const menu = document.querySelector('.menu-panel');
        this.menuOpen = !this.menuOpen;
        menu.classList.toggle('open', this.menuOpen);
    }

    toggleFullScreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(err => {
                console.log(`Error attempting to enable full-screen mode: ${err.message}`);
            });
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            }
        }
    }
    updateTrainingProgress() {
        fetch('/training_progress')
            .then(response => response.json())
            .then(data => {
                document.getElementById('progress-value').textContent = (data.progress * 100).toFixed(2);
            });
    }
    resetAI(){
        fetch('/reset_training', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('Обучение AI сброшено!');
                    this.updateTrainingProgress(); // Обновляем прогресс
                } else {
                    alert('Ошибка при сбросе обучения AI: ' + (data.error || 'Неизвестная ошибка'));
                }
            })
            .catch(error => {
                console.error('Error resetting AI training:', error);
                alert('Произошла ошибка при сбросе обучения AI.');
            });
    }
}

// Убедитесь, что код выполняется после загрузки DOM
document.addEventListener('DOMContentLoaded', () => {
     let game = new Game();
     game.init();
});
