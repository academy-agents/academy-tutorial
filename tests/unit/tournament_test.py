from __future__ import annotations

import asyncio
import warnings

import pytest
from academy.agent import action
from academy.handle import ProxyHandle

from academy_tutorial.battleship import Board
from academy_tutorial.battleship import Crd
from academy_tutorial.tournament import TournamentAgent
from testing.agents import MyBattleshipPlayer


@pytest.mark.asyncio
async def test_register_player():
    player = ProxyHandle(MyBattleshipPlayer())
    tournament = TournamentAgent()

    await tournament.register_player(player, 'me')

    player_2 = ProxyHandle(MyBattleshipPlayer())
    with pytest.raises(AssertionError, match='name has been registered'):
        await tournament.register_player(player_2, 'me')

    await tournament.register_player(player_2, 'you')

    players = await tournament.get_players()
    assert len(players) == 2  # noqa: PLR2004
    assert players[0]['win_rate'] == 0


def test_matching():
    players = ['velma', 'fred', 'shaggy', 'scooby', 'daphne']
    tournament = TournamentAgent()
    round_1 = set(tournament._matching(players, 1))
    assert len(round_1) == 2  # noqa: PLR2004

    round_2 = set(tournament._matching(players, 2))
    assert len(round_2) == 2  # noqa: PLR2004
    for matchup in round_1:
        assert matchup not in round_2


def test_matching_one_player():
    players = ['velma']
    tournament = TournamentAgent()
    round_1 = set(tournament._matching(players, 1))
    assert len(round_1) == 0


def test_matching_too_short():
    players = ['velma', 'fred']
    tournament = TournamentAgent()
    round_2 = set(tournament._matching(players, 2))
    assert len(round_2) == 0


@pytest.mark.asyncio
async def test_game():
    player = ProxyHandle(MyBattleshipPlayer())
    player_2 = ProxyHandle(MyBattleshipPlayer())
    tournament = TournamentAgent()
    shutdown_event = asyncio.Event()

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        winner = await tournament.play_game(shutdown_event, player, player_2)

    assert winner in {0, 1}


class SlowPlayer(MyBattleshipPlayer):
    @action
    async def new_game(self, ships, size=10) -> Board:
        await asyncio.sleep(0.2)
        return await super().new_game(ships, size)


@pytest.mark.asyncio
async def test_test_player_slow():
    tournament = TournamentAgent()
    slow = ProxyHandle(SlowPlayer())
    with pytest.raises(TimeoutError):
        await tournament.register_player(slow, 'slow')


@pytest.mark.asyncio
async def test_play_game_init_timeout():
    tournament = TournamentAgent()
    slow = ProxyHandle(SlowPlayer())
    player = ProxyHandle(MyBattleshipPlayer())
    shutdown_event = asyncio.Event()
    with pytest.warns(UserWarning, match='raised exception'):
        winner = await tournament.play_game(shutdown_event, player, slow)
    assert winner == 0

    with pytest.warns(UserWarning, match='raised exception'):
        winner = await tournament.play_game(shutdown_event, slow, player)
    assert winner == 1


class ExceptionPlayer(MyBattleshipPlayer):
    @action
    async def get_move(self) -> Crd:
        raise ValueError('Mistake')


@pytest.mark.asyncio
async def test_play_game_exception():
    tournament = TournamentAgent()
    player = ProxyHandle(MyBattleshipPlayer())
    bad = ProxyHandle(ExceptionPlayer())
    shutdown_event = asyncio.Event()
    with pytest.warns(UserWarning, match='raised exception'):
        winner = await tournament.play_game(shutdown_event, player, bad)
    assert winner == 0

    with pytest.warns(UserWarning, match='raised exception'):
        winner = await tournament.play_game(shutdown_event, bad, player)
    assert winner == 1


@pytest.mark.asyncio
async def test_play_tournament():
    tournament = TournamentAgent()
    for i in range(8):
        player = ProxyHandle(MyBattleshipPlayer())
        await tournament.register_player(player, f'player-{i}')

    shutdown_event = asyncio.Event()
    task = asyncio.create_task(tournament.play_tournament(shutdown_event))
    await asyncio.sleep(0.1)

    for i in range(8, 16):
        player = ProxyHandle(MyBattleshipPlayer())
        await tournament.register_player(player, f'player-{i}')

    await asyncio.sleep(1.0)

    assert tournament.round_num > 1
    players = await tournament.get_players()

    assert players[0]['win_rate'] > 0
    for i in range(15):
        assert players[i]['win_rate'] >= players[i + 1]['win_rate']

    shutdown_event.set()
    await task
