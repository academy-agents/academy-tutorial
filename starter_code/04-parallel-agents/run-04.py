from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any

from academy.agent import action
from academy.agent import Agent
from academy.exchange import LocalExchangeFactory
from academy.logging.recommended import recommended_logging
from academy.manager import Manager
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk import create_sdk_mcp_server
from claude_agent_sdk import ResultMessage
from claude_agent_sdk import tool

from academy_tutorial.wordle import WordleGame

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'claude-haiku-4-5'


class WordleAgent(Agent):
    """A LLM powered agent playing wordle.

    This agent uses a ReAct loop with a tool to make guesses to a wordle
    game. Each agent plays independently, without communicating with
    other agents.
    """

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model = model
        self.game: WordleGame | None = None
        self.client: ClaudeSDKClient | None = None

    def _make_guess_internal(self, guess: str) -> list[str] | str:
        """Internal guess mechanism.

        We need an internal guess method so that we can swap the game
        even after the Claude session has been created.
        """
        return self.game.make_guess(guess)

    async def agent_on_startup(self):
        @tool('wordle_feedback', WordleGame.make_guess.__doc__, {'guess': str})
        async def guess(args: dict[str, Any]) -> dict[str, Any]:
            text = str(self._make_guess_internal(args['guess']))
            return {'content': [{'type': 'text', 'text': text}]}

        options = ClaudeAgentOptions(
            model=self.model,
            system_prompt=(
                'You are playing Wordle, a word-guessing game. '
                'The target is a 5-letter English word. '
                'The `wordle_feedback` tool has an internal hidden word '
                'that you are trying to guess. '
                'Use the `wordle_feedback` tool to make guesses. '
                'After each guess you receive per-letter feedback: '
                'correct (right position), present (wrong position), '
                'absent (not in word). '
                'Use this feedback to narrow down the answer.'
            ),
            mcp_servers={
                'wordle': create_sdk_mcp_server('wordle', tools=[guess]),
            },
            # Only expose our tools, not built-in or user-configured ones
            tools=[],
            strict_mcp_config=True,
            allowed_tools=['mcp__wordle__wordle_feedback'],
            max_turns=12,
        )

        # Connect once so the agent reuses the same session across games
        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()

    async def agent_on_shutdown(self):
        if self.client is not None:
            await self.client.disconnect()

    @action
    async def play_wordle(self, game: WordleGame) -> str:
        """Play a game of wordle."""
        prompt = (
            'Play a new wordle by guessing words using `wordle_feedback`. '
            'Return the answer to the wordle puzzle.'
        )

        # TODO: Set the agent's game so it has the appropriate tool
        # Then let the agent solved the puzzle.


async def main(model: str = DEFAULT_MODEL):
    async with await Manager.from_exchange_factory(
        factory=LocalExchangeFactory(),
        log_config=recommended_logging(),
    ) as manager:
        logger.info('Launching agents.')
        # TODO: Launch the agents to solve wordle in parallel
        # (pass kwargs={'model': model})

        for _ in range(2):  # Play 2 games
            logger.info('Starting new game.')
            game = WordleGame()

            logger.info('Starting agent actions.')
            # TODO: Start the search on multiple agents in parallel
            # Stop the search when one of the agents finds an answer

            logger.info(f'True target word: {game.target}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--model',
        default=DEFAULT_MODEL,
        help=f'Model used for LLM inference (default: {DEFAULT_MODEL})',
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.model)))
