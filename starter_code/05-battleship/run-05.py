from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from typing import Literal

from academy.agent import action
from academy.exchange.cloud import HttpExchangeFactory
from academy.logging import init_logging
from academy.manager import Manager
from globus_compute_sdk import Executor as GCExecutor

from academy_tutorial.battleship import Board
from academy_tutorial.battleship import Crd
from academy_tutorial.coordinator import Coordinator
from academy_tutorial.player import BattleshipPlayer

EXCHANGE_ADDRESS = 'https://exchange.academy-agents.org'

logger = logging.getLogger(__name__)


class MyBattleshipPlayer(BattleshipPlayer):
    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.guesses = Board()

    @action
    async def get_move(self) -> Crd:
        """Choose a new attack.

        Returns:
            The coordinates to launch an attack.
        """

        # TODO: Implement an attack strategy

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
        """Start a new game.

        Args:
            ships: The list of ships to place.
            size: The size of the board.

        Returns:
            A new board with all the ships placed.
        """

        # TODO: Implement a strategy for placing the ships


async def main() -> int:
    init_logging(logging.INFO)

    if 'ACADEMY_TUTORIAL_ENDPOINT' in os.environ:
        executor = GCExecutor(os.environ['ACADEMY_TUTORIAL_ENDPOINT'])
    else:
        mp_context = multiprocessing.get_context('spawn')
        executor = ProcessPoolExecutor(
            max_workers=3,
            initializer=init_logging,
            mp_context=mp_context,
        )

    async with await Manager.from_exchange_factory(
        factory=HttpExchangeFactory(
            EXCHANGE_ADDRESS,
            auth_method='globus',
        ),
        executors=executor,
    ) as manager:
        player_1 = await manager.launch(MyBattleshipPlayer)
        player_2 = await manager.launch(MyBattleshipPlayer)
        coordinator = await manager.launch(
            Coordinator,
            args=(player_1, player_2),
        )

        loop = asyncio.get_event_loop()
        while True:
            user_input = await loop.run_in_executor(
                None,
                input,
                'Enter command (exit, game, stat): ',
            )
            if user_input.lower() == 'exit':
                print('Exiting...')
                break
            elif user_input.lower() == 'game':
                game = await coordinator.get_game_state()
                print('Current Game State: ')
                print(game)
            elif user_input.lower() == 'stat':
                stats = await coordinator.get_player_stats()
                print(f'Player 0 has won {stats[0]} games')
                print(f'Player 1 has won {stats[1]} games')
            else:
                print('Unknown command')
            print('-----------------------------------------------------')

    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
