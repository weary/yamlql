all: test

.PHONY: clean
clean:
	rm -rf ve ./.pytest_cache
	find . -name __pycache__ -exec rm -rf {} \;

ve/init: requirements.txt
	python3 -m venv ve
	./ve/bin/pip install -U pip
	./ve/bin/pip install -r requirements.txt
	touch ./ve/init

test: ve/init
	./ve/bin/pytest src
