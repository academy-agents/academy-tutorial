from __future__ import annotations

import argparse
import asyncio
import logging
import uuid
from typing import Any

from academy.exchange import HttpExchangeFactory
from academy.exchange.cloud.client import HttpAgentRegistration
from academy.handle import Handle
from academy.identifier import AgentId
from academy.manager import Manager
from academy.runtime import RuntimeConfig
from aiohttp import web

from academy_tutorial.tournament.agent import TournamentAgent


async def handle_rankings(request: web.Request) -> web.Response:
    """Handler for retrieving tournament rankings."""
    tournament = request.app['tournament_agent']
    return web.json_response(await tournament.get_players())


async def handle_matchups(request: web.Request) -> web.Response:
    """Handler for retrieving current tournament matchups."""
    tournament = request.app['tournament_agent']
    return web.json_response(await tournament.get_current_matchups())


async def handle_agent_id(request: web.Request) -> web.Response:
    """Return the agent id of the tournament agent."""
    tournament = request.app['tournament_agent']
    return web.json_response({'agent_id': str(tournament.agent_id.uid)})


async def create_app(
    tournament_agent: AgentId[TournamentAgent],
) -> web.Application:
    """Initialize the aiohttp web application."""
    app = web.Application()

    app['exchange_client'] = await HttpExchangeFactory().create_user_client()

    app['tournament_agent'] = Handle(
        tournament_agent,
        exchange=app['exchange_client'],
    )

    app.add_routes(
        [
            web.get('/rankings', handle_rankings),
            web.get('/matchups', handle_matchups),
            web.get('/agent_id', handle_agent_id),
        ],
    )

    app.add_routes(
        [
            web.static('/', path='static', show_index=True),
        ],
    )

    async def on_cleanup(app: web.Application) -> None:
        await app['exchange_client'].close()

    app.on_cleanup.append(on_cleanup)

    return app

async def main(agent_id: uuid.UUID) -> None:
    """Launches the backend server."""
    app = await create_app(AgentId(uid=agent_id))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 9123)
    await site.start()
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await site.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Start the battlehsip tournament server.',
    )
    parser.add_argument(
        '--agent-id',
        '-a',
        type=uuid.UUID,
        help='ID of Agent if mailbox has been registered before.',
    )
    args = parser.parse_args()

    raise SystemExit(asyncio.run(main(args.agent_id)))
