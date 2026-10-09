from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from academy.agent import action
from academy.agent import Agent
from academy.exchange import LocalExchangeFactory
from academy.handle import Handle
from academy.logging.recommended import recommended_logging
from academy.manager import Manager
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk import create_sdk_mcp_server
from claude_agent_sdk import query
from claude_agent_sdk import ResultMessage
from claude_agent_sdk import tool

from academy_tutorial.wordle import score_guess
from academy_tutorial.wordle import WordleGame

logger = logging.getLogger(__name__)

MODEL = 'claude-haiku-4-5'

RULES = (
    'Wordle is a word-guessing game where the target is a hidden 5-letter '
    'English word. After each guess the player receives per-letter '
    'feedback: correct (right position), present (wrong position), '
    'absent (not in word). '
)


def text(content: Any) -> dict[str, Any]:
    """Format a tool result."""
    return {'content': [{'type': 'text', 'text': str(content)}]}


def options(
    server: str,
    tools: list[Any],
    **kwargs: Any,
) -> ClaudeAgentOptions:
    """Build options exposing only the given in-process tools."""
    return ClaudeAgentOptions(
        model=MODEL,
        mcp_servers={server: create_sdk_mcp_server(server, tools=tools)},
        # Only expose our tools, not built-in or user-configured ones
        tools=[],
        strict_mcp_config=True,
        allowed_tools=[f'mcp__{server}__{t.name}' for t in tools],
        **kwargs,
    )


async def run(prompt: str, options: ClaudeAgentOptions) -> str:
    """Run a Claude Agent SDK query and return the final result."""
    result = ''
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message.result or ''
    return result


class StrategyAgent(Agent):
    """A LLM powered sub-agent evaluating a wordle strategy.

    The sub-agent designs its own test of the strategy using a cheap
    simulator, and never touches the costly true game.
    """

    async def agent_on_startup(self):
        """Initialize the academy agent state."""

        @tool(
            'simulate_feedback',
            'Score guesses against target words you choose, one guess per '
            'target. Returns the per-letter feedback the real game would '
            'give for each pair.',
            {'guesses': list[str], 'targets': list[str]},
        )
        async def simulate(args: dict[str, Any]) -> dict[str, Any]:
            pairs = list(zip(args['guesses'], args['targets']))
            logger.info(f'{self.agent_id} simulating {len(pairs)} guesses')
            return text([score_guess(g, t) for g, t in pairs])

        self.options = options(
            'simulator',
            [simulate],
            system_prompt=(
                RULES + 'You evaluate Wordle strategies offline. Design your '
                'own test: choose 3 to 5 varied target words and play the '
                'strategy against all of them at once, passing the next '
                'guess for every unsolved game in a single '
                '`simulate_feedback` call. When choosing guesses, only use '
                "the feedback, not the target's identity, so the test is "
                'fair.'
            ),
            max_turns=10,
        )

    @action
    async def evaluate_strategy(self, strategy: str) -> str:
        """Evaluate a wordle strategy and report how well it performs."""
        logger.info(f'{self.agent_id} evaluating: {strategy}')
        return await run(
            f'Evaluate this strategy:\n{strategy}\n\n'
            'Report the test words you used, the guesses taken for each, '
            'the average number of guesses, and any weaknesses you found.',
            self.options,
        )


class CoordinatorAgent(Agent):
    """A LLM powered agent searching for the best strategy to play wordle.

    The coordinator proposes strategies and delegates each one to a
    sub-agent for evaluation. Once it picks the best strategy, it plays the
    true game, where each guess is a costly evaluation.

    Args:
        workers: Handles to the sub-agents evaluating strategies.
    """

    def __init__(self, workers: list[Handle[StrategyAgent]]) -> None:
        self.workers = workers

    async def evaluate_strategies(self, strategies: list[str]) -> list[str]:
        """Evaluate wordle strategies in parallel, one per sub-agent.

        Each sub-agent tests its strategy offline and reports how many
        guesses it takes on average and its weaknesses.

        Args:
            strategies: Descriptions of the strategies to evaluate.
        """
        return await asyncio.gather(
            *(
                worker.evaluate_strategy(strategy)
                for worker, strategy in zip(self.workers, strategies)
            ),
        )

    async def agent_on_startup(self):
        """Initialize the academy agent state."""

        @tool(
            'evaluate_strategies',
            self.evaluate_strategies.__doc__,
            {'strategies': list[str]},
        )
        async def evaluate(args: dict[str, Any]) -> dict[str, Any]:
            reports = await self.evaluate_strategies(args['strategies'])
            return text(json.dumps(dict(zip(args['strategies'], reports))))

        self.search_options = options(
            'coordinator',
            [evaluate],
            system_prompt=(
                RULES + 'Your goal is to find the best general strategy for '
                'playing Wordle, one that solves puzzles in the fewest '
                f'guesses. You have {len(self.workers)} sub-agents. Use '
                '`evaluate_strategies` to have each sub-agent test one of '
                'your proposed strategies. You may refine and evaluate '
                'once more based on their reports, at most 2 rounds total.'
            ),
            max_turns=4,
        )

    @action
    async def play_wordle(self, game: WordleGame) -> dict[str, Any]:
        """Find the best strategy, then use it to play the true game."""
        strategy = await run(
            f'Propose {len(self.workers)} distinct wordle strategies and '
            'evaluate them, then reply with '
            'only the best strategy, written as instructions for a player.',
            self.search_options,
        )
        logger.info(f'Best strategy:\n{strategy}')

        # Each guess in the true game is costly, so only play it once
        guesses: list[str] = []

        @tool('wordle_feedback', game.make_guess.__doc__, {'guess': str})
        async def guess(args: dict[str, Any]) -> dict[str, Any]:
            guesses.append(args['guess'].lower())
            return text(game.make_guess(args['guess']))

        answer = await run(
            'Play wordle by guessing words using `wordle_feedback`. '
            'Return the answer to the wordle puzzle.',
            options(
                'wordle',
                [guess],
                system_prompt=(
                    RULES + 'The `wordle_feedback` tool has the hidden word. '
                    'Each guess is costly, so solve it in as few guesses as '
                    f'possible. Play following this strategy:\n{strategy}'
                ),
                max_turns=12,
            ),
        )
        return {'strategy': strategy, 'guesses': guesses, 'answer': answer}


async def main():
    game = WordleGame()

    async with await Manager.from_exchange_factory(
        factory=LocalExchangeFactory(),
        log_config=recommended_logging(),
    ) as manager:
        logger.info('Launching sub-agents.')
        workers = [await manager.launch(StrategyAgent) for _ in range(3)]

        logger.info('Launching coordinator.')
        coordinator = await manager.launch(CoordinatorAgent, args=(workers,))

        result = await coordinator.play_wordle(game)
        logger.info(f'True game guesses: {result["guesses"]}')
        logger.info(f'Coordinator returned {result["answer"]}')
        logger.info(f'True target word: {game.target}')


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
