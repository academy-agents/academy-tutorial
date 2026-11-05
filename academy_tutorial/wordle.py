from __future__ import annotations

import logging
import random
from collections import Counter

logger = logging.getLogger(__name__)


def score_guess(guess: str, target: str) -> list[str] | str:
    """Return per-letter Wordle feedback for a guess against a target.

    Each position in the returned list contains one of three values:
    - "correct":  letter is in the correct position (green)
    - "present":  letter is in the target but in the wrong position (yellow)
    - "absent":   letter is not in the target (grey)

    Duplicate letters are handled consistently with standard Wordle rules:
    correct-position matches are allocated first, then remaining target letters
    are matched left-to-right for "present" results.

    Args:
        guess: The guessed word (must be same length as target).
        target: The target word.

    Returns:
        A list of feedback strings, one per letter in guess, or an error
        message if the guess and target have different lengths.
    """
    guess = guess.lower()
    target = target.lower()

    if len(guess) != len(target):
        return f'Guess must be {len(target)} characters, got {len(guess)}'

    result = ['absent'] * len(guess)
    remaining: Counter[str] = Counter()

    # First pass: mark correct positions, track remaining target letters.
    for i, (g, t) in enumerate(zip(guess, target)):
        if g == t:
            result[i] = 'correct'
        else:
            remaining[t] += 1

    # Second pass: mark present letters using remaining quota.
    for i, g in enumerate(guess):
        if result[i] == 'absent' and remaining[g] > 0:
            result[i] = 'present'
            remaining[g] -= 1

    return result


TARGET_WORDS = [
    'trice',
    'knoll',
    'smite',
    'tacit',
    'atoll',
    'piney',
]


class WordleGame:
    """Instance of a wordle game."""

    def __init__(self):
        self.target = random.choice(TARGET_WORDS)

    def make_guess(self, guess: str) -> list[str] | str:
        """Return per-letter Wordle feedback for a guess.

        Each position in the returned list contains one of three values:
        - "correct":  letter is in the correct position (green)
        - "present":  letter is in the target but in the wrong spot (yellow)
        - "absent":   letter is not in the target (grey)

        Args:
            guess: The guessed 5-letter word.

        Returns:
            A list of feedback strings, one per letter in guess.
        """
        logger.info(f'Evaluating wordle guess: {guess.lower()}')
        return score_guess(guess, self.target)
