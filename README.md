The Open Permissions Platform Auth Service
==========================================

Useful Links
============
* [Open Permissions Platform](http://openpermissions.org)
* [Low level Design](https://github.com/openpermissions/auth-srv/blob/master/documents/markdown/low-level-design.md)
* [API Documentation](https://github.com/openpermissions/auth-srv/blob/master/documents/apiary/api.md)
* [How to authenticate with Open Permissions Platform services](https://github.com/openpermissions/auth-srv/blob/master/documents/markdown/how-to-auth.md)

Service Overview
================
This repository contains an Open Permissions Platform Auth application which is responsible for authenticating client access.

Running locally
---------------
To run the service locally:

```
pip install -r requirements/dev.txt
python setup.py develop
python auth/
```

To show a list of available CLI parameters:

```
python auth/ -h [--help]
```

To start the service using test.service.conf:

```
python auth/ -t [--test]
```

Running tests and generating code coverage
------------------------------------------
To have a "clean" target from build artifacts:

```
make clean
```

To install requirements. By default, prod requirement is used:

```
make requirements [REQUIREMENT=test|dev|prod]
```

To run all unit tests and generate a HTML code coverage report along with a
JUnit XML report in tests/unit/reports:

```
make test
```

To run pyLint and generate a HTML report in tests/unit/reports:

```
make pylint
```

To run create the documentation for the service in _build:

```
make docs
```
