from typing import TYPE_CHECKING

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

    def __init__(self, screen, manager: 'LoopManager'):
        super(WorkerDetails, self).__init__(screen,
                                            screen.height - 5,
                                            screen.width - 10,
                                            hover_focus=True,
                                            can_scroll=False,
                                            title="Details")

        # Create the form for displaying the list of contacts.
        self.manager = manager
        self.workers = list(self.manager.context.workers)
        self.worker = self.workers[0]
        self.set_theme('tlj256')

        # header
        self.header_layout = widgets.Layout([1])
        self.add_layout(self.header_layout)
        self.header = widgets.TextBox(1, as_string=True)
        self.header.disabled = True
        self.header.value = f"Running: {manager.running}         Workers: {len(manager.context.workers)}"
        self.header_layout.add_widget(self.header)
        self.header_layout.add_widget(widgets.Divider())

        # main layout
        self.main_layout = widgets.Layout([2, 1, 2, 1, 4], fill_frame=True)
        self.add_layout(self.main_layout)

        # ml-0
        names = [(w.name, index) for index, w in enumerate(self.workers)]
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
        footer_layout = widgets.Layout([1])
        self.add_layout(footer_layout)
        footer_layout.add_widget(widgets.Divider())
        text = Text('Press Q to stop')
        text.disabled = True
        footer_layout.add_widget(text)

        # for index, d in enumerate(data):
        #     for d_ in d:
        #         lm.add_item(widgets.Label(f'{d_[0]}: {d_[1]}'), index)
        #     lm.next()

        self.fix()

    def refresh(self):
        logs_ = [(msg, index) for index, msg in enumerate(self.worker.logs)]
        logs_.reverse()
        self.log_list._options = logs_[:50]

        # stats
        self._update_stats()

        # header
        finished_string = f"{' ' * 24}FINISHED!" if self.manager.finished else ''
        self.header.value = (f"Running: {self.manager.running}"
                             f"             Workers: {len(self.manager.context.workers)}" + finished_string)

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
            stat_list.append((f'time left: '
                              f'{self.worker.time_left()} secs', len(stat_list)))
            stat_list.append(('-' * 24, len(stat_list)))
            stat_list.append(('', len(stat_list)))

        queue_string = f'queue size: {(self.worker.working + self.worker.queue.qsize()) if not self.manager.finished else 0}'
        stat_list.append((
            queue_string,
            len(stat_list)))
        stat_list.append((f'workers: {self.worker.max_concurrent}', len(stat_list)))
        stat_list.append((f'status: {self.worker._status}', len(stat_list)))
        self.worker_stat_list._options = stat_list

    def _update(self, frame_no):
        super()._update(frame_no)
        self.refresh()

    @property
    def frame_update_count(self):
        if not self.manager.running:
            exit(0)
        return 1

    def _on_change(self, *args):
        self.worker = self.workers[self.selected.value]


def demo(screen, manager: 'LoopManager'):
    def on_input(event: KeyboardEvent):
        if event.key_code == 113:
            manager.stop()
            exit()
        if event.key_code == 115:
            manager.save()

    while manager.running:
        try:
            scenes = [
                Scene([WorkerDetails(screen, manager)], -1, name="Main"),
                # Scene([ContactView(screen)], -1, name="Edit Contact")
            ]

            screen.play(scenes, stop_on_resize=True, allow_int=True, unhandled_input=on_input)
        except KeyboardInterrupt:
            exit(0)
        except Exception as e:
            logger.exception(e)


def on_screen_ready(manager: 'LoopManager'):
    try:
        Screen.wrapper(demo, arguments=[manager])
    except KeyboardInterrupt:
        exit(0)
