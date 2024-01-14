set -ex

rye run black src
rye run black tests
rye run ruff src --fix
rye run ruff tests --fix
