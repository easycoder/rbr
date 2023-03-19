#! /bin/python

import sys, json
sys.path.insert(0, 'lib')
from picson import *

if __name__ == '__main__':
	def onClick(name):
		print(f'Click {name}!')
		setSource(name, 'images/down.png')

	element = {}
	element['name'] = 'test'
	element['type'] = 'image'
	element['left'] = 100
	element['top'] = 100
	element['width'] = 100
	element['height'] = 100
	element['src'] = 'images/up.png'
	createScreen({})
	render(json.dumps(element))
	setOnClick('test', lambda name:  onClick(name))
	showScreen()

