#!/usr/bin/env python3
"""A local MQTT broker for development, so the team does not need broker.hivemq.com.

The public broker is readable by anyone and goes down without warning. For local
work, run this instead and point both the backend and the device at 127.0.0.1.

    python3 scripts/dev_broker.py --port 1883

Then, in other terminals:

    JAGSI_MQTT_HOST=127.0.0.1 uvicorn app.main:app --port 8000
    python3 ../tools/fake_device.py --host 127.0.0.1 --device-id jagsi-watch-01

Install once: pip install amqtt
Note this is a development convenience only. Issue #8 replaces the broker with
Azure IoT Hub and device certificates.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys


async def serve(host: str, port: int) -> None:
    try:
        from amqtt.broker import Broker
    except ImportError:
        print("amqtt is not installed. Run: pip install amqtt", file=sys.stderr)
        raise SystemExit(1)

    broker = Broker(
        {
            "listeners": {"default": {"type": "tcp", "bind": f"{host}:{port}"}},
            "sys_interval": 0,
            "auth": {"allow-anonymous": True, "plugins": ["auth_anonymous"]},
            "topic-check": {"enabled": False},
        }
    )
    await broker.start()
    print(f"MQTT broker listening on {host}:{port}  (Ctrl-C to stop)")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await broker.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description="Local MQTT broker for JagSi development")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
    )
    try:
        asyncio.run(serve(args.host, args.port))
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
