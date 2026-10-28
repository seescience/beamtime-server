#!/usr/bin/env bash
# SPDX-License-Identifier: MIT

nohup uv run beamtime-server -q > /dev/null 2>&1 &
