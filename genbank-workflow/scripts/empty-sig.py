#! /usr/bin/env python

import argparse
import sourmash.save_load

p = argparse.ArgumentParser()

p.add_argument('output', nargs='?')

args = p.parse_args()

with sourmash.save_load.SaveSignaturesToLocation(args.output) as ss:
   pass
