"""Example: launch a UserAgent and a MonitoredAgent and exchange messages.

Architecture:

    +---------------+        messages        +------------+
    | MonitoredAgent| ---------------------->| UserAgent  |
    |  (worker)     |   receive_message()    |            |
    +---------------+                        +------------+
          |                                        |
          | logging.info / agent.log()             | get_messages()
          v                                        v
     forwarded automatically              inspect from client

This example requires a running UserAgent. Launch one with:
>:    user-agent-launcher
then export it's UUID with
>:    export USER_AGENT_ID=YOUR_USER_AGENT_UUID_STRING

"""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ProcessPoolExecutor
from uuid import UUID

from academy.agent import Agent
from academy.agent import loop
from academy.exchange.cloud import HttpExchangeFactory
from academy.handle import Handle
from academy.identifier import AgentId
from academy.manager import Manager

from academy_dashboard import MonitoredAgent
from academy_dashboard import UserAgent
from academy_dashboard.user_agent.message import UserPrompt


logger = logging.getLogger(__name__)

class Sleeper(Agent): # TODO: Inherit from MonitoredAgent instead of Agent
    """An Agent that sleeps."""

    def __init__(self, user_agent_handle: Handle[UserAgent]) -> None:
        super().__init__(user_agent_handle=user_agent_handle)

    @loop
    async def cycle(self, shutdown: asyncio.Event) -> None:
        """Log and sleep in loop."""
        counter = 0
        while not shutdown.is_set():
            await asyncio.sleep(2)
            logger.info('Sleeper iteration %d', counter)
            counter += 1

        #TODO: Add more log lines to send to the dashboard.

        await self.user_agent.prompt_user(
            "Academy Tutorial", 
            ..., # TODO: Create a UserPrompt to send to the dashboard
        )


async def main(user_agent_id: UUID) -> None:
    """Launch MonitoredAgents."""
    async with await Manager.from_exchange_factory(
        factory=HttpExchangeFactory(), # Must use the HttpExchangeFactory
        executors=ProcessPoolExecutor(max_workers=1),
    ) as manager:
        # 1. Launch UserAgent first so its handle can be passed to the worker.
        agent_id = AgentId(uid=user_agent_id, name='UserAgent')
        user_agent_handle = manager.get_handle(agent_id)

        # 2. Launch a single agents:
        sleeper = await manager.launch(
            Sleeper,
            kwargs={'user_agent_handle': user_agent_handle},
        )

        # 3. Wait for the sleeper agent, which will go on until cancelled
        #    with a ctrl+c
        await manager.wait([sleeper])
        logger.info('All done!')


if __name__ == '__main__':
    user_agent_id = os.environ['USER_AGENT_ID']
    raise SystemExit(asyncio.run(main(UUID(user_agent_id))))