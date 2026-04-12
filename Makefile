install_ci:
	uv sync
	uv run pre-commit install

install_dev:
	make install_ci
	uv run invoke --list

install_uv:
	pip install uv
	pip install --upgrade pip
