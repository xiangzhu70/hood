#!/usr/bin/env python3

# The logic about initial config setup, and run-time state
# Could be in a database.  Use the file system for now

import os
from configobj import ConfigObj


class DiagState:

    def __init__(self, config_file, state_file_path="/tmp/diag_state") -> None:

        if config_file:
            config = ConfigObj(config_file)
            print(f"{config['top.key1']}")
