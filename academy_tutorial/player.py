from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Literal

from academy.agent import action
from academy.agent import Agent

from academy_tutorial.battleship import Board
from academy_tutorial.battleship import Crd


class BattleshipPlayer(Agent, ABC):
    """Abstract base class of BattleshipPlayer."""

    def __init__(
        self,
    ) -> None:
        super().__init__()

    @action
    @abstractmethod
    async def get_move(self) -> Crd:
        """Return a guess of where an opposing ship is."""
        ...

    @action
    async def notify_result(
        self,
        loc: Crd,
        result: Literal['hit', 'miss', 'guessed'],
    ) -> None:
        """Called to notify player of result of last move."""
        return

    @action
    async def notify_move(self, loc: Crd) -> None:
        """Called to notify player of opponents guess."""
        return

    @action
    @abstractmethod
    async def new_game(self, ships: list[int], size: int = 10) -> Board:
        """Reset state of player.

        Args:
            ships: List of lengths of ships to place.
            size: Size of board to return.

        Returns:
            A board with all of the ships placed.
        """
        ...
