"""A simple utility to dump the entire MQTT state of a Venus OS device."""

import argparse
import json
import asyncio
import logging
from ..hub import Hub


def setup_arguments():
    """Setup the arguments for the script."""
    parser = argparse.ArgumentParser(description="Dump MQTT messages from a Venus OS hub")
    parser.add_argument("--host", default="venus.local.", help="Hostname of the Venus OS hub")
    parser.add_argument("--username", help="Username to use for the MQTT connection")
    parser.add_argument("--password", help="Password to use for the MQTT connection")
    parser.add_argument("--port", type=int, default=1883, help="Port of the Venus OS hub")
    parser.add_argument("--use-ssl", action="store_true", help="Use SSL for the connection")
    parser.add_argument("--verbose", action="store_true", help="output verbose logging information")
    return parser.parse_args()


async def async_main(args):
    """Main function."""
    hub = Hub(host=args.host, port=args.port, username=args.username, password=args.password, use_ssl=args.use_ssl)

    await hub.connect()
    output = await hub.create_full_raw_snapshot()
    await hub.disconnect()
    print(json.dumps(output, indent=4))


def main():
    """Wrapper for async main function."""
    args = setup_arguments()
    # Configure logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(thread)d] - %(message)s'
    )

    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
