# Used to make some small tests for the RPi control
import asyncio


class Interface:
    def __init__(self) -> None:
        self.tasks = []

    def add_pumping(self, pump, dt):
        async def _pump_coroutine(pump, dt):
            print(f"Starting pump {pump}.")
            await asyncio.sleep(dt)
            print(f"Pump {pump} finished after {dt} seconds.")

        self.tasks.append(asyncio.ensure_future(_pump_coroutine(pump, dt)))

    def launch_pump(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*self.tasks))
        self.tasks = []


if __name__ == "__main__":
    tmp = Interface()
    print("test")
    tmp.add_pumping(1, 2)
    tmp.add_pumping(2, 4)
    tmp.launch_pump()
    print("test2")
