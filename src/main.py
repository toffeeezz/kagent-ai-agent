import asyncio

from modules.gui.app import run


async def loop() -> None:
    run()


def main():
    asyncio.run(loop())
