from easyasyncio import Producer, JobManager


class PrintNumbersProducer(Producer):
    """print numbers asynchronously"""

    def __init__(self, data: int, **kwargs):
        super().__init__(data, **kwargs)

    async def fill_queue(self):
        """override this abstract method to fill the queue"""
        for i in range(0, self.input_data):
            await self.queue.put(i)
        await self.queue_finished()

    async def do_work(self, number):
        """
        This logic here will be applied to every item in the queue
        """
        # sleep_time = random.randint(1, 3)
        # await asyncio.sleep(sleep_time)
        self.log.info(number)
        self.increment_stat()

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the StatsDisplay displays information about this Producer.
        """
        return 'print_number'


# set autosave to false since we are not saving anything
manager = JobManager(False)

manager.add_jobs(PrintNumbersProducer(1000, max_concurrent=15))
manager.start()

# manager.start_graphics()
