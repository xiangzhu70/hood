#!/usr/bin/env python3

import os
import re
import tempfile
import subprocess
import shlex

from pdb import set_trace as stop


def group_str_parse(group_str):
    type_name = None
    range_str = None
    inst = None

    # type_name is before the first '['
    m = re.match(r"(?P<type_name>[^\[]+)\[(?P<range_str>\S+)\]$", group_str)
    if not m:
        m = re.match(r"(?P<type_name>\S+)(?P<inst>\d+)$", group_str)
        if m:
            # example: pim1
            type_name = m.group("type_name")
            inst = m.group("inst")
        else:
            type_name = group_str
    else:
        # range formats
        type_name = m.group("type_name")
        range_str = m.group("range_str")
        # Enter the group, not the instance.  In show_tree case.
        # example: pim[1..8]
        m = re.match(r"(?P<idx_start>\d+)\.\.(?P<idx_end>\d+)$", range_str)
        if m:
            # idx_start = int(m.group("idx_start"))
            # idx_end = int(m.group("idx_end"))
            # this range_str is ok, do nothing
            pass
    return (type_name, range_str, inst)


def parse_key_val_pairs(args=None):
    if not args:
        return {}
    args_dict = {}
    for pair in args:
        m = re.match(r"(?P<key>\S+)=(?P<val>\S+)", pair)
        if not m:
            print(f"parse_args: ignore {pair}")
            continue
        args_dict[m.group("key")] = m.group("val")
    return args_dict


def gen_graphviz(lines):
    with tempfile.NamedTemporaryFile(mode="w+") as fp:
        for line in lines:
            fp.write(line + "\n")
        fp.flush()
        # print(f"The tmp file is {fp.name}")
        stream = os.popen(f"pastry < {fp.name}")
        output = stream.read()
        m = re.match(r"(?P<paste_id>^P\d+): .*", output)
        if not m:
            raise Exception("invaild pastry output")
        paste_id = m.group("paste_id")
        print("graphviz is at")
        print(f"https://www.internalfb.com/intern/graphviz/?paste={paste_id}")


class InstanceEnumerator:
    def __init__(self, inst):
        print("enu init")
        self.inst = inst
        self.idx = 0
        self.group_mode_once_done = False

    def __next__(self):
        if self.inst.group_mode:
            if not self.group_mode_once_done:
                self.group_mode_once_done = True
                return self.inst.group_str
            else:
                raise StopIteration
        if self.idx <= self.idx_end:
            ret = f"{self.type_name}{self.idx}"
            self.idx += 1
            return ret
        raise StopIteration


class Instances:
    def __init__(self, type_name, range_str, context=None):
        self.type_name = type_name
        self.range_str = range_str
        # Example pim[1..8]
        m = re.match(r"(?P<idx_start>\d+)\.\.(?P<idx_end>\d+)$", range_str)
        if not m:
            raise Exception("Invalid range str")
        self.idx_start = m.group("idx_start")
        self.idx_end = m.group("idx_end")

    def __iter__(self):
        return InstanceEnumerator(self)


class NameStyle:
    @staticmethod
    def underscore_to_camel(underscore_str):
        parts = underscore_str.split("_")
        camel = ""
        for part in parts:
            camel += part[0].upper() + part[1:]
        return camel

    @staticmethod
    def camel_to_underscore(camel_str):
        # stop()
        underscore_str = re.sub(r"(?!^)([A-Z]+)", r"_\1", camel_str).lower()
        return underscore_str


class ShellCommand:
    def __init__(self, logger):
        self.logger = logger

    def run_cmd(self, cmd, shell=False, realtime=False, timeout=1):
        self.logger.info(f"== run_cmd [{cmd}]")
        if realtime:
            return self._run_cmd_realtime(cmd, shell=shell, timeout=timeout)

        try:
            cmpl = subprocess.run(shlex.split(cmd),
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=timeout, shell=shell)
            output = cmpl.stdout.decode().strip()
        except Exception as e:
            output = str(e)

        self.logger.info("-- output: ")
        self.logger.info(output)
        self.logger.info("-- output end")

        return output

    def _run_cmd_realtime(self, cmd, shell=False, timeout=100):
        if not shell:
            cmd_param = shlex.split(cmd)
        else:
            cmd_param = cmd
            # if shell==True, use the raw cmd as the calling param
        try:
            cmpl = subprocess.run(cmd_param,
                                  # stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=timeout, shell=shell)
            stdout = cmpl.stdout
            if isinstance(stdout, bytes):
                output = stdout.decode().strip()
            elif not output:
                output = "None"
            else:
                output = stdout
        except Exception as e:
            output = str(e)
        return output
