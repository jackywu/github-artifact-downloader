.PHONY: build clean install

build:
	uv run --all-groups -m PyInstaller -y main.spec

install:
	mkdir -p ~/.local/bin
	cp ./dist/github-artifact-downloader ~/.local/bin/
	chmod +x ~/.local/bin/github-artifact-downloader
	@echo "✅ Installed to ~/.local/bin/github-artifact-downloader"

clean:
	rm -rf build/ dist/ *.spec.bak

.DEFAULT_GOAL := build
