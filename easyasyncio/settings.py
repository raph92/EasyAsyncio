import datetime
import logging
import os

import logzero

__version__ = '0.0.1'

if not os.path.exists('logs/'):
    os.mkdir('logs')
logzero.logfile(f'./logs/{datetime.datetime.now().strftime("%y-%m-%d-%H:%M:%S")}.log',
                maxBytes=2e6, backupCount=5)
logzero.loglevel(logging.DEBUG)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:70.0) '
                  'Gecko/20100101 Firefox/70.0'
}


class Settings:
    TITLE = 'Scraper'
    DATA_FILE = 'data.txt'

    debug_stats_interval = 15
    auto_save_interval = 10
