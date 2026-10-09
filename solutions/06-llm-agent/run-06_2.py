from __future__ import annotations

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
from claude_agent_sdk import create_sdk_mcp_server
from claude_agent_sdk import query
from claude_agent_sdk import ResultMessage
from claude_agent_sdk import tool

from academy_tutorial.wordle import WordleGame

logger = logging.getLogger(__name__)


class WordleAgent(Agent):
    """A LLM powered agent playing wordle.

    This agent uses a ReAct loop with a tool to make guesses to a wordle
    game, and a tool to collaborate with other agents. This pattern coudld
    be used to build "agent forests". Academy allows there agents to run in
    a distributed environment, for instance to replace the Wordle game with
    a more computationally expensive simulation application.

    Args:
        peers: A list of other agent handles.
    """

    def __init__(
        self,
        peers: list[Handle[WordleAgent]],
    ) -> None:
        self.model = 'claude-haiku-4-5'
        self.peers = peers
        self.insight_dict: dict[AgentId[Any], str] = {}

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
        self.insight_dict[context.source_id] = info
        logger.info(
            f'\n\nCurrent blackboard state:\n{await self.read_blackboard()}',
        )

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

    @action
    async def play_wordle(self, game: WordleGame) -> str:
        """Play a game of wordle, collaborating through the blackboard."""

        @tool('read_blackboard', self.read_blackboard.__doc__, {})
        async def read_blackboard(args: dict[str, Any]) -> dict[str, Any]:
            text = await self.read_blackboard()
            return {'content': [{'type': 'text', 'text': text}]}

        @tool('write_blackboard', self.write_blackboard.__doc__, {'info': str})
        async def write_blackboard(args: dict[str, Any]) -> dict[str, Any]:
            await self.write_blackboard(args['info'])
            text = await self.read_blackboard()
            return {'content': [{'type': 'text', 'text': text}]}

        @tool('wordle_feedback', game.make_guess.__doc__, {'guess': str})
        async def guess(args: dict[str, Any]) -> dict[str, Any]:
            text = str(game.make_guess(args['guess']))
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

        result = ''
        async for message in query(
            prompt=(
                'Play wordle by collaborating with other agents '
                'and guessing words using `wordle_feedback`. '
                'Return the answer to the wordle puzzle.'
            ),
            options=options,
        ):
            if isinstance(message, ResultMessage):
                result = message.result or ''
        return result


async def main():
    game = WordleGame()

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
        hdls: Handle[WordleAgent] = []
        for wordle_agent_reg in agent_registrations:
            hdls.append(
                await manager.launch(
                    WordleAgent,
                    # The peer handles are used to create the
                    # communication graph
                    args=(peers,),
                    registration=wordle_agent_reg,
                ),
            )

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
    raise SystemExit(asyncio.run(main()))
