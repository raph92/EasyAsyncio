from setuptools import setup

setup(
        name='easyasyncio',
        version='7.1.0-beta',
        packages=['easyasyncio'],
        url='https://github.com/RaphaelNanje/easyasyncio.git',
        license='MIT',
        author='Raphael Nanje',
        author_email='rtnanje@gmail.com',
        description='A library that makes asyncio simple',
        install_requires=[
                'aiohttp',
                'easyfilemanager @ https://github.com/RaphaelNanje/'
                'easyfilemanager/archive/master.zip',
                'asciimatics'
        ],
        python_requires='~=3.6'
)
