#!/usr/bin/env python

import json
import logging
from os.path import exists
from sqlite3 import OperationalError
from typing import Union

import click
import diskcache

from easyasyncio import CacheSet

logger = logging.getLogger('decache')


def _load(cache_file) -> Union[dict, list]:
    if not exists(cache_file):
        raise FileNotFoundError('Cache file not found', cache_file)
    try:
        deque = diskcache.Deque([], cache_file)
    except OperationalError:
        pass
    except Exception as e:
        logger.exception(e)
    else:
        return list(deque)
    try:
        cache_set = CacheSet([], cache_file)
        list_ = list(cache_set)
        index = diskcache.Index(cache_set.index)
        # make sure we are dealing with a CacheSet and not just an Index
        pop = list_[0]
        if index[cache_set._hash(pop)] != pop:
            raise TypeError('The provided cache is not a CacheSet', cache_set)
    except OperationalError:
        pass
    except Exception as e:
        logger.exception(e)
    else:
        return list_
    try:
        index = diskcache.Index(cache_file)
    except OperationalError:
        pass
    except Exception as e:
        logger.exception(e)
    else:
        return dict(index)
    raise Exception('Unable to open cache file')


@click.command()
@click.argument('cache-file', type=str)
@click.argument('output', type=str)
def core(cache_file: str, output: str):
    try:
        cache_file = cache_file.replace('cache.db', '')
        data = _load(cache_file)
    except Exception:
        click.echo('Error loading cache file')
        raise
    else:
        with open(output, 'w') as f:
            if isinstance(data, dict):
                json.dump(data, f)
            elif isinstance(data, list):
                f.write('\n'.join([str(d) for d in data]))
        click.echo('Output %s lines to %s' % (len(data), output))
