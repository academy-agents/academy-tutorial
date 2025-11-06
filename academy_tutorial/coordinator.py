from __future__ import annotations

import asyncio
from typing import ClassVar

from academy.agent import action
from academy.agent import Agent
from academy.agent import loop
from academy.handle import Handle

from academy_tutorial.battleship import Board
from academy_tutorial.battleship import Game
from academy_tutorial.player import BattleshipPlayer


class Coordinator(Agent):
    """Simple coordinator of battleship games.

    Args:
        player_0: First player in game.
        player_1: Second player in game.
        size: Size of board.
        ships: The ships that each player uses. Defaults to
            self._default_ships
    """

    _default_ships: ClassVar[list[int]] = [5, 5, 4, 3, 2]

    def __init__(
        self,
        player_0: Handle[BattleshipPlayer],
        player_1: Handle[BattleshipPlayer],
        *,
        size: int = 10,
        ships: list[int] | None = None,
    ) -> None:
        super().__init__()
        self.player_0 = player_0
        self.player_1 = player_1
        self.game_state = Game(Board(), Board())
        self.ships = ships or self._default_ships
        self.stats = [0, 0]

    async def game(self, shutdown: asyncio.Event) -> int:
        """Play a single game between the players."""
        while not shutdown.is_set():
            attack = await self.player_0.get_move()
            result = self.game_state.attack(0, attack)
            await self.player_0.notify_result(attack, result)
            await self.player_1.notify_move(attack)
            if self.game_state.check_winner() >= 0:
                return self.game_state.check_winner()

            attack = await self.player_1.get_move()
            result = self.game_state.attack(1, attack)
            await self.player_1.notify_result(attack, result)
            await self.player_0.notify_move(attack)
            if self.game_state.check_winner() >= 0:
                return self.game_state.check_winner()

        return -1

    @loop
    async def play_games(self, shutdown: asyncio.Event) -> None:
        """Play a games until the agent is shutdown."""
        while not shutdown.is_set():
            player_0_board = await self.player_0.new_game(self.ships)
            player_1_board = await self.player_1.new_game(self.ships)
            self.game_state = Game(player_0_board, player_1_board)
            winner = await self.game(shutdown)
            self.stats[winner] += 1

    @action
    async def get_game_state(self) -> Game | None:
        """Return the state of the current game being played."""
        return self.game_state

    @action
    async def get_player_stats(self) -> list[int]:
        """Get the number of wins of each player."""
        return self.stats
