.PHONY: lint lint-fix

FIX ?=

lint:
	uv run --extra dev ruff check $(if $(FIX),--fix,) .
	uv run --extra dev ruff format $(if $(FIX),,--check) .
	uv run --extra dev mypy .

lint-fix:
	$(MAKE) lint FIX=1
