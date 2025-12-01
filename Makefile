.PHONY: build clean

build:
	uv run pyinstaller main.spec

clean:
	rm -rf build/ dist/ *.spec.bak

.DEFAULT_GOAL := build
