from __future__ import annotations

import asyncio

import pytest
from academy.handle import ProxyHandle

from academy_tutorial.coordinator import Coordinator
from testing.agents import MyBattleshipPlayer


@pytest.fixture
def coordinator() -> Coordinator:
    player_0 = ProxyHandle(MyBattleshipPlayer())
    player_1 = ProxyHandle(MyBattleshipPlayer())

    coordinator = Coordinator(player_0, player_1)
    return coordinator


@pytest.mark.asyncio
async def test_coordinator_init(coordinator):
    assert coordinator.ships == Coordinator._default_ships

    state = await coordinator.get_game_state()
    assert state is None

    stats = await coordinator.get_player_stats()
    assert len(stats) == 2  # noqa: PLR2004
    assert stats[0] == 0
    assert stats[1] == 0


@pytest.mark.asyncio
async def test_coordinator_game(coordinator):
    shutdown_event = asyncio.Event()
    winner = await coordinator.game(shutdown_event)
    assert winner in {0, 1}

    state = await coordinator.get_game_state()
    assert state is not None
    assert state.check_winner() == winner

    loser = 1 - winner
    assert state.boards[loser].all_ships_sunk()
