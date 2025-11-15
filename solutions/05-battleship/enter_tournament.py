from __future__ import annotations

import argparse
import asyncio
import logging
import os
import uuid
from typing import Literal

from academy.agent import action
from academy.exchange.cloud import HttpExchangeFactory
from academy.handle import Handle
from academy.identifier import AgentId
from academy.manager import Manager

from academy_tutorial.battleship import Board
from academy_tutorial.battleship import Crd
from academy_tutorial.player import BattleshipPlayer

EXCHANGE_ADDRESS = 'https://exchange.academy-agents.org'
logger = logging.getLogger(__name__)


class MyBattleshipPlayer(BattleshipPlayer):
    def __init__(
        self,
    ) -> None:
        from academy_tutorial.battleship import Board  # noqa: PLC0415

        super().__init__()
        self.guesses = Board()

    @action
    async def get_move(self) -> Crd:
        import random  # noqa: PLC0415

        from academy_tutorial.battleship import Crd  # noqa: PLC0415

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
    ) -> None:
        # Naive player does not keep track of results
        return

    @action
    async def notify_move(self, loc: Crd) -> None:
        # Naive player does not keep track of where guesses
        # happen
        return

    @action
    async def new_game(self, ships: list[int], size: int = 10) -> Board:
        from academy_tutorial.battleship import Board  # noqa: PLC0415
        from academy_tutorial.battleship import Crd  # noqa: PLC0415

        self.guesses = Board(size)
        my_board = Board(size)
        for i, ship in enumerate(ships):
            my_board.place_ship(Crd(i, 0), ship, 'horizontal')
        return my_board


async def main(name: str) -> int:
    group_id = uuid.UUID(os.environ['ACADEMY_TUTORIAL_GROUP'])

    tournament_aid = AgentId(
        uid=uuid.UUID(os.environ['ACADEMY_TUTORIAL_TOURNAMENT_AGENT']),
    )

    factory = HttpExchangeFactory(
        EXCHANGE_ADDRESS,
        auth_method='globus',
    )
    async with await Manager.from_exchange_factory(
        factory=factory,
    ) as manager:
        console = await factory.console()
        player_hdl = await manager.launch(MyBattleshipPlayer)
        await player_hdl.ping()

        await console.share_mailbox(manager.user_id, group_id)
        await console.share_mailbox(player_hdl.agent_id, group_id)

        tournament = Handle(tournament_aid)
        await tournament.register_player(player_hdl, name)

        while True:
            rankings = await tournament.get_players()
            print('==================== Rankings ====================')
            for i, player in enumerate(rankings):
                print(
                    f'{i}) {player["name"]}\tPercentage: {player["win_rate"]}',
                )
            await asyncio.sleep(30)

    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Enter the battleship tournament',
    )
    parser.add_argument(
        '--name',
        '-n',
        required=True,
        help='Display name for your battleship player',
    )
    args = parser.parse_args()

    raise SystemExit(asyncio.run(main(args.name)))
