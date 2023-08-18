#! /bin/python

from ec_program import Program
from ec_core import Core
from ec_graphics import Graphics

class EasyCoder:

	def __init__(self):
		self.version = 1

	f = open('gui.ecs', 'r')
	source = f.read()
	f.close()

	Program(source, [Core, Graphics])

if __name__ == '__main__':
    EasyCoder()
