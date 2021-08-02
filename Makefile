clean:
	@rm -rf build dist .eggs *.egg-info
	@rm -rf .benchmarks .coverage coverage.xml htmlcov report.xml .tox
	@find . -type d -name '.mypy_cache' -exec rm -rf {} +
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type d -name '*pytest_cache*' -exec rm -rf {} +
	@find . -type f -name "*.py[co]" -exec rm -rf {} +

# install all dependencies
setup:
	@poetry install -v

format: clean
	@poetry run black perfsizesagemaker/ tests/

type:
	@poetry run mypy --strict .

# test your application (tests in the tests/ directory)
test:
	@poetry run pytest -q --cov=perfsizesagemaker --cov-report=term-missing --cov-report=xml --cov-config=.coveragerc tests/

build:
	@poetry build

publish:
	@poetry publish
