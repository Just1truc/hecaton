import argparse

parser = argparse.ArgumentParser(
    prog="Hecaton Server",
    description="A server that centralise/load balance jobs across Hecaton GPUs"
)
parser.add_argument(
    "env", type=str
)
parser.add_argument(
    "port", type=str, default="8181"
)