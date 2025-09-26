from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from academy.agent import action
from academy.agent import Agent
from academy.agent import loop
from academy.exchange import LocalExchangeFactory
from academy.logging import init_logging
from academy.manager import Manager

logger = logging.getLogger(__name__)


class Coordinator(Agent):
    def __init__(
        self,
        # TODO: Initialize the agent with handles to the other agents
    ) -> None:
        super().__init__()
        # TODO: Store the handles as part of the agent state

    @action
    async def process(self, text: str) -> str:
        # TODO: Invoke the agents given the text 
        return text


class Lowerer(Agent):
    @action
    async def lower(self, text: str) -> str:
        return text.lower()


class Reverser(Agent):
    @action
    async def reverse(self, text: str) -> str:
        return text[::-1]


async def main() -> int:
    init_logging(logging.INFO)

    async with await Manager.from_exchange_factory(
        factory=LocalExchangeFactory(),
        executors=ThreadPoolExecutor(),
    ) as manager:
        lowerer = await manager.launch(Lowerer)
        reverser = await manager.launch(Reverser)
        coordinator = ... # TODO: Launch the coordinator agent
        
        text = 'DEADBEEF'
        expected = 'feebdaed'

        logger.info('Invoking process("%s") on %s', text, coordinator.agent_id)
        result = await coordinator.process(text)
        assert result == expected
        logger.info('Received result: "%s"', result)

    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
