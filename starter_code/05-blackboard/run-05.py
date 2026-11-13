from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any

from academy.agent import action
from academy.agent import Agent
from academy.context import ActionContext
from academy.exchange import LocalExchangeFactory
from academy.exchange.transport import AgentRegistrationT
from academy.handle import Handle
from academy.identifier import AgentId
from academy.logging.recommended import recommended_logging
from academy.manager import Manager
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk import create_sdk_mcp_server
from claude_agent_sdk import ResultMessage
from claude_agent_sdk import tool

from academy_tutorial.wordle import WordleGame

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'muse-spark-bf16'


class WordleAgent(Agent):
    """A LLM powered agent playing wordle.

    This agent uses a ReAct loop with a tool to make guesses to a wordle
    game, and a tool to collaborate with other agents. This pattern could
    be used to build "agent forests". Academy allows these agents to run in
    a distributed environment, for instance to replace the Wordle game with
    a more computationally expensive simulation application.

    Args:
        peers: A list of other agent handles.
        model: Model used for LLM inference.
    """

    def __init__(
        self,
        peers: list[Handle[WordleAgent]],
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.model = model
        self.peers = peers
        self.insight_dict: dict[AgentId[Any], str] = {}
        self.game: WordleGame | None = None
        self.client: ClaudeSDKClient | None = None

    def _make_guess_internal(self, guess: str) -> list[str] | str:
        """Internal guess mechanism.

        We need an internal guess method so that we can swap the game
        even after the Claude session has been created.
        """
        return self.game.make_guess(guess)

    async def read_blackboard(self) -> str:
        """Read the blackboard of insights shared by peer agents.

        Check the blackboard before guessing to use what your peers have
        learned about the target word.
        """
        insights = '\n'.join(
            f'- Agent {agent_id}: {insight}'
            for agent_id, insight in self.insight_dict.items()
        )
        return insights or 'The blackboard is empty.'

    @action(context=True)
    async def receive_information(
        self,
        info: str,
        *,
        context: ActionContext,
    ) -> None:
        """Receive information from other agents playing the same game.

        Args:
            info: Information received from other agent.

        """
        # TODO: Write an action that receives information from another agent
        # and writes it into a dictionary

    async def write_blackboard(self, info: str) -> None:
        """Write information to the blackboard shared with other agents.

        By sharing information with other agents, as a group you can solve
        the puzzle faster. For instance after you conclude the position of
        some letters you should say "My guesses reveal the target has letters
        _ _ x _ y and z appears in one of the remaining positions."

        Args:
            info: The information to share.
        """
        logger.info(f'Writing to blackboard of {len(self.peers)} agents.')
        await asyncio.gather(
            *(peer.receive_information(info) for peer in self.peers),
        )

    async def agent_on_startup(self):
        """Initialize the academy agent state."""
        self.peers = [p for p in self.peers if p.agent_id != self.agent_id]

        @tool('read_blackboard', self.read_blackboard.__doc__, {})
        async def read_blackboard(args: dict[str, Any]) -> dict[str, Any]:
            text = await self.read_blackboard()
            return {'content': [{'type': 'text', 'text': text}]}

        @tool('write_blackboard', self.write_blackboard.__doc__, {'info': str})
        async def write_blackboard(args: dict[str, Any]) -> dict[str, Any]:
            await self.write_blackboard(args['info'])
            text = await self.read_blackboard()
            return {'content': [{'type': 'text', 'text': text}]}

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
                'Use this feedback to narrow down the answer. '
                'You share a blackboard with peer agents playing the same '
                'game. Use `read_blackboard` to see what your peers have '
                'learned, and `write_blackboard` to share what you learn. '
                'Incorporate their insights into your reasoning to solve the '
                'puzzle faster. '
                'THIS IS A GAME TO PLAY AROUND WITH AGENT COLLABORATION.'
            ),
            mcp_servers={
                'wordle': create_sdk_mcp_server(
                    'wordle',
                    tools=[read_blackboard, write_blackboard, guess],
                ),
            },
            # Only expose our tools, not built-in or user-configured ones
            tools=[],
            strict_mcp_config=True,
            allowed_tools=[
                'mcp__wordle__read_blackboard',
                'mcp__wordle__write_blackboard',
                'mcp__wordle__wordle_feedback',
            ],
            max_turns=16,
        )

        # Connect once so the agent reuses the same session across games
        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()

    async def agent_on_shutdown(self):
        if self.client is not None:
            await self.client.disconnect()

    @action
    async def play_wordle(self, game: WordleGame) -> str:
        """Play a game of wordle, collaborating through the blackboard."""
        self.game = game
        # Insights from the previous game no longer apply
        self.insight_dict.clear()

        prompt = (
            'Play a new wordle by collaborating with other agents '
            'and guessing words using `wordle_feedback`. '
            'Return the answer to the wordle puzzle.'
        )

        result = ''
        await self.client.query(prompt)
        async for message in self.client.receive_response():
            if isinstance(message, ResultMessage):
                result = message.result or ''
        return result


async def main(model: str = DEFAULT_MODEL):
    async with await Manager.from_exchange_factory(
        factory=LocalExchangeFactory(),
        log_config=recommended_logging(),
    ) as manager:
        # Academy allows you to create circular dependencies by
        # creating mailboxes before launching agents
        logger.info('Minting the agent mailboxes.')
        agent_registrations: list[AgentRegistrationT] = []
        for _ in range(2):
            agent_registrations.append(
                await manager.register_agent(WordleAgent),
            )
        peers = [Handle(reg.agent_id) for reg in agent_registrations]

        # The pre-created mailboxes are then used to launch the agents
        logger.info('Launching agents.')
        hdls: list[Handle[WordleAgent]] = []
        for wordle_agent_reg in agent_registrations:
            hdls.append(
                await manager.launch(
                    WordleAgent,
                    # The peer handles are used to create the
                    # communication graph
                    args=(peers,),
                    kwargs={'model': model},
                    registration=wordle_agent_reg,
                ),
            )

        for _ in range(2):  # Play 2 games
            logger.info('Starting new game.')
            game = WordleGame()

            logger.info('Starting agent actions.')
            results = await asyncio.gather(
                *(hdl.play_wordle(game) for hdl in hdls),
            )
            for hdl, result in zip(hdls, results, strict=True):
                logger.info(
                    f'{hdl.agent_id} returned {result}',
                )

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
