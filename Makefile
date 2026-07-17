.PHONY: default clear dist all install
default: all ;

_state:
	make -C .dev/state

clear:
	make -C .dev/state clear
	rm -f dist/*

install:
	python3 -m pip install -r requirements.txt

dist:
	python3 src/main.py
	# generates dist/json/*.json, dist/yaml/**/*.yaml, dist/NOTICE, dist/manifest.json

all: _state dist

