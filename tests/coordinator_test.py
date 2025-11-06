from __future__ import annotations

from academy.handle import ProxyHandle

from academy_tutorial.coordinator import Coordinator
from testing.agents import MyBattleshipPlayer


def test_coordinator_init():
    player_0 = ProxyHandle(MyBattleshipPlayer())
    player_1 = ProxyHandle(MyBattleshipPlayer())

    Coordinator(player_0, player_1)
