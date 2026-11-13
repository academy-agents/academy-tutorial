# Academy Tutorial
---
This tutorial provides a step by step introduction of Academy, from building a simple "Hello World" agent to coordinating a distributed, multi-agent game. The tutorial is structured as 6 modules that are cumulative --- the solution to the previous module provides the necessary information to understand the next module.

*Estimated Time: 40 minutes*

---
## Setup

#### Install Tutorial Package

Clone the repository from github and install the tutorial package. The package will automatically install `academy` as well.  The tutorial requires `python>=3.11;python<3.15`. We recommend completing the tutorial inside a virtual environment with `uv`.
```
git clone git@github.com:academy-agents/academy-tutorial.git
cd academy-tutorial
uv sync
```
This will set up a local environment to complete the tutorial.

### Set-up Inference Provider
The tutorial is written using ClaudeSDKClient to perform LLM inference.
By default, the `.claude/settings.local.json` file points the inference requests to the [ALCF inference service](https://docs.alcf.anl.gov/services/inference-endpoints/).

You must authenticate with Globus to use the inference provider, and be part of the group that we created for this tutorial:
```
uv run alcf-tokens login
```

If you would like to use a different inference provider, first delete the settings file (otherwise its values override your environment variables), then use environment variables to point to any Anthropic API compatible endpoint.
```
rm .claude/settings.local.json
export ANTHROPIC_BASE_URL=<YOUR ENDPOINT>
export ANTHROPIC_API_KEY=<YOUR API KEY>
```
To use Anthropic's API directly, delete the settings file --- it will automatically use an API key or auth token that you have set on your machine.

If your inference provider does not provide `muse-spark-bf16` (the default model), pass your model as a command line argument to each script:
```
uv run python run-01.py --model <MODEL NAME>
```

Each module's starter code is in `starter_code/<module>/`, and the reference solution is in `solutions/<module>/`. Run each script from inside its module directory, e.g.:
```
cd starter_code/01-llm-agent
uv run python run-01.py
```

#### (Optional) Set-up Globus Compute Endpoint
The tutorial also contains a walk through of writing distributed applications with `academy` and `globus compute`. You will need to follow the instructions to setup a [globus compute endpoint](https://globus-compute.readthedocs.io/en/latest/quickstart.html#deploying-an-endpoint) or provide the `endpoint_id` of an endpoint you have access to. In the endpoint environment, you will also need to install the `academy-tutorial` package.
To use the endpoint with the tutorial:
```
export ACADEMY_TUTORIAL_ENDPOINT=<endpoint_id>
```


---
## Helpful links

* [Example](https://docs.academy-agents.org/stable/#example): shows basic usage of most classes and methods needed in this tutorial
* [Getting started guide](https://docs.academy-agents.org/main/get-started/): an annotated example demonstrating basic features of Academy
* [API reference](https://docs.academy-agents.org/main/api/): detailed reference for Academy

---
## Module 01: Your First Agent
In the first module, write a simple chat agent.

The starter code contains an outline of a `HelloWorldAgent` class, which wraps a `ClaudeSDKClient` in an Academy agent.
The `HelloWorldAgent` initializes a Claude session in `agent_on_startup`. Academy calls `agent_on_startup` when the agent is launched.
There is an existing `message` action that sends a message to the session but does not return the response.

To finish this module, first implement a new `query` action that allows another agent or user to query the session and returns the result.
Then, in the `main` function, set the exchange `factory` to a `LocalExchangeFactory`, and launch and query the agent.
Use `manager.launch` to launch the agent and get a `Handle` to that agent.
Then use the handle to call the `query` action that you wrote.


To run the script:
```
uv run python run-01.py
```

---
## Module 02: Agent-Agent Communication
Academy allows you to build multi-agent systems. Agent `Handle`s can be passed to other agents (or created by other agents) to allow one agent to invoke another.

The starter code for Module 02 contains an LLM-driven `MaterialsAgent` and an `MLIPAgent` for calculating interatomic potentials with a machine-learned model.
The code also contains a `run_mlip` function that downloads an MLIP model, loads the model into memory, and performs inference using that model.
Move the code from `run_mlip` into the `MLIPAgent`: the MLIP model should be downloaded and loaded in `agent_on_startup`, and the `predict_energy` action should compute the energy of the structures using the loaded model.
Then launch the `MLIPAgent` in the `main` function.

The `MaterialsAgent` is not given a handle to the `MLIPAgent`. Instead, its LLM writes Python code that discovers the `MLIPAgent` on the exchange and calls it.


To run the script:
```
uv run python run-02.py
```

---
## Module 03: Distributing Computation
Academy integrates with a cloud hosted exchange and `globus compute` to build distributed agentic systems.
The starter code for Module 03 creates an executor used to launch agents: a `GCExecutor` (Globus Compute Executor) if `ACADEMY_TUTORIAL_ENDPOINT` is set, or a `ProcessPoolExecutor` otherwise. The `Manager` uses the `HttpExchangeFactory`, so agents running on different resources can communicate.
Pass the executor to the `Manager` with the `executors` argument; a single executor becomes the default executor for `manager.launch`. Then launch the `MLIPAgent` with the default executor, and launch the `MaterialsAgent` locally by passing `executor='event_loop'` to `manager.launch`.
To keep this module lightweight, the `MLIPAgent` here returns mock energies instead of running the model.

Globus Compute is a FaaS platform that allows you to bring your own compute resource. In `run-compute-function.py` we show an example of running a remote function. To run the test function, set the environment variable, then run:

```
export ACADEMY_TUTORIAL_ENDPOINT=<ENDPOINT_ID>
uv run python run-compute-function.py
```

We will share the ENDPOINT ID during the tutorial.

The script also uses a cloud hosted exchange. The exchange is authenticated with [Globus Auth](https://www.globus.org/platform/services/auth), a federated identity provider. When you run the script you will be asked to give permissions for the `academy` client to use the exchange, and authenticate your token. After you provide the permissions, a token will be created that the `academy` client uses to communicate with the exchange.

To run the script (if `ACADEMY_TUTORIAL_ENDPOINT` is not set, the MLIP agent runs in a local process pool instead):
```
uv run python run-03.py
```

---
## Module 04: Parallel Agents
One class of scientific areas ripe for agents are (1) problems that can be formulated as a search over a large space where human-like heuristics are helpful, and (2) solutions that are able to be verified or evaluated automatically. 
For instance, math proofs are not easy to create without mathematical knowledge, but can be verified automatically with Lean. In contrast, training a model is a similar search over parameters, but doesn't use human-like heuristics (i.e. a human doesn't have very good intuition that this feature should be weighed heavier).

To illustrate and explore these problems, we will use the Wordle game.
Wordle is an interactive guessing game. A game is initialized with a 5 letter word that is hidden from the player. The player guesses a 5 letter word, and the system gives feedback per letter in each position, green if the letter is the right letter in the right spot, yellow if the letter in that position is somewhere else in the hidden word but not in that spot, and grey if the letter at that position is not in the hidden word.
Typically a player has 6 guesses to figure out the target word, but in this codebase we do not enforce this limit.


In this activity, we will build an agent swarm to solve Wordle.
First implement the `play_wordle` action.
Set the `self.game` attribute in the `WordleAgent` so that the LLM's `wordle_feedback` tool makes guesses against that game.
Then prompt the LLM to solve the game and return its final result.
In the `main` function, launch 2 agents, and have them play the same game in parallel (e.g., with `asyncio.gather`).

To run the script:
```
uv run python run-04.py
```


## Module 05: Blackboard Communication
Now we will set up group communication between agents.
We will use a decentralized pattern: each agent is independently searching for the same goal but can explicitly share information with other agents.

The starter code implements the outlines of a blackboard for communication. This is one pattern of communication where an agent can write a message or status to other agents, but only the latest status from each agent is available for the other agents to read. Look at how the `read_blackboard` and `write_blackboard` tools are implemented using the `insight_dict` attribute of the `WordleAgent`. Then implement `receive_information`, the action that `write_blackboard` calls on each peer to share information. It should store the information in `insight_dict`, keyed by the sender's ID (`context.source_id`).

To run the script:
```
uv run python run-05.py
```

## Module 06: Centralized Orchestration
Next, we use worker agents to search for the best strategy for playing wordle and use that strategy to play the game.
First look at the `StrategyAgent`, which is written to investigate a particular strategy. Instead of making guesses against a fixed game, it is given a `simulate_feedback` tool, which allows it to simulate a guess.
The strategy agent can simulate how a strategy performs on an imagined set of games, but cannot play the real game.
The `CoordinatorAgent` implements a search over candidate strategies.

First implement `find_strategy`, which uses the worker agents. The `self.search_client` LLM client already has an `evaluate_strategies` tool that uses the worker agents, so send it the prompt (the `run` helper is useful) and return the best strategy.
Then in `main`, launch the coordinator agent with the worker handles, and before playing a wordle game, use `find_strategy` to find the best strategy.

To run the script:
```
uv run python run-06.py
```

## Module 07: Observing Agents
Lastly, we will look at monitoring and observing remotely deployed agents. `academy-dashboard` is a package that connects Academy agents to a cloud-hosted (or locally hosted) dashboard.
Go to [dashboard.academy-agents.org](https://dashboard.academy-agents.org) and log in using Globus.
Create an agent on the dashboard. Each dashboard agent organizes the display and logs for one project or campaign.
Copy the UUID of the agent.

`run-07.py` is a complete version of Module 01, built as a `MonitoredAgent`. This agent is initialized with the ID of the dashboard agent. `MonitoredAgent` forwards the agent's logs to the dashboard so they can be observed remotely. It also adds actions that allow the dashboard to manage the agent.

The dashboard requires Python 3.13. If you have python 3.13, install the dashboard code with:
```
uv python pin 3.13
uv sync --extra dashboard
```

To run the script:
```
uv run python run-07.py --user-agent-id <DASHBOARD_ID>
```
