import shutil

import pytest

from easyasyncio import JobManager

manager = JobManager()
data = manager.context.data

shutil.rmtree('./testfiles/')


@pytest.mark.asyncio
async def test_registration():
    d = [[f'test{i}', f'data{i}', f'row{i}'] for i in range(100)]
    headers = 'test,data,row'.split(',')
    data.register('csv', d, './testfiles/test.csv',
                  save_kwargs=dict(headers=headers))
    data['csv'].append('8,9,10'.split(','))
    print(data['csv'])
    await data.save()

    load = data.filemanager.load('csv')
    print(load)
    assert 'test,data,row' in load


@pytest.mark.asyncio
async def test_loading():
    data.register('csv', list(), './testfiles/test.csv')
    load = data.get('csv')
    assert 'test0,data0,row0' in load
