from setuptools import setup

setup(
    name='easyasyncio',
    version='0.0.1',
    packages=[
        'easyasyncio',
        'logzero',
        'git+ssh://git@github.com/RaphaelNanje/Easy-App-Dirs.git#egg=easyappdirs'
    ],
    url='https://github.com/RaphaelNanje/easyasyncio.git',
    license='',
    author='Raphael Nanje',
    author_email='rtnanje@gmail.com',
    description='A library that makes asyncio simple'
)
