# Used to make some small tests for the RPi control
import asyncio

async def say_hello(text):
    await asyncio.sleep(text)
    print(text)

async def main():
    for ii in range(5):
        asyncio.create_task(say_hello(ii))
    tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]

    print(asyncio.all_tasks())
    await asyncio.sleep(2.5)
    print(asyncio.all_tasks())
    
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())