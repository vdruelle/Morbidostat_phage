# Used to make some small tests for the RPi control
import asyncio

async def say_hello(text):
    await asyncio.sleep(10)
    print(text)

async def main():
    tasks = []
    for i in range(5):
        task = asyncio.create_task(say_hello("hello"))
        tasks.append(task)
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())