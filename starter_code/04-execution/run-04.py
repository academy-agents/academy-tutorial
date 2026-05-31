from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os

from academy.agent import action
from academy.agent import Agent
from academy.handle import Handle
from academy.logging.recommended import recommended_logging
from academy.manager import Manager
from dotenv import load_dotenv
from dotenv import find_dotenv

load_dotenv(find_dotenv('tpc.env', raise_error_if_not_found=True))

EXCHANGE_ADDRESS = 'https://exchange.academy-agents.org'
logger = logging.getLogger(__name__)


class Coordinator(Agent):
    def __init__(
        self,
        lowerer: Handle[Lowerer],
    ) -> None:
        super().__init__()
        self.lowerer = lowerer

    @action
    async def process(self, text: str) -> str:
        text = await self.lowerer.lower(text)
        return text


class Lowerer(Agent):
    @action
    async def lower(self, text: str) -> str:
        return text.lower()


async def main() -> int:
    if 'ACADEMY_TUTORIAL_ENDPOINT' in os.environ:
        # NOTE: The tutorial endpoint is limited to 2 agents per user
        endpoint = os.environ['ACADEMY_TUTORIAL_ENDPOINT']
        executor  # TODO: create a GCExecutor with this endpoint as its argument
    else:
        mp_context = multiprocessing.get_context('spawn')
        executor_kwargs = dict(max_workers=3, mp_context=mp_context)
        executor = (
            ...
        )  # TODO: create a ProcessPoolExecutor with the above kwargs

    async with (
        await Manager.from_exchange_factory(
            factory=...,  # TODO: create an HTTPSExchangeFactory associated with EXCHANGE_ADDRESS and with auth_method='globus'
            executors=...,  # TODO: pass the executor created above
            log_config=recommended_logging(),
        ) as manager
    ):
        # Launch each of the three agents types. The returned type is
        # a handle to that agent used to invoke actions.
        lowerer = await manager.launch(Lowerer)
        coordinator = await manager.launch(
            Coordinator,
            args=(lowerer,),
        )

        text = 'DEADBEEF'
        expected = 'deadbeef'

        logger.info(
            'Invoking process("%s") on %s',
            text,
            coordinator.agent_id,
        )
        result = await coordinator.process(text)
        assert result == expected
        logger.info('Received result: "%s"', result)

    # Upon exit, the Manager context will instruct each agent to shutdown,
    # closing their respective handles, and shutting down the executors.

    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
