# Picson.py

import json
from tkinter import *
from PIL import Image, ImageTk

screen = None
elements = {}
homeLeft = {}
homeTop = {}
names = {}
ids = {}
zlist = []
images = {}
onInit = None
onTick = None
first = True
running = True
loglevel = 0

# Create a screen
def createScreen(values = {}):
    screen = Tk()
    setScreen(screen)
    width = values['width'] if 'width' in values else 800
    height = values['height'] if 'height' in values else 480
    geometry = str(width) + 'x' + str(height)
    screen.geometry(geometry)
    screen.title('Graphic test')

    # Handle a click in the screen
    def onClick(event):
        global screenLeft, screenTop, zlist
        x = event.x
        y = event.y
        # print('Clicked at : '+ str(x) +","+ str(y))
        for i in range(1, len(zlist) + 1):
            element = zlist[-i]
            id = list(element)[0]
            values = element[id]
            x1 = values['left']
            x2 = x1 + values['width']
            y1 = values['top']
            y2 = y1 + values['height']
            if x >= x1 and x < x2 and y >= y1 and y < y2:
                if id in elements:
                    element = elements[id]
                    if 'cb' in element:
                        element['cb'](id)
                        break
                else:
                    PicsonError(None, f'Element \'{id}\' does not exist')
    screen.bind('<Button-1>', onClick)

    fill = values['fill']['content'] if 'fill' in values else 'white'
    canvas = Canvas(screen, width=width, height=height, bg=fill)
    canvas.pack()
    setCanvas(canvas)

# Set the screen
def setScreen(s):
    global screen
    screen = s

# Get the screen
def getScreen():
    global screen
    return screen

# Set up the init handler
def setOnInit(cb):
    global onInit
    onInit = cb

# Set up the tick handler
def setOnTick(cb):
    global onTick
    onTick = cb

# Set up a click handler in an element
def setOnClick(name, cb):
    global elements
    if name in elements:
        elements[name]['cb'] = cb
    else:
        PicsonError(None, f'Element \'{name}\' does not exist')
    return

# Set the canvas
def setCanvas(c):
    global canvas
    canvas = c

# Get the canvas
def getCanvas():
    global canvas
    return canvas

# Set the source of an image
def setSource(name, value):
    global images
    img=ImageTk.PhotoImage(file=value)
    id = elements[name]['id']
    images[id] = img
    canvas.itemconfig(id, image=img)

# Get the element whose name is given
def getElement(name):
    global elements
    if name in elements:
        return elements[name]
    else:
        PicsonError(None, f'Element \'{name}\' does not exist')

# Save the name of an element against its id and vice versa
def saveName(id, name):
    global names, ids
    if name in ids:
        raise PicsonError(f'Name {name} has already been used')
    names[id]= name
    ids[name] = id

# Show the screen and call onTick() every 10ms to allow other programs to run
def showScreen():
    screen = getScreen()
    def afterCB(screen):
        pass
    #     global onInit, onTick
    #     if onInit:
    #         onInit()
    #         onInit = False
    #     elif onTick:
    #         onTick()
    #     screen.after(100, lambda: afterCB(screen))
    screen.after(100, lambda: afterCB(screen))
    screen.mainloop()
    raise SystemExit

# Render a JSON graphic specification
def render(spec, parent = 'screen'):
    global elements

    # Get the value of an argument
    def getValue(args, item):
        if item in args:
            if type(item) == int:
                return item
            return args[item]
        return item

    # Render an image
    def renderImage(elementType, values, offset, args, family):
        global names, images, home, loglevel
        left = getValue(args, values['left']) if 'left' in values else 0
        top = getValue(args, values['top']) if 'top' in values else 0
        left = offset['dx'] + left
        top = offset['dy'] + top
        width = getValue(args, values['width']) if 'width' in values else 100
        height = getValue(args, values['height']) if 'height' in values else 100
        w = int(width)
        h = int(height)
        right = left + width
        bottom = top + height
        src = getValue(args, values['src']) if 'src' in values else None
        img = Image.open(src)
        img = img.resize((w,h), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(img)
        imageId = getCanvas().create_image((left), top, anchor='nw', image=img)
        if loglevel > 2:
            writeLog(f'Created image, id={imageId}, source \'{src}\'')
        images[imageId] = img
        family.append(imageId)
        # family.append(containerId)
        if 'name' in values:
            name = values['name']
            elementSpec = {
                "id": imageId,
                "type": elementType,
                "containerId": None,
                "left": left,
                "top": top,
                "width": width,
                "height": height,
                "children": []
            }
            elements[name] = elementSpec
            homeLeft[name] = left
            homeTop[name] = top
            zlist.append({name: elementSpec})
            if src == None:
                return f'No image source given for \'{id}\''
            saveName(imageId, name)
        return None

    # Render a graphic element
    def renderElement(element, offset, args, family):
        elementType = element['type']
        if elementType == 'image':
            return renderImage(elementType, element, offset, args, family)
        else:
            return f'Type must be rect/ellipse/text/image'

    # Render a complete specification
    def renderSpec(spec, offset, args):
        # If a list, iterate it
        if type(spec) is list:
            for element in spec:
                result = renderElement(element, offset, args, [])
                if result != None:
                    return result
        # Otherwise, process the single element
        else:
            return renderElement(spec, offset, args, [])

    # Main entry point
    offset = {'dx': 0, 'dy': 0}
    if parent != 'screen':
        element = getElement(parent)
        offset['dx'] = element['left']
        offset['dy'] = element['top']

   # If it'a string, process it
    if type(spec) is str:
        return renderSpec(json.loads(spec), offset, {})

# Write to the log file
def writeLog(text):
    f = open('log.txt', 'a')
    f.write(f'{text}\n')
    f.close()

#Define exceptions
class PicsonError(Exception):
    pass