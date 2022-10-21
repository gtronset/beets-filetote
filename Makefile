init:
	git clone --depth 1 https://github.com/beetbox/beets.git beets
	virtualenv env
	./env/bin/pip install -r requirements.txt
	./env/bin/pip install -e .
	cp -b config.yaml ~/.config/beets/

test:
	pytest tests
