#! /bin/python

import sys
sys.path.insert(0, 'lib')
from ec_main import Main
from ec_program import Program
from ec_core import Core
from ec_graphics import Graphics
from ec_p100 import P100

if __name__ == '__main__':
	if (len(sys.argv) > 1):
		scriptName = sys.argv[1]

		f = open(scriptName, 'r')
		source = f.read()
		f.close()

		Program(Main(), source, [Core, Graphics, P100])
