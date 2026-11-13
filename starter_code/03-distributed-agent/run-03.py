from __future__ import annotations

import argparse
import ast
import asyncio
import contextlib
import inspect
import io
import logging
import multiprocessing
import os
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import ase
import ase.build  # noqa: F401  (put build into the namespace for the LLM)
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk import ResultMessage
from claude_agent_sdk import create_sdk_mcp_server
from claude_agent_sdk import tool

from academy.agent import action
from academy.agent import Agent
from academy.exchange import HttpExchangeFactory
from academy.handle import Handle
from academy.logging.recommended import recommended_logging
from academy.manager import Manager
from globus_compute_sdk import Executor as GCExecutor


logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'muse-spark-bf16'


class MLIPAgent(Agent):
    """Wraps a machine-learned interatomic potential.

    This agent knows nothing about LLMs: it takes `ase.Atoms` and returns
    plain Python numbers, so any agent (or script) can use it.
    """

    MOCK_ENERGIES = [-7662.041, -7660.843]

    def __init__(self) -> None:
        self.n_predicted = 0

    @action
    async def predict_energy(self, structures: list[ase.Atoms]) -> list[float]:
        """Predict the potential energy of each structure.

        The model only supports structures containing H, C, and O atoms.

        Args:
            structures: Structures to evaluate, as `ase.Atoms` objects.

        Returns:
            The energy of each structure in eV, in the same order.
        """
        logger.info(f'Called mock predict energy on {len(structures)} structure(s).')
        energies = []
        for _ in structures:
            energies.append(
                self.MOCK_ENERGIES[self.n_predicted % len(self.MOCK_ENERGIES)],
            )
            self.n_predicted += 1
        return energies


async def run_python(code: str, namespace: dict[str, Any]) -> str:
    """Execute code in `namespace` and return everything it printed.

    The code may use top-level `await`, so the LLM can call handles directly.
    Exceptions are returned as a traceback so the LLM can fix its code.
    """
    output = io.StringIO()

    logger.info(
        f'Running code\n\n{code}'
    )
    try:
        compiled = compile(
            code, '<llm>', 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
        )
        with contextlib.redirect_stdout(output):
            result = eval(compiled, namespace)
            if inspect.iscoroutine(result):
                await result
    except Exception:
        output.write(traceback.format_exc())
    return output.getvalue() or '(no output; use print() to see results)'


class MaterialsAgent(Agent):
    """A LLM powered agent for materials design."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model = model
        self.client: ClaudeSDKClient | None = None
        # Variables the LLM's code can see. It persists between tool calls,
        # so a handle or structure created in one call can be reused later.
        self.namespace: dict[str, Any] = {}

    async def agent_on_startup(self) -> None:
        self.namespace.update({
            'agent': self,
            'Agent': Agent,
            'Handle': Handle,
            'ase': ase,
        })

        @tool(
            'execute_python',
            (
                'Execute Python code inside the materials agent. Variables '
                'persist between calls and top-level `await` is allowed. '
                'Use print() to see results.'
            ),
            {'code': str},
        )
        async def execute_python(args: dict[str, Any]) -> dict[str, Any]:
            output = await run_python(args['code'], self.namespace)
            return {'content': [{'type': 'text', 'text': output}]}

        options = ClaudeAgentOptions(
            model=self.model,
            system_prompt=(
                'You are an assistant to an expert materials scientist. '
                'You can run Python with the `execute_python` tool. '
                'You are running inside an Academy agent, and other agents '
                'with useful capabilities are available on the exchange. '
                'The following are already defined:\n'
                '- `agent`: this agent.\n'
                '- `Agent`: the base class of all agents.\n'
                '- `Handle`: used to talk to another agent.\n'
                '- `ase`: the Atomic Simulation Environment.\n'
                '\n'
                'Use the exchange to find agents and the actions they offer:\n'
                '1. `await agent.agent_exchange_client.discover(Agent)` '
                'returns a tuple of IDs of all running agents (including '
                'your own, `agent.agent_id`).\n'
                '2. `handle = Handle(agent_id)` creates a handle to an agent.\n'
                '3. `await handle.agent_describe()` returns a description of '
                'the agent, with `.description` and `.actions`, a dict '
                'mapping action names to their type signature and docstring.\n'
                '4. Call an action with `await handle.<action_name>(...)`.\n'
                '\n'
                'Energies are in eV and lengths in Angstrom.'
            ),
            mcp_servers={
                'python': create_sdk_mcp_server('python', tools=[execute_python]),
            },
            # Only expose our tools, not built-in or user-configured ones
            tools=[],
            strict_mcp_config=True,
            allowed_tools=['mcp__python__execute_python'],
            max_turns=12,
        )

        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()

    async def agent_on_shutdown(self) -> None:
        if self.client is not None:
            await self.client.disconnect()

    @action
    async def query(self, prompt: str) -> str:
        """Ask the materials agent a question."""
        result = ''
        await self.client.query(prompt)
        async for message in self.client.receive_response():
            if isinstance(message, ResultMessage):
                result = message.result or ''
        return result


async def main(model: str = DEFAULT_MODEL) -> None:

    if 'ACADEMY_TUTORIAL_ENDPOINT' in os.environ:
        # NOTE: The tutorial endpoint is limited to 2 agents per user
        executor = GCExecutor(os.environ['ACADEMY_TUTORIAL_ENDPOINT'])
    else:
        mp_context = multiprocessing.get_context('spawn')
        executor = ProcessPoolExecutor(
            max_workers=3,
            mp_context=mp_context,
        )

    async with await Manager.from_exchange_factory(
        factory=HttpExchangeFactory(),
        log_config=recommended_logging(),
        executors=...,  # TODO: Pass the executor to the manager
    ) as manager:
        logger.info('Launching agents.')

        mlip_agent = ...  # TODO: Launch with the passed executor
        
        # Wait for the MLIP agent to launch 
        await mlip_agent.ping()

        # TODO: Launch the materials agent locally, on the event loop
        # (pass kwargs={'model': model})
        hdl = ...

        result = await hdl.query(
            'First, compute the energy of ethanol. Then, in a separate '
            'call, compute the energy of its isomer dimethyl ether '
            '(both are C2H6O). Which one is more stable, and by how much?',
        )
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
