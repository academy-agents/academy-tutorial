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
            # Only expose our tools, not built-in or user-configured ones
            tools=[],
            strict_mcp_config=True,
            allowed_tools=[],
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

    @action
    async def query(self, prompt: str) -> str:
        await self.client.query(prompt)
        async for message in self.client.receive_response():
            if isinstance(message, ResultMessage):
                result = message.result or ''
        return result

async def main():
    async with await Manager.from_exchange_factory(
        factory=LocalExchangeFactory(),
        log_config=recommended_logging(),
    ) as manager:
        logger.info('Launching agents.')

        hdl = await manager.launch(HelloWorldAgent)

        # Message the agent
        await hdl.message('Remember, Kyle is buying drinks tonight!')

        # Since the agent stores the session in it's state
        # It recalls information from earlier
        result = await hdl.query('Who is getting the first round?')

        logger.info(f'Agent response: {result}')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
