.PHONY: run test

run:
	uv run bits-and-bots

test:
	uv run --group dev pytest