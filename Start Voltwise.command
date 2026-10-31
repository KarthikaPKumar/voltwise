#!/bin/zsh
cd -- "$(dirname -- "$0")" || exit 1
if [[ ! -x .venv/bin/python ]]; then
  print 'Please set up the Python environment using README.md first.'
  read 'reply?Press Return to close.'
  exit 1
fi
.venv/bin/python scripts/start_local.py
