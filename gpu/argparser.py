import argparse

parser = argparse.ArgumentParser(
    prog="Hecaton GPU",
    description="A client to start an instance of a hecaton GPU cluster"
)
parser.add_argument(
    "ip", type=str, default="0.0.0.0:8181"
)