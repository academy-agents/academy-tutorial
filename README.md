# Academy Tutorial
---
This tutorial provides a step by step introduction of Academy, from building a simple "Hello World" agent to coordinating a distributed, multi-agent game. The tutorial is structured as 5 modules that are cumulative --- the solution to the previous module provides the necessary information to understand the next module.

*Estimated Time: 1 hour*

---
## Setup

#### Install Tutorial Package

Clone the repository from github and install the tutorial package. The package will automatically install `academy` as well.  The tutorial requires `python>=3.12`. We recommend completing the tutorial inside a virtual environment.
```
git clone git@github.com:academy-agents/academy-tutorial.git
cd academy-tutorial
python -m venv venv
. ./venv/bin/activate
pip install .
python -m ipykernel install --user --name=academy-tutorial --display-name="Python (Academy)"
```
This will set up a local environment to complete the tutorial.

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
## Module 01: Simple Actor-Client Application:
In the first module, we will write a simple example of launching a stateful actor and invoking actions from a user program.

The starter code contains an outline of an `Agent` class and a `Manager` class. In the `Counter` agent class add two new functions `increment` and `get_count` annotated with `@action` decorator.
In the `manager` context, first fill in the `factory` and the `executors` arguments. Then use `manager.launch` to launch the counter agent, and create a handle to the newly launched agent. To verify that the agent launched and is running call the `increment` and `get_count` methods of the agent using the handle.

To run the script:
```
python run-01.py
```

---
## Module 02: Adding "Autonomy"
Academy allows `agents` to express autonomous action using the `@loop` decorator. This can be used to monitor and respond to changing state or environment.

Using the completed code from Module 01, change the increment method to a loop that increments the value of count every one second.
To observe that it is working, change the `increment` call within the manager context to a `asyncio.sleep`. The `agent.count` should increment for how ever long the sleep is called.

To run the script:
```
python run-02.py
```

---
## Module 03: Agent-Agent Communication
Academy allows you to build multi-agent systems. Agent `Handle`s can be passed to other agents (or created by other agents) to allow one agent to invoke another.

The starter code for Module 03 contains a coordinator class that should lower and reverse a string using two other agents. Fill in the constructor to accept `Handle`s to the `Lowerer` and `Reverser` agents and store them as part of the `Coordinator` state. Then fill in the `process` action to invoke each handle.
In the `manager` context, launch the `Coordinator` agent. You can pass arguments to the `Coordinator`constructor using the `args=` argument of `manager.launch`

To run the script:
```
python run-03.py
```

---
## Module 04: Distributing Computation
Academy integrates with a cloud hosted exchange and `globus compute` to build distributed agentic systems.
In the starter code for Module 04, fill in the constructor of an executor used to launch agents with the `GCExecutor` (Globus Compute Executor) or a `ProcessPoolExecutor` if you do not have a Globus Compute Endpoint available. Then complete the Manager context with the appropriate fields. For the `factory` use the `HttpExchangeFactory`, which by defaults points at our hosted exchange `https:exchange.academy-agents.org` with `auth_method='globus'`. For the `executors` field use the `GCExecutor` or `ProcessPoolExecutor` you created above.
This will enable you to launch the agents across distributed resources.

Globus Compute is a FaaS platform that allows you to bring your own compute resource. In `run-compute-function.py` we show an example of running a remote function.

The script also uses a cloud hosted exchange. The exchange is authenticated with [globus auth](https://www.globus.org/platform/services/auth), and federated identification provider. When you run the script you will be asked to give permissions for the `academy` client to use the exchange, and authenticate your token. After you provide the permissions, a token will be created that the `academy` client uses to communicate with the exchange.

To run the script:
```
python run-04.py
```

---
## Module 05: Battleship
Next, we use `academy` to build a battleship game. Battleship consists of two agents --- a `coordinator` the manages the game state, and multiple instance of the `player` agent which implements a strategy.

Implement the player strategy for guessing where opponent ships are and for placing ships on your board.

To run the script:
```
python run-05.py
```

Link to join ISC Battleship Group for the Tournament:

[https://app.globus.org/groups/301fe241-5556-11f1-97c5-0eea096e6be1/about](https://app.globus.org/groups/301fe241-5556-11f1-97c5-0eea096e6be1/about)


## Module 06: LLM Agent
`academy` combines with LLM agent harnesses to deploy intelligent agents in federated and parallel environments.
In `run-06.py` we have used `langchain` to build a LLM agent to play `wordle` in a team.
We want to start multiple agents in parallel and have them communicate with each other to solve the puzzle.

To run this script you will need access to a LLM (i.e. any API key). Follow instructions from your LLM provider to set the correct environment variables and update the model used in the script to point to your hosted model.

In `run-06.py` first fill in the `share_information` method to call actions on other agents.
Then, add the `share_information` method to the `langchain.agent.create_agent` function as a tool for the LLM.
In order to enable circular dependencies (each agent depends on each other), `academy` lets  separates the creation of mailboxes from the launching of agents.
First, in the main method, use `manager.register_agent` to create the mailbox for each `WordleAgent`.
Then, use the list of assembled handles and `manager.launch` to launch the agents.

Here's a link with a key:
https://docs.google.com/document/d/1jrhiS7zSre94VvJVeO6RjbEAuvMRTk3zg_ICdzk0Mg8/edit?tab=t.0

To run the script:
```
python run-06.py
```

## Module 07: Academy Dashboard
One exciting direction of agent research is human/agent collaboration, or human-in-the-loop design.
Academy is developing a dashboard for monitoring and controlling agentic applications.
The dashboard is hosted at [https://dashboard.academy-agents.org](https://dashboard.academy-agents.org]).

First, go to that web application and log in using Globus federated log in.
Then click the (+ New Agent) button, which will launch a dashboard for you. Conceptually, the dashboard is another `Agent`, so the same principles that we learned for agents apply to the dashboard -- it is mapped to an AgentId, has a mailbox on the exchange, and communicates using actions. Copy the uuid from the dashboard, which is the AgentId that we need to send messages to the dashboard.

Run `export USER_AGENT_ID=<uuid>` to point to the dashboard that you launched. Then fill in the TODOs in that `run-07.py`. Change the constructed Agent class to inherit from `academy-dashboard.MonitoredAgent` instead of `Agent`. Write a log message in the agent that will show up in the dashboard. Change the options of the user-prompt in the agent that will be shown as a pop-pu in the dashboard.

To run the script:
```
python run-07.py
```
Be sure to watch the dashboard and approve the prompt when it appears.
