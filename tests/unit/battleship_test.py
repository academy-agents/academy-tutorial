from __future__ import annotations

import pytest

from academy_tutorial.battleship import Board
from academy_tutorial.battleship import Crd
from academy_tutorial.battleship import Game
from academy_tutorial.battleship import Ship


def test_ship_sinks():
    crds = [Crd(i, 0) for i in range(3)]
    ship = Ship(crds)

    assert not ship.is_sunk

    ship.register_hit(Crd(1, 0))
    assert len(ship.hits) == 1

    ship.register_hit(Crd(0, 0))
    ship.register_hit(Crd(2, 0))
    assert ship.is_sunk


def test_ship_repr():
    crds = [Crd(i, 0) for i in range(3)]
    ship = Ship(crds)

    assert str(len(crds)) in str(ship)


def test_board_place_and_sink():
    board = Board()

    ship = board.place_ship(Crd(0, 0), 2, 'horizontal')
    assert ship is not None
    assert ship.length == 2  # noqa: PLR2004
    assert not board.all_ships_sunk()

    result = board.receive_attack(Crd(0, 0))
    assert result == 'hit'
    result = board.receive_attack(Crd(0, 0))
    assert result == 'guessed'
    result = board.receive_attack(Crd(1, 1))
    assert result == 'miss'
    result = board.receive_attack(Crd(0, 1))
    assert result == 'hit'
    assert board.all_ships_sunk()


def test_board_ship_overlap():
    board = Board()
    board.place_ship(Crd(0, 0), 2, 'vertical')

    ship = board.place_ship(Crd(1, 0), 2, 'horizontal')
    assert ship is None


def test_board_ship_diagonal():
    board = Board()
    with pytest.raises(ValueError, match='Invalid direction'):
        board.place_ship(Crd(0, 0), 2, 'diagonal')  # type: ignore[arg-type]


def test_board_out_of_bounds():
    board = Board()
    ship = board.place_ship(Crd(0, 9), 2, 'horizontal')
    assert ship is None

    ship = board.place_ship(Crd(9, 0), 2, 'vertical')
    assert ship is None


def test_game():
    board = Board()
    board.place_ship(Crd(0, 0), 2, 'vertical')

    board_2 = Board()
    board_2.place_ship(Crd(0, 0), 2, 'vertical')

    game = Game(board, board_2)
    assert game.current_turn == 0

    result = game.attack(0, Crd(0, 0))
    assert result == 'hit'
    assert game.current_turn == 1
    assert game.check_winner() == -1

    result = game.attack(1, Crd(0, 0))
    assert result == 'hit'
    assert game.current_turn == 0
    assert game.check_winner() == -1

    result = game.attack(0, Crd(0, 0))
    assert result == 'guessed'
    assert game.current_turn == 0
    assert game.attack(0, Crd(1, 0))
    assert game.check_winner() == 0
