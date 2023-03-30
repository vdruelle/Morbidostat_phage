# Used to make some small tests for the RPi control
import asyncio
import time
from interface import Interface

async def say_hello(dt):
    await asyncio.sleep(dt)
    print("Hello")

async def run_hello_tasks(tasks):
    await asyncio.gather(*tasks)

def run_blocking_function():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*asyncio.all_tasks()))
    print("Done")

if __name__ == '__main__':
    # The loop seems to allow to put events there, and start them only when the run_until_complete function
    # is called.
    loop = asyncio.get_event_loop()

    tmp = Interface()
    task1 = loop.create_task(tmp._run_pump(1, 5))
    task2 = loop.create_task(tmp._run_pump(2, 10))
    print("test")
    time.sleep(3)
    print("test2")
    # tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
    loop.run_until_complete(asyncio.gather(task1, task2))
    print("test3")

    # First batch of tasks
    # tasks1 = [loop.create_task(say_hello(2)) for _ in range(3)]

    # Do other things in your code here...

    # Second batch of tasks
    # tasks2 = [loop.create_task(say_hello(4)) for _ in range(2)]

    # Do other things in your code here...

    # Wait for all tasks to complete
    # loop.run_until_complete(run_hello_tasks(tasks1 + tasks2))