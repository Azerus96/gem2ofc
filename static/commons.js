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
