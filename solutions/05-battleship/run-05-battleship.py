from __future__ import annotations

import asyncio
import logging
import random
from typing import ClassVar, Literal

from academy.agent import action
from academy.agent import Agent
from academy.agent import loop
from academy.exchange.cloud import HttpExchangeFactory
from academy.handle import Handle
from academy.logging import init_logging
from academy.manager import Manager
from globus_compute_sdk import Executor

from academy_tutorial.battleship import Board
from academy_tutorial.battleship import Crd
from academy_tutorial.battleship import Game

EXCHANGE_ADDRESS = 'https://exchange.proxystore.dev'
TUTORIAL_ENDPOINT_UUID = '707fe7ed-6f06-4ec3-877f-1c1f0e9aeb84'
logger = logging.getLogger(__name__)


class BattleshipPlayer(Agent):
    def __init__(
        self,
    ) -> None:
        from academy_tutorial.battleship import Board

        super().__init__()
        self.guesses = Board()

    @action
    async def get_move(self) -> Crd:
        from academy_tutorial.battleship import Crd
        import asyncio
        import random

        await asyncio.sleep(1)
        while True:
            row = random.randint(0, self.guesses.size - 1)
            col = random.randint(0, self.guesses.size - 1)
            if self.guesses.receive_attack(Crd(row, col)) != 'guessed':
                return Crd(row, col)
    
    @action
    async def notify_result(self, loc: Crd, result: Literal["hit", "miss", "guessed"]):
        # Naive player does not keep track of results
        return 

    @action
    async def notify_move(self, loc: Crd) -> None:
        # Naive player does not keep track of where guesses
        # happen
        return

    @action
    async def new_game(self, ships: list[int], size: int = 10) -> Board:
        from academy_tutorial.battleship import Board
        from academy_tutorial.battleship import Crd

        self.guesses = Board(size)
        my_board = Board(size)
        for i, ship in enumerate(ships):
            my_board.place_ship(Crd(i, 0), ship, 'horizontal')
        return my_board


class Coordinator(Agent):
    _default_ships: ClassVar[list[int]] = [5, 5, 4, 3, 2]

    def __init__(
        self,
        player_0: Handle[BattleshipPlayer],
        player_1: Handle[BattleshipPlayer],
        *,
        size: int = 10,
        ships: list[int] | None = None,
    ) -> None:
        from academy_tutorial.battleship import Board
        from academy_tutorial.battleship import Game

        super().__init__()
        self.player_0 = player_0
        self.player_1 = player_1
        self.game_state = Game(Board(), Board())
        self.ships = ships or self._default_ships
        self.stats = [0, 0]

    async def game(self, shutdown: asyncio.Event) -> int:
        while not shutdown.is_set():
            attack = await (await self.player_0.get_move())
            result = self.game_state.attack(0, attack)
            await (await self.player_0.notify_result(attack, result))
            await (await self.player_1.notify_move(attack))
            if self.game_state.check_winner() >= 0:
                return self.game_state.check_winner()

            attack = await (await self.player_1.get_move())
            result = self.game_state.attack(1, attack)
            await (await self.player_1.notify_result(attack, result))
            await (await self.player_0.notify_move(attack))
            if self.game_state.check_winner() >= 0:
                return self.game_state.check_winner()

        return -1

    @loop
    async def play_games(self, shutdown: asyncio.Event) -> None:
        from academy_tutorial.battleship import Board
        from academy_tutorial.battleship import Game
        
        while not shutdown.is_set():
            player_0_board = await (await self.player_0.new_game(self.ships))
            player_1_board = await (await self.player_1.new_game(self.ships))
            self.game_state = Game(player_0_board, player_1_board)
            winner = await self.game(shutdown)
            self.stats[winner] += 1

    @action
    async def get_game_state(self) -> Game | None:
        return self.game_state

    @action
    async def get_player_stats(self) -> list[int]:
        return self.stats


async def main() -> int:
    init_logging(logging.INFO)

    # Use the chameleon instance for execution.
    executor = Executor(TUTORIAL_ENDPOINT_UUID)

    # Use the hosted exchange with globus auth.
    factory = HttpExchangeFactory(
        url=EXCHANGE_ADDRESS,
        auth_method='globus',
    )

    async with await Manager.from_exchange_factory(
        factory=factory,
        # Agents are run by the manager in the processes of this
        # process pool executor.
        executors=executor,
    ) as manager:
        # Launch each of the three agents, each implementing a different
        # behavior. The returned type is a handle to that agent used to
        # invoke actions.
        player_1 = await manager.launch(BattleshipPlayer)
        player_2 = await manager.launch(BattleshipPlayer)
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
                print('Exiting... attempting shutdown')
                await coordinator.shutdown()
                await player_1.shutdown()
                await player_2.shutdown()
                break
            elif user_input.lower() == 'game':
                game = await (await coordinator.get_game_state())
                print('Current Game State: ')
                print(game)
            elif user_input.lower() == 'stat':
                stats = await (await coordinator.get_player_stats())
                print(f'Player 0 has won {stats[0]} games')
                print(f'Player 1 has won {stats[1]} games')
            else:
                print('Unknown command')
            print('-----------------------------------------------------')

        # Upon exit, the Manager context will instruct each agent to shutdown,
        # closing their respective handles, and shutting down the executors.

    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
