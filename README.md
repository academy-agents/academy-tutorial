# Academy Tutorial
---
This tutorial provides a step by step introduction of Academy, from building a simple "Hello World" agent to coordinating a distributed, multi-agent game. The tutorial is structured as 5 modules that are cumulative --- the solution to the previous module provides the necessary information to understand the next module.

*Estimated Time: 40 minutes*

---
## Setup

#### Install Tutorial Package

Clone the repository from github and install the tutorial package. The package will automatically install `academy` as well.  The tutorial requires `python>=3.12`. We recommend completing the tutorial inside a virtual environment with `uv`.
```
git clone git@github.com:academy-agents/academy-tutorial.git
cd academy-tutorial
uv sync
```
This will set up a local environment to complete the tutorial.

### Set-up Infernce Provider
The tutorial is written using ClaudeSDKClient to perform LLM inference.
If you are not authenticated with anthropic, or would like to use a different inference provider, use environment varaibles to point to any Anthropic API compatible endpoint.
```
export ANTHROPIC_BASE_URL=<YOUR ENDPOINT>
export ANTHRPOIC_API_KEY=<YOUR API KEY>
```

I your inference provider does not provide `claude-haiku-5.5`, you should pass your model as a command line argument to each applicable script:
```
uv run python run-01.py --model <>
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

The starter code contains an outline of an `HelloWorldAgent` class, which wraps a `ClaudeSKDClient` in a Academy agent.
The `HelloWorldAgent` initializes a `claude` session as part of `agent_on_startup`. Academy call `agent_on_startup` when the agent is launched.
There is a existing action that allows a user to message the session, but not receive messages.

To finish implementing this module, first implement a new `query` action that allows a different agent or user to query the session and returns the result
Then in the `main` function launch and message the agent.
Use `manager.launch` to launch the agent nad get a `Handle` to that agent.
Then use the handle to call the `query` method that you wrote.


To run the script:
```
uv run python run-01.py
```

---
## Module 02: Agent-Agent Communication
Academy allows you to build multi-agent systems. Agent `Handle`s can be passed to other agents (or created by other agents) to allow one agent to invoke another.

The starter code for Module 02 contains a LLM-driven `MaterialsAgent` and a `MLIPAgent`for calculating inter-atomic potentials from a ML model.
The code also contains a function for downloading an MLIP model, loading the model into memory, and performing infernence using that model.
Rewrite the `run_mlip` function inside of the `MLIPAgent`. The MLIP model should be downloaded and loaded when the agent is started. Then the `predict_energy` function should compute the energy of the strucutres.
Launch the `MLIPAgent` in the `main` function.


To run the script:
```
uv run python run-02.py
```

---
## Module 03: Distributing Computation
Academy integrates with a cloud hosted exchange and `globus compute` to build distributed agentic systems.
In the starter code for Module 04, fill in the constructor of an executor used to launch agents with the `GCExecutor` (Globus Compute Executor) or a `ProcessPoolExecutor` if you do not have a Globus Compute Endpoint available. Then complete the Manager context with the appropriate fields. For the `factory` use the `HttpExchangeFactory`. For the `executors` field use the `GCExecutor` or `ProcessPoolExecutor` you created above.
This will enable you to launch the agents across distributed resources.

Globus Compute is a FaaS platform that allows you to bring your own compute resource. In `run-compute-function.py` we show an example of running a remote function. To run the test function, set the environment variable, then run:
```
export ACADEMY_TUTORIAL_ENDPOINT=<ENDPOINT_ID>
uv run python run-compute-function.py
```

The script also uses a cloud hosted exchange. The exchange is authenticated with [globus auth](https://www.globus.org/platform/services/auth), and federated identification provider. When you run the script you will be asked to give permissions for the `academy` client to use the exchange, and authenticate your token. After you provide the permissions, a token will be created that the `academy` client uses to communicate with the exchange.

To run the script:
```
uv run python run-03.py
```

---
## Module 04: Parallel Agents

To run the script:
```
uv run python run-04.py
```


## Module 05: Blackboard Communication

To run the script:
```
uv run python run-06.py
```

## Module 06: Sub-Agents
To run the script:
```
uv run python run-06.py
```