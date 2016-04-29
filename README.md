The Open Permissions Platform Authentication Service
====================================================

This repository contains an Open Permissions Platform Coalition Authentication application which take care
of service use authentication.

Running locally
===============
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
==========================================
To have a "clean" target from build artifacts:

```
make clean
```

To install requirements. By default prod requirement is used:

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
