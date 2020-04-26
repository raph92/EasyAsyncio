from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from easyasyncio import Job


class Response(Exception):
    reason: str

    def __init__(self, reason, *args: object) -> None:
        super().__init__(*args)
        self.reason = reason


class RequeueResponse(Response):
    """Processing did not return meaningful data, and it will be added to the
     queue for reprocessing."""

    def __init__(self, reason='requeued', *args: object) -> None:
        super().__init__(reason, *args)


class FutureResponse(Response):
    """The input data was sent to another worker and will be returned later."""

    def __init__(self, reason='awaiting', secondary_reason='',
                 obj: object = None, job: Union[int, 'Job'] = None,
                 *args) -> None:
        super().__init__(reason, *args)
        self.secondary_reason = secondary_reason
        self.obj = obj
        self.job = job


class FailResponse(Response):
    """Processing failed and will consistently fail so it will not be added
    back to the queue and will not be processed in the future."""

    def __init__(self, reason='failed', extra_info='', *args: object) -> None:
        super().__init__(reason, *args)
        self.extra_info = extra_info


class ValidationRequeueResponse(Response):
    """Processing received an invalid input that was fixed and requeued.
    The original queued_data will be added to the failed list and the new one
    will be added to the back of the queue"""

    def __init__(self, new_input, reason='requeue', *args: object) -> None:
        super().__init__(reason, *args)
        self.new_input = new_input


class NoRequeueResponse(Response):
    """Processing did not return a value, but will not be requeued during this
    session. However it will be added on the next run."""

    def __init__(self, reason='temporarily-failed', *args: object) -> None:
        super().__init__(str(reason), *args)


class UnknownResponse(Response):
    def __init__(self, diagnostics: 'Diagnostics', reason='unknown',
                 extra_info='', *args: object) -> None:
        super().__init__(reason, *args)
        self.diagnostics = diagnostics
        self.extra_info = extra_info
