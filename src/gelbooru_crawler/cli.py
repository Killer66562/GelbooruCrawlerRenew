import argparse


parser = argparse.ArgumentParser(
    prog="crawler", 
    usage="crawler <action> ..."
)

parser.add_argument("action", type=str)
parser.add_argument("tags")