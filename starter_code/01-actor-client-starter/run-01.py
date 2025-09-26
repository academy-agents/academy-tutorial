from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from academy.agent import action
from academy.agent import Agent
from academy.exchange.local import LocalExchangeFactory
from academy.logging import init_logging
from academy.manager import Manager


class Counter(Agent):
    count: int

    async def agent_on_startup(self) -> None:
        self.count = 0

    # TODO: Implement actions


async def main() -> int:
    init_logging(logging.INFO)

    async with await Manager.from_exchange_factory(
        factory = # TODO: Use local exchange,
        executors = # TODO: Use thread pool launcher
    ) as manager:
        
        # TODO: Launch agent using manager.launch

        # TODO: Invoke actions with handles

    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))