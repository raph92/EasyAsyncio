from setuptools import setup

setup(
        name='easyasyncio',
        version='8.0.4',
        packages=['easyasyncio'],
        url='https://github.com/RaphaelNanje/easyasyncio.git',
        license='MIT',
        author='Raphael Nanje',
        author_email='rtnanje@gmail.com',
        description='A library that makes asyncio simple',
        install_requires=[
                'aiohttp',
                'easyfilemanager',
                'asciimatics'
        ],
        dependency_links=[
                'https://github.com/RaphaelNanje/'
                'easyfilemanager.git#egg=easyfilemanager'
        ],
        python_requires='~=3.6'
)
