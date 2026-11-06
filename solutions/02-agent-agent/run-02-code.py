from __future__ import annotations

import ast
import asyncio
import contextlib
import inspect
import io
import logging
import traceback
from typing import Any

import ase
import ase.build  # noqa: F401  (makes ase.build available to the LLM)
from huggingface_hub import snapshot_download
from mlip.inference import run_batched_inference
from mlip.models import Visnet
from mlip.models.model_io import load_model_from_zip

from academy.agent import action
from academy.agent import Agent
from academy.exchange import LocalExchangeFactory
from academy.handle import Handle
from academy.logging.recommended import recommended_logging
from academy.manager import Manager
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk import ResultMessage
from claude_agent_sdk import create_sdk_mcp_server
from claude_agent_sdk import tool

logger = logging.getLogger(__name__)


class MLIPAgent(Agent):
    """Wraps a machine-learned interatomic potential.

    This agent knows nothing about LLMs: it takes `ase.Atoms` and returns
    plain Python numbers, so any agent (or script) can use it.
    """

    async def agent_on_startup(self) -> None:
        # Download and load the model off the event loop
        await asyncio.to_thread(
            snapshot_download,
            repo_id='InstaDeepAI/MLIP-tutorials',
            allow_patterns='simulation/*',
            local_dir='.',
        )
        self.force_field = await asyncio.to_thread(
            load_model_from_zip,
            Visnet,
            'simulation/example_model_v2.zip',
        )

    @action
    async def predict_energy(self, structures: list[ase.Atoms]) -> list[float]:
        """Predict the energy (eV) of each structure."""
        predictions = await asyncio.to_thread(
            run_batched_inference,
            structures,
            self.force_field,
        )
        # Convert jax arrays to floats before sending them over the exchange
        return [float(pred.energy) for pred in predictions]


async def run_python(code: str, namespace: dict[str, Any]) -> str:
    """Execute code in `namespace` and return everything it printed.

    The code may use top-level `await`, so the LLM can call handles directly.
    Exceptions are returned as a traceback so the LLM can fix its code.
    """
    output = io.StringIO()
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
    """A LLM powered agent for materials design.

    The LLM writes Python that runs inside this agent, so it can use the
    agent's exchange client to discover the MLIPAgent and call it.
    """

    def __init__(self) -> None:
        self.model = 'claude-haiku-4-5'
        self.client: ClaudeSDKClient | None = None
        # Variables the LLM's code can see. It persists between tool calls,
        # so a handle or structure created in one call can be reused later.
        self.namespace: dict[str, Any] = {}

    async def agent_on_startup(self) -> None:
        self.namespace.update({
            'agent': self,
            'Handle': Handle,
            'MLIPAgent': MLIPAgent,
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
                'The following are already defined:\n'
                '- `agent`: this agent. Find other agents with '
                '`await agent.agent_exchange_client.discover(MLIPAgent)`, '
                'which returns a tuple of agent IDs.\n'
                '- `Handle`: wrap an agent ID with `Handle(agent_id)` to '
                'call its actions.\n'
                '- `MLIPAgent`: has the action '
                '`await handle.predict_energy(structures: list[ase.Atoms]) '
                '-> list[float]`, returning energies in eV.\n'
                '- `ase`: the Atomic Simulation Environment, e.g. '
                '`ase.build.bulk(...)`.\n'
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


async def main() -> None:
    async with await Manager.from_exchange_factory(
        factory=LocalExchangeFactory(),
        log_config=recommended_logging(),
    ) as manager:
        logger.info('Launching agents.')

        # Note: we do NOT pass the MLIPAgent handle to the MaterialsAgent.
        # The LLM finds it on its own by writing code that uses the exchange.
        await manager.launch(MLIPAgent)
        hdl = await manager.launch(MaterialsAgent)

        result = await hdl.query(
            'Which is more stable for silicon: diamond or fcc? '
            'Scan a few lattice constants for each and report the lowest '
            'energy per atom you find.',
        )
        logger.info(f'Agent response: {result}')


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
