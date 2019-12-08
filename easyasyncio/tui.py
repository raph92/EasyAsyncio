import sys
from typing import TYPE_CHECKING, Iterable, Sized

import asciimatics.widgets as widgets
from asciimatics.event import KeyboardEvent
from asciimatics.scene import Scene
from asciimatics.screen import Screen, _CursesScreen

from . import logger

if TYPE_CHECKING:
    from .loopmanager import LoopManager


class Text(widgets.TextBox):
    def __init__(self, text):
        super().__init__(1, as_string=True)
        self.value = text


class WorkerDetails(widgets.Frame):
    screen: _CursesScreen
    error = ''
    status = ''

    def __init__(self, screen, manager: 'LoopManager'):
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
        self.workers = list(self.manager.context.workers)
        self.worker = self.workers[0]
        self.set_theme('tlj256')

        # header
        self._initiate_header(manager)

        # main layout
        self.main_layout = widgets.Layout([2, 1, 2, 1, 4], fill_frame=True)
        self.add_layout(self.main_layout)

        # ml-0
        names = [(w.name, index) for index, w in enumerate(self.workers)]
        names.append(('-' * 10, len(names)))
        names.append(('Totals', len(names)))

        self.selected = widgets.ListBox(widgets.Widget.FILL_FRAME, names,
                                        on_change=self._on_change, on_select=self._on_change)
        self.main_layout.add_widget(self.selected, 0)

        # ml-1
        self.main_layout.add_widget(widgets.VerticalDivider(), 1)
        # ml-2
        stat_list = []
        for stat in self.worker.stats:
            stat_list.append((f'{stat} count: {self.manager.context.stats[stat]}', stat))
            stat_list.append((f'{stat}\'s count per second: '
                              f'{self.manager.context.stats[stat] / self.manager.context.stats.elapsed_time}', stat))
        self.worker_stat_list = widgets.ListBox(widgets.Widget.FILL_COLUMN, stat_list)
        self.main_layout.add_widget(self.worker_stat_list, 2)
        # ml-4
        self.log_list = widgets.ListBox(widgets.Widget.FILL_COLUMN,
                                        [(msg, index) for index, msg in enumerate(self.worker.logs)])
        self.main_layout.add_widget(self.log_list, 4)

        # footer
        self._initiate_footer()
        self.fix()

    def refresh(self):
        self.text.value = f'Press Q to stop (twice to quit) | Press S to manually save        {WorkerDetails.error}'
        if self.worker:
            logs_ = [(msg, index) for index, msg in enumerate(self.worker.logs)]
            logs_.reverse()
            self.log_list._options = logs_[:50]
            # stats
            self._update_stats()
        elif self.selected_total:
            self._update_totals()

        # header
        header_string = f"{' ' * 24}Status: {self.manager.status}{' ' * 24}Last save: {int(self.manager.context.save_thread.last_saved)} " \
                        f"seconds ago"
        self.header.value = (f"Running: {self.manager.running}"
                             f"             Workers: {len(self.manager.context.workers)}" + header_string)

    def _update_totals(self):
        stat_list = []
        stat_list.append((f'elapsed time: {self.manager.context.stats.elapsed_time: .2f}', len(stat_list)))
        stat_list.append(('-' * 10, len(stat_list)))
        stat_list.append(('', len(stat_list)))
        for name, stat in self.manager.context.data.items():
            if name in self.manager.context.data.do_not_display_list:
                continue
            if isinstance(stat, Iterable) and isinstance(stat, Sized):
                stat = len(stat)
            stat_list.append((f'{name}: {stat}', len(stat_list)))
        stat_list.append(('-' * 10, len(stat_list)))
        stat_in_workers = [stat for worker in self.manager.context.workers for stat in worker.stats]
        for stat, count in self.manager.context.stats.items():
            if stat in stat_in_workers:
                continue
            stat_list.append((f'{stat}: {count}', len(stat_list)))
        self.worker_stat_list._options = stat_list

    def _update_stats(self):
        stat_list = []

        stat_list.append((f'elapsed time: {self.manager.context.stats.elapsed_time: .2f}', len(stat_list)))
        stat_list.append(('', len(stat_list)))
        for stat in self.worker.stats:
            stat_list.append((stat.center(24, '-'), len(stat_list)))

            stat_list.append((f'count: {self.manager.context.stats[stat]}', len(stat_list)))
            stat_list.append((f'per second: '
                              f'{self.manager.context.stats[stat] / self.manager.context.stats.elapsed_time: .2f}',
                              len(stat_list)))
            # if stat == self.worker.name:
            #     stat_list.append((f'time left: '
            #                       f'{self.worker.time_left()} secs', len(stat_list)))
            stat_list.append(('-' * 24, len(stat_list)))
            stat_list.append(('', len(stat_list)))

        queue_string = f'queue size: {(self.worker.working + self.worker.queue.qsize()) if not self.manager.finished else 0}'
        stat_list.append((
            queue_string,
            len(stat_list)))
        stat_list.append((f'workers: {self.worker.max_concurrent}', len(stat_list)))
        stat_list.append((f'status: {self.worker._status}', len(stat_list)))
        self.worker_stat_list._options = stat_list

    def _initiate_header(self, manager):
        self.header_layout = widgets.Layout([1])
        self.add_layout(self.header_layout)
        self.header = widgets.TextBox(1, as_string=True)
        self.header.disabled = True
        self.header.value = f"Running: {manager.running}         Workers: {len(manager.context.workers)}"
        self.header_layout.add_widget(self.header)
        self.header_layout.add_widget(widgets.Divider())

    def _initiate_footer(self):
        footer_layout = widgets.Layout([1])
        self.add_layout(footer_layout)
        footer_layout.add_widget(widgets.Divider())
        self.text = Text(f'Press Q to stop (twice to quit) | Press S to manually save        {self.error}')
        self.text.disabled = True
        footer_layout.add_widget(self.text)

    def _update(self, frame_no):
        super()._update(frame_no)
        self.refresh()

    @property
    def frame_update_count(self):
        # if self.final_update:
        #     return super().frame_update_count
        # if self.manager.finished:
        #     self.final_update = True
        return 1

    def _on_change(self, *args):
        if self.selected.value < len(self.workers):
            self.worker = self.workers[self.selected.value]
            self.selected_total = False
            return

        elif self.selected.value == len(self.selected.options) - 1:
            self.worker = None
            self.selected_total = True


def demo(screen, manager: 'LoopManager'):
    def on_input(event: KeyboardEvent):
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
            sys.exit(0)
        except Exception as e_:
            logger.exception(e_)
            WorkerDetails.error = str(e_)

    while manager.running:
        try:
            worker_details = WorkerDetails(screen, manager)
            scenes = [
                Scene([worker_details], -1, name="Main"),
                # Scene([ContactView(screen)], -1, name="Edit Contact")
            ]

            screen.play(scenes, stop_on_resize=True, allow_int=True, unhandled_input=on_input)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            logger.exception(e)
            WorkerDetails.error = str(e)


def on_screen_ready(manager: 'LoopManager'):
    try:
        Screen.wrapper(demo, arguments=[manager])
    except KeyboardInterrupt:
        exit(0)
