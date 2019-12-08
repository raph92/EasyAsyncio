from setuptools import setup

setup(
    name='easyasyncio',
    version='5.5.6',
    packages=['easyasyncio'],
    url='https://github.com/RaphaelNanje/easyasyncio.git',
    license='MIT',
    author='Raphael Nanje',
    author_email='rtnanje@gmail.com',
    description='A library that makes asyncio simple',
    install_requires=[
        'logzero',
        'aiohttp',
        'requests',
        'easyfilemanager @ https://github.com/RaphaelNanje/easyfilemanager.git#egg=easyfilemanager-0.0.1'
    ],
    dependency_links=[],
    python_requies='~=3.6'
)
