#! /bin/python

import sys
sys.path.insert(0, 'lib')
from ec_main import Main
from ec_program import Program
from ec_core import Core

if __name__ == '__main__':
	f = open('benchmark.ecs', 'r')
	source = f.read()
	f.close()
	Program(Main(), source, [Core])
