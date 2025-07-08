from __future__ import annotations

from typing import Literal
from typing import NamedTuple


class Crd(NamedTuple):
    """Coordinate structure."""

    x: int
    y: int


class Ship:
    """Structure to represent a battleship."""

    def __init__(self, positions: list[Crd]):
        """Structure to represent a battleship.

        Args:
            length: Number of slots on the ship.
            positions: Coordinates of ship.
        """
        self.length = len(positions)
        self.positions = positions  # e.g., [(2,3), (2,4), (2,5)]
        self.hits: set[Crd] = set()

    def register_hit(self, pos: Crd) -> None:
        """Add a hit to this ship.

        Args:
            pos: Position of the attack.
        """
        if pos in self.positions:
            self.hits.add(pos)

    @property
    def is_sunk(self) -> bool:
        """Check if ship is sunk."""
        return len(self.hits) == self.length

    def __repr__(self) -> str:
        return f'<Ship length={self.length} sunk={self.is_sunk}>'


class Board:
    """Battleship game board."""

    def __init__(self, size: int = 10):
        """Initialize an empty board of size.

        Args:
            size: The number of slots in one dimension of board.
        """
        self.size = size
        self.ships: list[Ship] = []
        self.guesses: set[Crd] = set()  # all shots made on this board

    def place_ship(
        self,
        start: Crd,
        length: int,
        direction: Literal['horizontal', 'vertical'],
    ) -> Ship | None:
        """Place a ship starting at `start` with length and direction.

        Args:
            start: Start coordinate of the ship with format (row, col).
            length: Number of slots of ship.
            direction: Orientation of ship as horizontal or vertical.

        Returns:
            The ship if placed successfully, or None if invalid placement.
        """
        row, col = start
        positions: list[Crd] = []

        if direction == 'horizontal':
            if col + length > self.size:
                return None  # out of bounds
            positions = [Crd(row, col + i) for i in range(length)]
        elif direction == 'vertical':
            if row + length > self.size:
                return None  # out of bounds
            positions = [Crd(row + i, col) for i in range(length)]
        else:
            raise ValueError(
                "Invalid direction, must be 'horizontal' or 'vertical'.",
            )

        # check for overlaps with existing ships
        for s in self.ships:
            if set(positions) & set(s.positions):
                return None  # conflict

        ship = Ship(positions)
        self.ships.append(ship)
        return ship

    def receive_attack(self, pos: Crd) -> Literal['hit', 'miss', 'guessed']:
        """Mark an attack on the board.

        Args:
            pos: Coordinate of attack.

        Returns:
            'hit', 'miss', or 'guessed'
        """
        if pos in self.guesses:
            return 'guessed'

        self.guesses.add(pos)

        for ship in self.ships:
            if pos in ship.positions:
                ship.register_hit(pos)
                return 'hit'
        return 'miss'

    def all_ships_sunk(self) -> bool:
        """Check if the board has remaining ships."""
        return all(ship.is_sunk for ship in self.ships)

    def __repr__(self) -> str:
        grid = [['.' for _ in range(self.size)] for _ in range(self.size)]

        # place ships
        for ship in self.ships:
            for pos in ship.positions:
                row, col = pos
                grid[row][col] = 'S'

        # place hits and misses
        for guess in self.guesses:
            row, col = guess
            for ship in self.ships:
                if guess in ship.positions:
                    grid[row][col] = 'H'
                    break
            else:
                grid[row][col] = 'M'

        # build string representation
        result = '  ' + ' '.join(str(c) for c in range(self.size)) + '\n'
        for r in range(self.size):
            result += str(r) + ' ' + ' '.join(grid[r]) + '\n'
        return result


class Game:
    """Structure for battleship game."""

    def __init__(self, player_1: Board, player_2: Board):
        """Initialize a game.

        Args:
            player_1: The board of the first player.
            player_2: The board of the second player.
        """
        self.boards = [player_1, player_2]  # 2 boards, index 0 and 1
        self.current_turn = 0  # 0 or 1

    def attack(self, player: int, pos: Crd) -> str:
        """Send attack to opposing player.

        player: Index of attacking player (0 or 1).
        pos: Coordinate to attack.
        """
        opponent = 1 - player
        result = self.boards[opponent].receive_attack(pos)
        if result in ('hit', 'miss'):
            self.current_turn = opponent  # swap turn on valid move
        return result

    def check_winner(self) -> int:
        """Check if there is a winner on the board.

        Return:
          - 0 if player 0 wins
          - 1 if player 1 wins
          - -1 if no winner yet
        """
        if self.boards[0].all_ships_sunk():
            return 1
        elif self.boards[1].all_ships_sunk():
            return 0
        return -1

    def __repr__(self) -> str:
        """Show both players' boards side by side with labels."""
        # get the string representation of each board and split into lines
        board0_lines = self.boards[0].__repr__().splitlines()
        board1_lines = self.boards[1].__repr__().splitlines()

        result = "Player 0's Board".ljust(25) + ' | ' + "Player 1's Board\n"
        result += '-' * 25 + '+' + '-' * 25 + '\n'

        # zip the rows of the two boards together to show side by side
        for left, right in zip(board0_lines, board1_lines):
            result += left.ljust(25) + ' | ' + right + '\n'

        result += f'\nCurrent turn: Player {self.current_turn}'
        return result
