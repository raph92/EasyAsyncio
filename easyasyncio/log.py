import datetime
import logging
import os

start_date = datetime.datetime.now().strftime("%y-%m-%d-%H%M%S")
_path = f'./logs/{start_date}/logs.log'
if not os.path.exists(os.path.split(_path)[0]):
    os.makedirs(os.path.split(_path)[0])

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)s:%(lineno)d '
                           '%(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S',
                    filename=_path,
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)
