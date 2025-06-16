#!/bin/bash
set -e
python3 -m pip install -q pytest
python3 -m pip install -q -r server/liquidsoap/requirements.txt
pytest -q
