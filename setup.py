from setuptools import setup

setup(
        name='easyasyncio',
        version='9.0.2',
        packages=['easyasyncio'],
        url='https://github.com/RaphaelNanje/easyasyncio.git',
        license='MIT',
        author='Raphael Nanje',
        author_email='rtnanje@gmail.com',
        description='A library that makes asyncio simple',
        install_requires=[
                'aiohttp==3.6.2',
                'asciimatics',
                'diskcache',
                'easyfilemanager @ https://github.com'
                '/RaphaelNanje/easyfilemanager/releases/tag/v3.0.1'

        ],
        python_requires='~=3.6'
)
