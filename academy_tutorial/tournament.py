from __future__ import annotations

import asyncio
import random
import warnings
from collections.abc import Iterable
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import ClassVar

from academy.agent import action
from academy.agent import Agent
from academy.agent import loop
from academy.handle import Handle

from academy_tutorial.battleship import Game
from academy_tutorial.player import BattleshipPlayer


@dataclass
class PlayerInfo:
    """Information for a registered player."""

    player: Handle[BattleshipPlayer]
    wins: int = 0
    losses: int = 0
    games: int = 0
    previous_matchups: list[tuple[str, int]] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        """Proportion of games won."""
        return self.wins / self.games if self.games > 0 else 0


class TournamentAgent(Agent):
    """Play battleship agents against one another."""

    timeout: ClassVar[float] = 0.1
    ships: ClassVar[list[int]] = [5, 5, 4, 3, 2]

    def __init__(self) -> None:
        super().__init__()
        self.registered_players: dict[str, PlayerInfo] = {}
        self.matchups: list[tuple[str, str]] = []
        self.round_num = 1
        self.round_lock = asyncio.Lock()
        self.new_players = asyncio.Condition()

    async def test_player(self, player: Handle[BattleshipPlayer]) -> None:
        """Test if player completes necessary methods.

        Raises:
            TimeoutError if player in unavailable or slow.
        """
        await asyncio.wait_for(player.ping(), self.timeout)
        await asyncio.wait_for(player.new_game(self.ships), self.timeout)
        await asyncio.wait_for(player.get_move(), self.timeout)

    @action
    async def register_player(
        self,
        player: Handle[BattleshipPlayer],
        name: str,
    ) -> None:
        """Register a player for the tournament."""
        await self.test_player(player)
        assert name not in self.registered_players, (
            'Player name has been registered. Choose another display name.'
        )
        async with self.new_players:
            self.registered_players[name] = PlayerInfo(player)
            self.round_num = 1  # Reset round num so everyone plays everyone

            # Shuffle players so we don't get stuck with the same matchups
            players = list(self.registered_players.items())
            random.shuffle(players)
            self.registered_players = dict(players)
            self.new_players.notify()

    @action
    async def get_players(self) -> list[dict[str, Any]]:
        """Return a ranked list of the players."""
        players = [
            {
                'name': name,
                'wins': info.wins,
                'games': info.games,
                'win_rate': info.win_rate,
                'record': info.previous_matchups,
            }
            for name, info in self.registered_players.items()
        ]
        return sorted(players, key=lambda x: x['win_rate'], reverse=True)

    @action
    async def get_current_matchups(self) -> list[tuple[str, str]]:
        """Return the activate matchups."""
        return self.matchups

    def _matching(
        self,
        players: list[str],
        round_num: int,
    ) -> Iterable[tuple[str, str]]:
        """Match players for next round.

        Currently we use a round robin system. In the future we might
        implement a swiss system.
        """
        if round_num >= len(players):
            return []

        players_rotated = players[1:]
        players_rotated = (
            players_rotated[-round_num:] + players_rotated[:-round_num]
        )
        players = players[:1] + players_rotated

        n_games = len(players) // 2
        matchups = zip(players[:n_games], players[n_games:])
        return matchups

    async def play_game(  # noqa: C901, PLR0911
        self,
        shutdown: asyncio.Event,
        player_0: Handle[BattleshipPlayer],
        player_1: Handle[BattleshipPlayer],
    ) -> int:
        """Play players against each other in single game."""
        try:
            player_0_board = await asyncio.wait_for(
                player_0.new_game(self.ships),
                self.timeout,
            )
            if sorted([s.length for s in player_0_board.ships]) != sorted(
                self.ships,
            ):
                warnings.warn(
                    'Player 0 returned an invalid board.',
                    stacklevel=1,
                )
                return 1
        except Exception as e:
            warnings.warn(
                f'Player 0 raised exception {e}, player 1 wins.',
                stacklevel=1,
            )
            return 1

        try:
            player_1_board = await asyncio.wait_for(
                player_1.new_game(self.ships),
                self.timeout,
            )
            if sorted([s.length for s in player_1_board.ships]) != sorted(
                self.ships,
            ):
                return 0
        except Exception as e:
            warnings.warn(
                f'Player 1 raised exception {e}, player 0 wins.',
                stacklevel=1,
            )
            return 0

        game_state = Game(player_0_board, player_1_board)
        while not shutdown.is_set():
            try:
                attack = await asyncio.wait_for(
                    player_0.get_move(),
                    timeout=self.timeout,
                )
                result = game_state.attack(0, attack)
                await asyncio.wait_for(
                    player_0.notify_result(attack, result),
                    timeout=self.timeout,
                )
            except Exception as e:
                warnings.warn(
                    f'Player 0 raised exception {e}, player 1 wins.',
                    stacklevel=1,
                )
                return 1

            if game_state.check_winner() >= 0:
                return game_state.check_winner()

            try:
                await asyncio.wait_for(
                    player_1.notify_move(attack),
                    timeout=self.timeout,
                )
                attack = await asyncio.wait_for(
                    player_1.get_move(),
                    timeout=self.timeout,
                )
                result = game_state.attack(1, attack)
                await asyncio.wait_for(
                    player_1.notify_result(attack, result),
                    timeout=self.timeout,
                )
            except Exception as e:
                warnings.warn(
                    f'Player 1 raised exception {e}, player 0 wins.',
                    stacklevel=1,
                )
                return 0

            if game_state.check_winner() >= 0:
                return game_state.check_winner()

            try:
                await asyncio.wait_for(
                    player_0.notify_move(attack),
                    timeout=self.timeout,
                )
            except Exception as e:
                warnings.warn(
                    f'Player 0 raised exception {e}, player 1 wins.',
                    stacklevel=1,
                )
                return 1

            await asyncio.sleep(0.0)

        return -1

    @loop
    async def play_tournament(self, shutdown: asyncio.Event) -> None:
        """Continuously play games in tournament."""
        while not shutdown.is_set():
            # Get the current players for the round
            async with self.new_players:
                while True:
                    cur_players = list(self.registered_players.keys())
                    self.matchups = list(
                        self._matching(cur_players, self.round_num),
                    )
                    if len(self.matchups) > 0:
                        break
                    else:
                        await self.new_players.wait()

                self.round_num += 1

            task_map: dict[asyncio.Task[Any], tuple[str, str]] = {}
            for matchup in self.matchups:
                (player_1_name, player_2_name) = matchup
                player_1 = self.registered_players[player_1_name].player
                player_2 = self.registered_players[player_2_name].player
                task = asyncio.create_task(
                    self.play_game(shutdown, player_1, player_2),
                )
                task_map[task] = matchup

            await asyncio.wait(task_map.keys())

            for task, matchup in task_map.items():
                if task.result() == -1:  # Game was skipped
                    continue

                winner_name = matchup[task.result()]
                loser_name = matchup[1 - task.result()]

                winner = self.registered_players[winner_name]
                winner.wins += 1
                winner.games += 1
                winner.previous_matchups.append((loser_name, 1))

                loser = self.registered_players[loser_name]
                loser.losses += 1
                loser.games += 1
                loser.previous_matchups.append((winner_name, 0))

            await asyncio.sleep(0.1)  # Rate limit between rounds.
