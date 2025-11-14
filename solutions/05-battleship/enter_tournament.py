from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Literal

from academy.agent import action
from academy.exchange.cloud import HttpExchangeFactory
from academy.handle import Handle
from academy.identifier import AgentId
from academy.logging import init_logging
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


async def main() -> int:
    init_logging(logging.INFO)
    factory = HttpExchangeFactory(
        EXCHANGE_ADDRESS,
        auth_method='globus',
    )
    async with await Manager.from_exchange_factory(
        factory=factory,
    ) as manager:
        console = await factory.console()
        player = await manager.launch(MyBattleshipPlayer)
        group_id = uuid.UUID('47697db5-c19f-11f0-981f-0ee9d7d7fffb')
        await player.ping()

        await console.share_mailbox(manager.user_id, group_id)
        await console.share_mailbox(player.agent_id, group_id)

        tournament_aid = AgentId(
            uid=uuid.UUID('a6a33dd5-1892-4e48-a2fc-cd7c1ec5a82f'),
        )
        tournament = Handle(tournament_aid)
        await tournament.register_player(player, 'dummy1')

        await manager.wait((player,))

    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
