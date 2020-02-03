from setuptools import setup

setup(
        name='easyasyncio',
        version='11.3.0',
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
                '/RaphaelNanje/easyfilemanager/archive/v3.1.1.tar.gz',
                'uvloop',
                'click'

        ],
        python_requires='~=3.6',
        entry_points={
                'console_scripts': [
                        'decache=easyasyncio.bin.decache:core'
                ],
        }
)
