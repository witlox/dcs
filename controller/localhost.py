import argparse
from ilm.api import api as ilm
from wjc.api import api as wjc

parser = argparse.ArgumentParser(description='run ilm or wjc locally.')

# Compulsory arguments
run_mode_group = parser.add_mutually_exclusive_group(required=True)
run_mode_group.add_argument("-i", "--ilm",
                            help="Launch ilm",
                            dest="run_mode",
                            action="store_const",
                            const="ilm")
run_mode_group.add_argument("-w", "--wjc",
                            help="Launch wjc",
                            dest="run_mode",
                            action="store_const",
                            const="jwc")

# Start parsing
args = parser.parse_args()

if args.__dict__["run_mode"] == "ilm":
    ilm.run(port=6000, debug=True)

if args.__dict__["run_mode"] == "wjc":
    wjc.run(port=7000, debug=True)
