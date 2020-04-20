from collections import defaultdict, deque, Counter
from numbers import Number
from typing import Dict


class AverageTracker(defaultdict, Dict[str, list]):

    def __init__(self) -> None:
        defaultdict.__init__(self, self._ADeque)

        self.totals = Counter()

        # avg: avg_bandwidth | total: total_bandwidth
        # basically keep the avg display name and total display name separate
        self.total_names: Dict[str, str] = {}

        # maybe regular name is "bandwidth" and the display is "bandwidth(mb)"
        self.display_names: Dict[str, str] = {}

    def add(self, name: str, value: Number):
        self[name].append(value)
        if name in self.total_names:
            self.totals[name] += value

    def track(self, name: str, display_name: str, total_name: str = None):
        if total_name:
            self.total_names[name] = total_name
        if display_name:
            self.display_names[name] = display_name

    def get_average(self, name: str) -> str:
        return '%.2f' % (sum(self.get(name)) / len(self[name]))

    def get_stats(self):
        d = {}
        for key in self:
            if len(self[key]) > 1:
                d[self.display_names.get(key) or key] = self.get_average(key)
            if key in self.total_names:
                d[self.total_names[key]] = self.get_total(key)

        return d

    def get_total(self, key) -> str:
        value = self.totals[key]

        if not isinstance(value, int): return '%.2f' % value
        else: return str(int)

    class _ADeque(deque):

        def __init__(self) -> None:
            super().__init__([], 1000)


if __name__ == '__main__':
    averages = AverageTracker()
    averages['bandwidth'].append(500)
    averages['bandwidth'].append(250)
    averages['bandwidth'].append(50)

    print(averages.get_average('bandwidth'))
