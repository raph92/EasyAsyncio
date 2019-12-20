import _curses
import sys
from typing import TYPE_CHECKING, Iterable, Sized, List, Tuple, Optional

import asciimatics.widgets as widgets
from asciimatics.event import KeyboardEvent
from asciimatics.exceptions import ResizeScreenError
from asciimatics.scene import Scene
from asciimatics.screen import Screen, _CursesScreen

from . import logger

if TYPE_CHECKING:
    from .jobmanager import JobManager
    from .job import Job

logger = logger.getChild('tui')


class Text(widgets.TextBox):
    def __init__(self, text: str) -> None:
        super().__init__(1, as_string=True)
        self.value = text


class WorkerDetails(widgets.Frame):
    screen: _CursesScreen
    error = ''
    status = ''

    def __init__(self, screen: Screen, manager: 'JobManager') -> None:
        super(WorkerDetails, self).__init__(screen,
                                            screen.height - 5,
                                            screen.width - 10,
                                            hover_focus=True,
                                            can_scroll=False,
                                            title="Details")
        self.selected_total = False
        self.final_update = False
        # Create the form for displaying the list of contacts.
        self.manager = manager
        self.jobs = list(self.manager.context.jobs)
        self.worker: 'Optional[Job]' = self.jobs[0]
        self.set_theme('tlj256')

        # header
        self._initiate_header()

        # main layout
        self.main_layout = widgets.Layout([2, 1, 2, 1, 4], fill_frame=True)
        self.add_layout(self.main_layout)

        # ml-0
        names = [(w.name, index) for index, w in enumerate(self.jobs)]
        names.append(('-' * 10, len(names)))
        names.append(('Totals', len(names)))

        self.selected = widgets.ListBox(widgets.Widget.FILL_FRAME, names,
                                        on_change=self._on_change,
                                        on_select=self._on_change)
        self.main_layout.add_widget(self.selected, 0)

        # ml-1
        self.main_layout.add_widget(widgets.VerticalDivider(), 1)
        # ml-2
        self.worker_stat_list = widgets.ListBox(widgets.Widget.FILL_COLUMN,
                                                [('', '-----')])
        self.main_layout.add_widget(self.worker_stat_list, 2)
        # ml-4
        self.log_list = widgets.ListBox(widgets.Widget.FILL_COLUMN,
                                        [('', '-----')])
        self.main_layout.add_widget(self.log_list, 4)

        # footer
        self._initiate_footer()
        self.fix()

    def refresh(self) -> None:
        string = 'Press Q to stop (twice to quit) | Press S to manually save'
        self.text.value = f'{string}{" " * 8}{WorkerDetails.error}'
        if self.worker:
            # prevent mutation during iteration
            worker_logs = self.worker.logs.copy()
            logs_ = [(msg, index) for index, msg in
                     enumerate(worker_logs)]
            logs_.reverse()
            self.log_list._options = logs_
            # stats
            self._update_stats()
        elif self.selected_total:
            self._update_totals()
            logs_ = [(msg, index) for index, msg in
                     enumerate(self.manager.logs)]
            logs_.reverse()
            self.log_list._options = logs_[:50]
        # header
        self._refresh_header()

    def _refresh_header(self) -> None:
        last_saved = self.manager.context.save_thread.last_saved
        elapsed_time = self.manager.context.stats.elapsed_time
        self.running_label._text = f'Elapsed time: {elapsed_time : .2f}'
        self.workers_label._text = (f'Workers: '
                                    f'{len(self.manager.context.jobs)}')
        self.status_label._text = f'Status: {self.manager.status}'
        self.last_save_label._text = f'Last save: {int(last_saved)} secs'

    def _update_totals(self) -> None:
        stat_list: List[Tuple[str, int]] = []
        elapsed_time = self.manager.context.stats.elapsed_time
        stat_list.append((
                f'elapsed time: {elapsed_time : .2f}', len(stat_list)))
        stat_list.append(('-' * 10, len(stat_list)))
        stat_list.append(('', len(stat_list)))
        for name, stat in self.manager.context.data.items():
            if name in self.manager.context.data.do_not_display:
                continue
            if isinstance(stat, Iterable) and isinstance(stat, Sized):
                stat = len(stat)
            stat_list.append((f'{name}: {stat}', len(stat_list)))
        stat_list.append(('-' * 10, len(stat_list)))
        stat_in_workers = [stat for worker in self.manager.context.jobs for
                           stat in worker.stats]
        for stat, count in self.manager.context.stats.items():
            if stat in stat_in_workers:
                continue
            stat_list.append((f'{stat}: {count}', len(stat_list)))
        self.worker_stat_list._options = stat_list

    def _update_stats(self) -> None:
        stat_list: List[Tuple[str, int]] = []
        for stat in self.worker.stats:
            stat_list.append((stat.center(24, '-'), len(stat_list)))

            stat_list.append((f'count: {self.worker.stats[stat]}',
                              len(stat_list)))
            elapsed_time = self.manager.context.stats.elapsed_time
            per_second = self.worker.stats[stat] / elapsed_time
            stat_list.append((f'per second: {per_second : .2f}',
                              len(stat_list)))
            stat_list.append(('-' * 24, len(stat_list)))
            stat_list.append(('', len(stat_list)))

        worker_queue_qsize = self.worker.working + self.worker.queue.qsize()
        finished_else_ = worker_queue_qsize if not self.manager.finished else 0
        queue_string = f'queue size: {finished_else_}'
        stat_list.append((
                queue_string,
                len(stat_list)))
        for stat, value in self.worker.info.items():
            stat_list.append(
                    (f'{stat}: {value}', len(stat_list)))
        self.worker_stat_list._options = stat_list

    def _initiate_header(self) -> None:
        self.header_layout = widgets.Layout([1, 1, 1, 1])
        self.add_layout(self.header_layout)

        self.running_label = widgets.Label(f'', align='^')
        self.workers_label = widgets.Label(f'', align='^')
        self.status_label = widgets.Label(f'', align='^')
        self.last_save_label = widgets.Label(f'', align='^')

        self.header_layout.add_widget(self.running_label, 0)
        self.header_layout.add_widget(self.workers_label, 1)
        self.header_layout.add_widget(self.status_label, 2)
        self.header_layout.add_widget(self.last_save_label, 3)

        self.header_layout.add_widget(widgets.Divider(), 0)
        self.header_layout.add_widget(widgets.Divider(), 1)
        self.header_layout.add_widget(widgets.Divider(), 2)
        self.header_layout.add_widget(widgets.Divider(), 3)

    def _initiate_footer(self) -> None:
        footer_layout = widgets.Layout([1])
        self.add_layout(footer_layout)
        footer_layout.add_widget(widgets.Divider())
        q_to_stop_string = 'Press Q to stop (twice to quit)'
        s_to_save_string = 'Press S to manually save'
        self.text = Text(
                f'{q_to_stop_string} | {s_to_save_string}        {self.error}')
        self.text.disabled = True
        footer_layout.add_widget(self.text)

    def _update(self, frame_no: int) -> None:
        super()._update(frame_no)
        self.refresh()

    @property
    def frame_update_count(self) -> int:
        return 1

    def _on_change(self) -> None:
        if self.selected.value < len(self.jobs):
            self.worker = self.jobs[self.selected.value]
            self.selected_total = False
            return

        elif self.selected.value == len(self.selected.options) - 1:
            self.worker = None
            self.selected_total = True


def demo(screen: Screen, manager: 'JobManager') -> None:
    def on_input(event: KeyboardEvent) -> None:
        try:
            if event.key_code == 113:
                if WorkerDetails.status == 'Stopping...':
                    sys.exit(0)
                manager.stop()
                screen.force_update()
                WorkerDetails.status = 'Stopping...'
            if event.key_code == 115:
                manager.save()
        except AttributeError:
            pass
        except Exception as e_:
            WorkerDetails.error = str(e_)

    worker_details = WorkerDetails(screen, manager)
    scenes = [
            Scene([worker_details], -1, name="Main"),
    ]

    screen.play(scenes, stop_on_resize=True, allow_int=True,
                unhandled_input=on_input)


def on_screen_ready(manager: 'JobManager') -> None:
    while manager.running:
        try:
            Screen.wrapper(demo, catch_interrupt=True, arguments=[manager])
            sys.exit(0)
        except _curses.error:
            logger.error('Please run this in a terminal or '
                         'do not call LoopManager.start_graphics()')
            sys.exit(2)
        except ResizeScreenError:
            pass
        except KeyboardInterrupt:
            sys.exit(3)
        except Exception as e:
            logger.exception(e)
            WorkerDetails.error = str(e)
