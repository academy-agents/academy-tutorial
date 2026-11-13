from __future__ import annotations

import argparse
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

DEFAULT_MODEL = 'muse-spark-bf16'


class HelloWorldAgent(Agent):
    """A simple chat agent wrapping a persistent Claude session."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model = model
        self.client: ClaudeSDKClient | None = None

    async def agent_on_startup(self):
        options = ClaudeAgentOptions(
            model=self.model,
            system_prompt='You are a helpful assistant.',
            # Don't expose built-in or user-configured tools
            tools=[],
            strict_mcp_config=True,
            max_turns=12,
        )

        # Connect once so the agent reuses the same session across queries
        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()

    async def agent_on_shutdown(self):
        if self.client is not None:
            await self.client.disconnect()

    @action
    async def message(self, message: str) -> None:
        """Message the agent without receiving a response."""
        await self.client.query(message)
        # Wait for the turn to finish, but discard the reply
        async for _ in self.client.receive_response():
            pass

    # TODO: Write a `query` action that sends a prompt to the LLM and returns
    # the response. Iterate over `self.client.receive_response()` to get the
    # messages, and return `message.result` from the `ResultMessage`.

async def main(model: str = DEFAULT_MODEL):
    async with await Manager.from_exchange_factory(
        factory=..., # TODO: Use the LocalExchangeFactory
        log_config=recommended_logging(),
    ) as manager:
        logger.info('Launching agents.')

        # TODO: Launch the Agent (pass kwargs={'model': model})
        hdl = ...

        # Message the agent
        await hdl.message('Remember, Kyle is buying drinks tonight!')

        # TODO: Query the agent
        result = ...

        logger.info(f'Agent response: {result}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--model',
        default=DEFAULT_MODEL,
        help=f'Model used for LLM inference (default: {DEFAULT_MODEL})',
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.model)))
