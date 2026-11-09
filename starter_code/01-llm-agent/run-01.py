from __future__ import annotations

import asyncio
import logging

from academy.agent import action
from academy.agent import Agent
from academy.exchange import LocalExchangeFactory
from academy.logging.recommended import recommended_logging
from academy.manager import Manager
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk import ResultMessage

logger = logging.getLogger(__name__)


class HelloWorldAgent(Agent):
    """A LLM powered agent playing wordle.

    This agent uses a ReAct loop with a tool to make guesses to a wordle
    game. Each agent plays independently, without communicating with
    other agents.
    """

    def __init__(self) -> None:
        self.model = 'claude-haiku-4-5'
        self.client: ClaudeSDKClient | None = None

    async def agent_on_startup(self):
        options = ClaudeAgentOptions(
            model=self.model,
            system_prompt='You are a helpful assistant.',
            tools=[],
            max_turns=12,
        )

        # Connect once so the agent reuses the same session across games
        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()

    async def agent_on_shutdown(self):
        if self.client is not None:
            await self.client.disconnect()

    @action
    async def message(self, message: str) -> None:
        """Message the agent without recieving a response."""

        await self.client.query(message)
        await self.client.receive_messages()

    # TODO: Write an action to query the LLM and return the respons
    # Use `self.client.receive_response()` for get the result messages
    # Check if the message is a `ResultMessage` and return message.result

async def main():
    async with await Manager.from_exchange_factory(
        factory=..., # TODO: Use the LocalExchangeFactory
        log_config=recommended_logging(),
    ) as manager:
        logger.info('Launching agents.')

        # TODO: Launch the Agent
        hdl = ...

        # Message the agent
        await hdl.message('Remember, Kyle is buying drinks tonight!')

        # TODO: Query the agent
        result = ...

        logger.info(f'Agent response: {result}')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
