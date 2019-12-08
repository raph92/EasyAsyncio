flake:
	flake8 easyasyncio tests examples setup.py

cov cover coverage:
	py.test -s -v --cov-report term --cov-report html --cov easyasyncio ./tests
	@echo "open file://`pwd`/htmlcov/index.html"

mypy:
	if ! python --version | grep -q 'Python 3\.5\.'; then \
	    mypy easyasyncio --ignore-missing-imports --no-strict-optional --strict --disallow-untyped-calls --disallow-incomplete-defs; \
	fi

mypyloop:
	while true ; do \
	mypy easyasyncio --ignore-missing-imports --no-strict-optional --strict --disallow-untyped-calls --disallow-incomplete-defs > mypyerrors ; \
	sleep 15 ; \
	done

clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -f `find . -type f -name '@*' `
	rm -f `find . -type f -name '#*#' `
	rm -f `find . -type f -name '*.orig' `
	rm -f `find . -type f -name '*.rej' `
	rm -f .coverage
	rm -rf coverage
	rm -rf build
	rm -rf htmlcov
	rm -rf dist
	rm -rf node_modules