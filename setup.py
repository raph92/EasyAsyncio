from setuptools import setup

setup(
    name='easyasyncio',
    version='5.1.0',
    packages=['easyasyncio'],
    url='https://github.com/RaphaelNanje/easyasyncio.git',
    license='MIT',
    author='Raphael Nanje',
    author_email='rtnanje@gmail.com',
    description='A library that makes asyncio simple',
    install_requires=[
        'logzero',
        'aiohttp',
        'https://github.com/RaphaelNanje/easyfilemanager/archive/0.0.1.tar.gz'
    ]
)
