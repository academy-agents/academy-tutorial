from __future__ import annotations

import argparse
import asyncio
import logging
import uuid

from academy.agent import action
from academy.exchange import HttpExchangeFactory
from academy.handle import Handle
from academy.identifier import AgentId
from academy.logging.recommended import recommended_logging
from academy.manager import Manager
from academy_dashboard import MonitoredAgent
from academy_dashboard import UserAgent
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk import ResultMessage

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'muse-spark-bf16'


class HelloWorldAgent(MonitoredAgent):
    """A simple chat agent wrapping a persistent Claude session."""

    def __init__(
        self,
        user_agent_handle: Handle[UserAgent],
        model: str = DEFAULT_MODEL,
    ) -> None:
        super().__init__(user_agent_handle=user_agent_handle)
        self.model = model
        self.client: ClaudeSDKClient | None = None

    async def agent_on_startup(self):
        # Register with the dashboard and start forwarding logs
        await super().agent_on_startup()

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
        await super().agent_on_shutdown()

    @action
    async def message(self, message: str) -> None:
        """Message the agent without receiving a response."""
        await self.client.query(message)
        # Wait for the turn to finish, but discard the reply
        async for _ in self.client.receive_response():
            pass

    @action
    async def query(self, prompt: str) -> str:
        """Query the agent and return its response."""
        result = ''
        await self.client.query(prompt)
        async for message in self.client.receive_response():
            if isinstance(message, ResultMessage):
                result = message.result or ''
        return result


async def main(user_agent_id: str, model: str = DEFAULT_MODEL):
    async with await Manager.from_exchange_factory(
        factory=HttpExchangeFactory(),
        log_config=recommended_logging(),
    ) as manager:
        # Get a handle to the user agent
        agent_id = AgentId(uid=uuid.UUID(user_agent_id), name='UserAgent')
        user_agent_handle = manager.get_handle(agent_id)

        hdl = await manager.launch(
            HelloWorldAgent,
            kwargs={
                'model': model,
                'user_agent_handle': user_agent_handle,
            },
        )

        # Message the agent
        await hdl.message('Remember, Kyle is buying drinks tonight!')

        # Since the agent stores the session in its state
        # It recalls information from earlier
        result = await hdl.query('Who is getting the first round?')

        logger.info(f'Agent response: {result}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--user-agent-id',
        required=True,
        help='UUID of the dashboard UserAgent to report to',
    )
    parser.add_argument(
        '--model',
        default=DEFAULT_MODEL,
        help=f'Model used for LLM inference (default: {DEFAULT_MODEL})',
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.user_agent_id, args.model)))
