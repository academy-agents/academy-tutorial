# 07: Academy Dashboard

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