import asyncio

from easyasyncio import Producer, JobManager, Constants


class WithSessionProducer(Producer):
    """requests websites asynchronously"""

    def __init__(self, data: int, **kwargs):
        super().__init__(data, **kwargs)

    async def fill_queue(self):
        """override this abstract method to fill the queue"""
        for i in range(0, self.input_data):
            await self.queue.put(i)
        await self.queue_finished()

    async def do_work(self, number):
        """implement the business logic here"""
        await asyncio.sleep(1)
        try:
            async with self.context.session.get(
                    'http://127.0.0.1:5500/temp.html',
                    headers=Constants.HEADERS
            ) as response:
                text = await response.read()
                self.log.ino("%s %s", number, str(text))
            self.increment_stat()
        except Exception as e:
            self.log.exception(e)
            self.with_errors = True

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the StatsDisplay displays information about
        this AsyncWorker.
        """
        return 'parse_request'


manager = JobManager(auto_save=False, use_session=True)
manager.add_jobs(WithSessionProducer(100, max_concurrent=15))

manager.start()
manager.start_graphics()