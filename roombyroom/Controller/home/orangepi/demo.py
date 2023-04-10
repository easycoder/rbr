#! /bin/python

import sys, json
sys.path.insert(0, 'lib')
from tkinter import *
from PIL import ImageTk
from pison import *

if __name__ == '__main__':
	def onClick(name):
		print(f'Click {name}!')
		try:
			setSource(name, 'images/down.png')
		except Exception as e:
			print(e)
	
	# def onTick():
	# 	pass

	createScreen()
	screen = getScreen()

	# Create an instance of tkinter frame
	# screen = Tk()
	# setScreen(screen)

	# Set the geometry
	# screen.geometry("800x480")

	# Create a canvas and add the image into it
	# canvas=Canvas(screen, width=800, height=480)
	# canvas.pack()
	# setCanvas(canvas)

	img1=ImageTk.PhotoImage(file="images/up.png")
	# getCanvas().create_image(100 ,100, anchor="nw", image=img1)
	element = {}
	element['name'] = 'test'
	element['type'] = 'image'
	element['left'] = 100
	element['top'] = 100
	element['width'] = 100
	element['height'] = 100
	element['src'] = 'images/up.png'
	element = json.dumps(element)
	render(element)

	setOnClick('test', lambda name:  onClick(name))
	setOnTick(lambda: onTick())
	# getScreen().mainloop()
	showScreen()

