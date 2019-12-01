# EasyAsyncio

EasyAsyncio is a Python library for making asyncio simple. The main
use-case is for rapid deployment of small projects using asyncio.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install
easyasyncio.

```bash
pip install -e git+ssh://git@github.com/RaphaelNanje/EasyAsyncio.git#egg=easyasyncio
```

## Usage

```python
import asyncio
import random

from easyasyncio import Prosumer, LoopManager


class PrintNumbersProducer(Prosumer):
    """print numbers asynchronously"""

    def __init__(self, data: int, context):
        super().__init__(data, context)

    async def fill_queue(self):
        """override this abstract class to fill the queue"""
        for i in range(0, self.data):
            await self.queue.put(i)

    async def work(self, number):
        """implement the business logic here"""
        sleep_time = random.randint(1, 3)
        await asyncio.sleep(sleep_time)
        self.logger.info(number)
        self.append()

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the DataHandler displays information about
        this Prosumer.
        """
        return 'print_item'


manager = LoopManager()
manager.add_tasks(PrintNumbersProducer(5, manager.context))
manager.start()
```
### Output
```
[I 191201 00:43:30 queuemanager:14] Creating new queue: print_number...
[I 191201 00:43:31 example1:22] 3
[I 191201 00:43:32 example1:22] 0
[I 191201 00:43:32 example1:22] 2
[I 191201 00:43:33 example1:22] 1
[I 191201 00:43:33 example1:22] 4
[I 191201 00:43:33 prosumer:32] print_number is finished
[I 191201 00:43:33 loopmanager:34] All tasks have completed!
[I 191201 00:43:33 loopmanager:53] Closing...
[I 191201 00:43:33 loopmanager:55] 
    			    elapsed time: 3.003718 secs
    			    print_number success count: 5
    			    print_number's processed per second: 1.6646037236478675
    			    print_number queue: 0 items left
    			    print_number workers: 5
```
## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)