#!/usr/bin/env python3

from flask import Flask, make_response, jsonify, request, send_from_directory, json
import os
from pdb import set_trace as stop

import threading

import argparse
import re
import os

from hood.diag_session import Session

hood_version = "0.0.0"

# flask app is global, following the flask example.

lock = threading.Lock()

flask_app = Flask(__name__)

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
node_path = os.path.abspath(os.path.expanduser(args.node_file_path))

cwd = os.getcwd()

session = Session(args.node_file_path,
                  verbose=args.verbose)


# the web command count
session.cmd_count = 0

# hood changes the cwd.  change it back to allow flask to run
os.chdir(cwd)
app = Flask(__name__)


@app.route("/")
def base():
    print("route /")
    return send_from_directory(frontend_path, "index.html")


# route("/<path:path>") is needed for all the static files (compiled JS/CSS, etc.)
@app.route("/<path:path>")
def home(path):
    print(f"route home, path=<{path}>")
    ret = send_from_directory(frontend_path, path)
    print(f"ret = {ret}")
    return ret

    node_tree = """
    {
		label: 'USA',
		children: [
			{
				label: 'Florida',
				children: [
					{ label: 'Jacksonville' },
					{
						label: 'Orlando',
						children: [
							{ label: 'Disney World' },
							{ label: 'Universal Studio' },
							{ label: 'Sea World' }
						]
					},
					{ label: 'Miami' }
				]
			},
			{
				label: 'California',
				children: [{ label: 'San Francisco' }, { label: 'Los Angeles' }, { label: 'Sacramento' }]
			}
		]
	};
    """


@app.route("/cmd", methods=["GET", "POST"])
def cli_cmd():

    print(f"route cmd <{request.data}>")
    ret_json = {
        "label": f"default label, not filled by the cmd",
        "children": []}

    try:
        print(request)
        data_str = request.data.decode('utf-8')
        data = json.loads(data_str)
        cmd_str = data["cmd"]
        print(f"cmd_str = <{cmd_str}>")
        output_dict = {"cmd": cmd_str}
        if cmd_str:
            lock.acquire()  # ugly lock, will clean up later. TBD
            session.cmd_count += 1
            f.write(f"== cmd {session.cmd_count}: {cmd_str}\n")

            words = cmd_str.split()
            tree = "-t" in words
            output_dict = session.cli_cmd(words[0], words[1:], tree=tree)
            lock.release()
            print(f"cmd output_dict {output_dict}")
        ret_json = jsonify(output_dict)
        print(f"ret_json: {ret_json}")
        f.write(f"--ret_json: {ret_json}\n")
        f.flush()

    except Exception as e:
        print(e)
    response = make_response(ret_json)
    response.headers["Content-Type"] = "application/json"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.status_code = 200

    return ret_json


if __name__ == "__main__":

    app.run(debug=True,
            host="0.0.0.0",
            port=5001,
            # ssl_context=('/home/xiang/cert/server.crt',
            # '/home/xiang/cert/server.key')
            )
