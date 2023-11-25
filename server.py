#!/usr/bin/env python3

from flask import Flask, make_response, jsonify, request, send_from_directory, json
from flask_socketio import SocketIO, emit
import os
from pdb import set_trace as stop

import threading
import logging

import argparse
import re
import os

from hood.diag_cli import CmdShell

hood_version = "0.0.0"

lock = threading.Lock()

log_file = "/tmp/hood_server.log"
f = open(log_file, "w")
if not f:
    raise Exception("Failed to open the log file")

parser = argparse.ArgumentParser(
    description=f"Hood web server.  Version {hood_version}",
    formatter_class=argparse.RawTextHelpFormatter,
)

parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("front_path", help="front end path")
parser.add_argument("node_file_path", help="node file path")

args = parser.parse_args()

frontend_path = os.path.abspath(os.path.expanduser(args.front_path))
node_file_path = os.path.abspath(os.path.expanduser(args.node_file_path))

cwd = os.getcwd()

# Starts the diag cmd shell.
cmd_shell = CmdShell(node_file_path,
    node_args = None,
    conf_file = None,
    state_file_path = None,
    verbose = False,
    flag_output_json = True,
    console_show = False)

# the web command count
cmd_shell.cmd_count = 0

# hood changes the cwd.  change it back to allow flask to run
os.chdir(cwd)

app = Flask(__name__)
socketio = SocketIO(app)

class SocketIOHandler(logging.Handler):
    def emit(self, record):
        socketio.emit("cmd_run_log", record.getMessage())
socketio_log_handler = SocketIOHandler()
cmd_shell.session.logger.addHandler(socketio_log_handler)


@app.route("/")
def base():
    print("route /")
    return send_from_directory(frontend_path, "index.html")


# route("/<path:path>") is needed for all the static files (compiled JS/CSS, etc.)
@app.route("/<path:path>")
def home(path):
    print(f"== flask route path: <{path}>")
    return send_from_directory(frontend_path, path)


@app.route("/cmd", methods=["GET", "POST"])
def cli_cmd():

    lock.acquire()  # ugly lock, will clean up later. TBD
    ret_json = {}
    try:

        data_str = request.data.decode('utf-8')
        data = json.loads(data_str)
        request_cmd_str = data["cmd"]
        
        output_dict = {}
        m = re.match(
            r"^((?P<obj_path>\S+)\s+)?cmd\s+(?P<cmd_str>.*)$", request_cmd_str)
        if m:
            obj_path = m.group("obj_path")
            cmd_str = m.group("cmd_str")

            cmd_shell.cmd_count += 1
            log_str = f"== [cmd {cmd_shell.cmd_count}] {obj_path} {cmd_str}"
            print(log_str)
            socketio.emit("server_log", log_str)
            f.write(f"{log_str}\n")
            if obj_path:
                cmd_shell.onecmd("cd " + obj_path)
            cmd_shell.onecmd("cmd " + cmd_str)
            output_dict = cmd_shell.output_dict

            f.write(f"-- cmd output_dict {output_dict}\n")
        else:
            print(f"Parsing failed.  request_cmd_str = <{request_cmd_str}>")

        ret_json = jsonify(output_dict)

        f.flush()

    except Exception as e:
        print(e)
    response = make_response(ret_json)
    response.headers["Content-Type"] = "application/json"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.status_code = 200
    lock.release()

    return ret_json


if __name__ == "__main__":

    socketio.run(app,
        debug=False,
        host='0.0.0.0',
        port=5001,
        # ssl_context=('/home/xiang/cert/server.crt',
        #   '/home/xiang/cert/server.key')
        )
