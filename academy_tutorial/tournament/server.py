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
from academy.logging import init_logging
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
    exchange_address: str = 'https://exchange.academy-agents.org',
    auth_method: str | None = 'globus',
) -> web.Application:
    """Initialize the aiohttp web application."""
    app = web.Application()

    app['exchange_client'] = await HttpExchangeFactory(
        exchange_address,
        auth_method=auth_method,
    ).create_user_client()

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


def init_func(argv: str | None) -> web.Application:
    """Compatibility function to init app from cli."""
    parser = argparse.ArgumentParser()
    parser.add_argument('agent_id', type=uuid.UUID)
    parser.add_argument(
        '-e',
        'exchange',
        help='Address of the exchange to connect to.',
    )
    parser.add_argument('--no_auth', action='store_true')
    args = parser.parse_args(argv)

    agent: AgentId[Any] = AgentId(uid=args.agent_id)
    auth_method = 'globus' if not args.no_auth else None
    return asyncio.run(create_app(agent, args.exchange, auth_method))


async def main(agent_id: str | None) -> None:
    """Launches the tournament agent and backend server."""
    init_logging(logging.INFO)

    factory = HttpExchangeFactory(
        'https://exchange.academy-agents.org',
        auth_method='globus',
    )

    registration: HttpAgentRegistration[Any] | None = None
    if agent_id is not None:
        agent_id = AgentId(uid=uuid.UUID(agent_id))
        registration = HttpAgentRegistration(
            agent_id=agent_id,
        )
    async with await Manager.from_exchange_factory(
        factory=factory,
    ) as manager:
        tournament = await manager.launch(
            TournamentAgent,
            config=RuntimeConfig(
                terminate_on_success=False,
                terminate_on_error=False,
            ),
            registration=registration,
        )
        console = await factory.console()
        await console.share_mailbox(
            tournament.agent_id,
            uuid.UUID('47697db5-c19f-11f0-981f-0ee9d7d7fffb'),
        )
        print(f'Tournament Agent Id: {tournament.agent_id.uid}')

        app = await create_app(tournament.agent_id)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 9123)

        print('Starting app!')
        await site.start()

        while True:
            await asyncio.sleep(3600)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Start the battlehsip tournament agent',
    )
    parser.add_argument(
        '--agent_id',
        '-a',
        type=str,
        help='ID of Agent if mailbox has been registered before.',
    )
    args = parser.parse_args()

    raise SystemExit(asyncio.run(main(args.agent_id)))
