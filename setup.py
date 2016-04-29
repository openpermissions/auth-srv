
from setuptools import find_packages, setup
import auth

setup(
    name='opp auth service',
    version=auth.__version__,
    description='Open Permissions Platform Auth Service',
    author='CDE Catapult',
    author_email='support-copyrighthub@cde.catapult.org.uk',
    url='https://github.com/openpermissions/auth-srv',
    packages=find_packages(exclude=['test']),
    entry_points={
        'console_scripts':
        ['auth-srv = auth.app:main']},
    )
