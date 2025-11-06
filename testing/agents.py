from __future__ import annotations

import random
from typing import Literal

from academy.agent import action

from academy_tutorial.battleship import Board
from academy_tutorial.battleship import Crd
from academy_tutorial.player import BattleshipPlayer


class MyBattleshipPlayer(BattleshipPlayer):
    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.guesses = Board()

    @action
    async def get_move(self) -> Crd:
        while True:
            row = random.randint(0, self.guesses.size - 1)
            col = random.randint(0, self.guesses.size - 1)
            if self.guesses.receive_attack(Crd(row, col)) != 'guessed':
                return Crd(row, col)

    @action
    async def notify_result(
        self,
        loc: Crd,
        result: Literal['hit', 'miss', 'guessed'],
    ):
        return

    @action
    async def notify_move(self, loc: Crd) -> None:
        return

    @action
    async def new_game(self, ships: list[int], size: int = 10) -> Board:
        self.guesses = Board(size)
        my_board = Board(size)
        for i, ship in enumerate(ships):
            my_board.place_ship(Crd(i, 0), ship, 'horizontal')
        return my_board
