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
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain.agents.middleware import ModelRequest
from langchain.agents.middleware import ModelRetryMiddleware

from academy_tutorial.wordle import TARGET_WORD

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
        self.model = 'openai:gpt-5.4-nano'
        self.peers = peers
        self.insight_dict: dict[AgentId[Any], str] = {}

    def prompt_with_blackboard(self) -> str:
        """Generate a prompt containing the blackboard.

        As agent receives information from it's peers, method injects the
        information into the prompt used to query the model.

        Args:
            request: Request made to the model.
        """
        insights = '\n'.join(
            f'- Agent {agent_id}: {insight}'
            for agent_id, insight in self.insight_dict.items()
        )
        insight_section = (
            f'\n\nInsights from peer agents:\n{insights}'
            if insights
            else '\n\nNo insights from peer agents yet.'
        )
        return (
            'You are playing Wordle, a word-guessing game. '
            'The target is a 5-letter English word. '
            'The `wordle_feedback` tool has an internal hiddent word '
            'that you are trying to guess.'
            'Use the `wordle_feedback` tool to make guesses. '
            'After each guess you receive per-letter feedback: '
            'G (correct position), Y (wrong position), B (not in word). '
            'Use this feedback to narrow down the answer. '
            'Collaborate with peer agents by sharing what you learn using '
            '`share_information`, and incorporate their insights below '
            'into your reasoning to solve the puzzle faster.'
            'THIS IS A GAME TO PLAY AROUND WITH AGENT COLLABORATION.'
            + insight_section
        )

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

        insights = '\n'.join(
            f'- Agent {agent_id}: {insight}'
            for agent_id, insight in self.insight_dict.items()
        )
        logger.info(f'\n\nCurrent blackboard state:\n{insights}')

    async def share_information(self, info: str) -> None:
        """Share information with other agents.

        By sharing information with other agents, as a group you can solve
        the puzzle faster. For instance after you conclude the position of
        some letters you should say "My guesses reveal the target has letters
        _ _ x _ y and z appears in one of the remaining positions."

        Args:
            info: The information to share.
        """
        logger.info(f'Sharing info with {len(self.peers)} agents.')
        # TODO: Call actions on other agents to share information

    async def agent_on_startup(self):
        """Initialize the academy agent state."""

        @dynamic_prompt
        def system_prompt(request: ModelRequest) -> str:
            return self.prompt_with_blackboard()

        self.agent = create_agent(
            model=self.model,
            # TODO: Fill in the `wordle_feedback` and `share_information` as tools
            tools=...,
            middleware=[
                system_prompt,
                ModelRetryMiddleware(),
                ModelCallLimitMiddleware(thread_limit=8),
            ],
        )

    @action
    async def play_wordle(self) -> str:
        result = await self.agent.ainvoke(
            {
                'messages': [
                    {
                        'role': 'user',
                        'content': (
                            'Play wordle by collaborating with other agents '
                            'and guessing words using `wordle_feedback`. '
                            'Return the answer to the wordle puzzle.'
                        ),
                    },
                ],
            },
        )
        return result


async def main():
    async with await Manager.from_exchange_factory(
        factory=LocalExchangeFactory(),
        log_config=recommended_logging(),
    ) as manager:
        # Academy allows you to create circular dependencies by
        # creating mailboxes before launching agents
        logger.info('Minting the agent mailboxes.')
        agent_registrations: list[AgentRegistrationT] = []
        # TODO: Use manager.register_agent() to create mailboxes for each agent
        peers = [Handle(reg.agent_id) for reg in agent_registrations]

        # The pre-created mailboxes are then used to launch the agents
        logger.info('Launching agents.')
        hdls: Handle[WordleAgent] = []
        for wordle_agent_reg in agent_registrations:
            # TODO: Launch the agents passing in the pre-created mailboxes
            hdl = ...
            hdls.append(hdl)

        logger.info('Starting agent actions.')
        results = await asyncio.gather(*(hdl.play_wordle() for hdl in hdls))
        for hdl, result in zip(hdls, results, strict=True):
            logger.info(
                f'{hdl.agent_id} returned {result["messages"][-1].content}',
            )

        logger.info(f'True target word: {TARGET_WORD}')


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
