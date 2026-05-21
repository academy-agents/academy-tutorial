import argparse
import asyncio
import uuid

from academy.identifier import AgentId
from academy.exchange import HttpExchangeFactory

async def main(agent_id: uuid.UUID, group_id: uuid.UUID):
    console = await HttpExchangeFactory().console()
    await console.share_mailbox(AgentId(uid=agent_id), group_id)
    await console.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Start the battlehsip tournament agent',
    )
    parser.add_argument(
        '--agent-id',
        '-a',
        type=uuid.UUID,
        help='ID of Agent if mailbox has been registered before.',
    )
    parser.add_argument(
        '--group-id',
        '-g',
        type=uuid.UUID,
        help='ID of Globus group to share agent with.',
    )
    args = parser.parse_args()

    raise SystemExit(asyncio.run(main(args.agent_id, args.group_id)))