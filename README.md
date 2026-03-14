# epub-compiler


## Instalation

# Install uv if you haven't (one-time)
# curl -LsSf https://astral.sh/uv/install.sh | sh    # or via brew, pipx, etc.

# Create virtual env + install dependencies from pyproject.toml
uv sync

# Or if you add dev group later:
uv add --group dev ruff
uv sync

# Run your script in the project venv
uv run python txt2epub.py ./my-book-folder

# Or install as editable CLI tool
uv pip install -e .
txt2epub ./my-book-folder    # now available globally in the venv
