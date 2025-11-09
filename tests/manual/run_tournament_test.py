from __future__ import annotations

import asyncio
import logging
import random
from typing import Literal

from academy.agent import action
from academy.exchange import HttpExchangeFactory
from academy.exchange.cloud.client import spawn_http_exchange
from academy.socket import open_port
from academy.logging import init_logging
from academy.manager import Manager

from academy_tutorial.battleship import Board
from academy_tutorial.battleship import Crd
from academy_tutorial.player import BattleshipPlayer
from academy_tutorial.tournament import TournamentAgent

logger = logging.getLogger()


class MyBattleshipPlayer(BattleshipPlayer):
    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.not_guessed: set[Crd] = set()

    @action
    async def get_move(self) -> Crd:
        guess = random.choice(list(self.not_guessed))
        self.not_guessed.remove(guess)
        return guess

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
        self.not_guessed = {
            Crd(i, j) for i in range(size) for j in range(size)
        }
        my_board = Board(size)
        for i, ship in enumerate(ships):
            my_board.place_ship(Crd(i, 0), ship, 'horizontal')
        return my_board


async def main():
    init_logging(logging.INFO)
    with spawn_http_exchange("localhost", open_port()) as factory:
        async with await Manager.from_exchange_factory(
            factory=factory,
        ) as manager:
            tournament = await manager.launch(TournamentAgent)

            players = []
            for i in range(4):
                player = await manager.launch(MyBattleshipPlayer)
                await player.ping()
                players.append(player)
                await tournament.register_player(player, f'player-{i}')
                await asyncio.sleep(0.2)

            await asyncio.sleep(1)
            # import pdb; pdb.set_trace()
            rankings = await tournament.get_players()
            for i, player in enumerate(rankings):
                print(
                    f'{i}. {player["name"]}:\tWins: {player["wins"]}'
                    f'\tGames: {player["games"]}'
                    f'\tWin Rate: {player["win_rate"]}',
                )
            for player in players:
                await player.shutdown()

            for i in range(4, 8):
                player = await manager.launch(MyBattleshipPlayer)
                await player.ping()
                logger.info('Registering player.')
                await tournament.register_player(player, f'player-{i}')
                logger.info('Player registered.')
                # await asyncio.sleep(0.0)

            await asyncio.sleep(3)
            rankings = await tournament.get_players()
            for i, player in enumerate(rankings):
                print(
                    f'{i}. {player["name"]}:\tWins: {player["wins"]}'
                    f'\tGames: {player["games"]}'
                    f'\tWin Rate: {player["win_rate"]}',
                )


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
