# Picson.py

import json
import tkinter as tk
from tkinter import *
from PIL import Image, ImageTk

elements = {}
homeLeft = {}
homeTop = {}
names = {}
ids = {}
zlist = []
images = {}
onTick = None
first = True
running = True

# Set the canvas
def setCanvas(c):
    global canvas
    canvas = c

# Get the canvas
def getCanvas():
    global canvas
    return canvas

# Create a screen
def createScreen(values):
    global screen, canvas, screenLeft, screenTop, loglevel
    screen = tk.Tk()
    screen.title('RBR Simulator')
    if values['fullscreen']:
        width = screen.winfo_screenwidth()
        height = screen.winfo_screenheight()
        screen.attributes('-fullscreen', True)
    else:
        width = values['width']['content'] if 'width' in values else 800
        height = values['height']['content'] if 'height' in values else 480
        screenLeft = int((screen.winfo_screenwidth() - width) / 2)
        screenTop = int((screen.winfo_screenheight() - height) / 2)
        if 'left' in values:
            screenLeft = values['left']['content']
        if 'top' in values:
            screenTop = values['top']['content']

        geometry = str(width) + 'x' + str(height) + '+' + str(screenLeft) + '+' + str(screenTop)
        screen.geometry(geometry)
    loglevel = int(values['loglevel'])
    file = open('log.txt', 'w')
    file.close()

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
    canvas = tk.Canvas(master=screen, width=width, height=height, bg=fill)
    canvas.place(x=0, y=0)
    setCanvas(canvas)

# Close the screen
def closeScreen():
    global screen
    screen.destroy()

# Get the screen width
def getScreenWidth():
    global screen
    return screen.winfo_screenwidth()

# Get the screen height
def getScreenHeight():
    global screen
    return screen.winfo_screenheight()

# Set up a click handler in an element
def setOnClick(id, cb):
    global elements
    if id in elements:
        elements[id]['cb'] = cb
    else:
        PicsonError(None, f'Element \'{id}\' does not exist')
    return

# Set up the init handler
def setOnInit(cb):
    global onInit
    onInit = cb

# Set up the tick handler
def setOnTick(cb):
    global onTick
    onTick = cb

# Show the screen and call onTick() every 10ms to allow other programs to run
def showScreen():
    global screen, onTick
    def afterCB(screen):
        global first
        if first:
            onInit()
            first = False
        elif onTick:
            onTick()
        screen.after(100, lambda: afterCB(screen))
    screen.after(100, lambda: afterCB(screen))
    screen.mainloop()
    raise SystemExit

# Hide the cursor
def hideCursor():
    screen.config(cursor="none")

# Render a JSON graphic specification
def render(spec, parent):
    global elements

    # Get the value of an argument
    def getValue(args, item):
        if item in args:
            if type(item) == int:
                return item
            return args[item]
        return item

    # Render a rectangle or ellipse
    def renderIntoRectangle(elementType, values, offset, args, family):
        global zlist, names
        left = getValue(args, values['left']) if 'left' in values else 0
        top = getValue(args, values['top']) if 'top' in values else 0
        left = offset['dx'] + left
        top = offset['dy'] + top
        width = getValue(args, values['width']) if 'width' in values else 100
        height = getValue(args, values['height']) if 'height' in values else 100
        right = left + width
        bottom = top + height
        fill = values['fill'] if 'fill' in values else None
        outline = values['outline'] if 'outline' in values else None
        if outline != None:
            outlineWidth = getValue(args, values['outlineWidth']) if 'outlineWidth' in values else 1
        else:
            outlineWidth = 0
        if elementType == 'rect':
            elementId = getCanvas().create_rectangle(left, top, right, bottom, fill=fill, outline=outline, width=outlineWidth)
            if loglevel > 2:
                writeLog(f'Created rectangle, id={elementId}')
        elif elementType == 'ellipse':
            elementId = getCanvas().create_oval(left, top, right, bottom, fill=fill, outline=outline, width=outlineWidth)
            if loglevel > 2:
                writeLog(f'Created ellipse, id={elementId}')
        else:
            return f'Unknown element type \'{elementType}\''
        family.append(elementId)

        children = []
        if '#' in values:
            for item in values['#']:
                result = renderElement(item, {'dx': left, 'dy': top}, args, children)
                if result != None:
                    writeLog(f'Error: {result}')
        for child in children:
            family.append(child)

        if 'name' in values:
            name = getValue(args, values['name'])
            elementSpec = {
                "id": elementId,
                "children": children,
                "type": elementType,
                "containerId": None,
                "left": left,
                "top": top,
                "width": width,
                "height": height
            }
            elements[name] = elementSpec
            homeLeft[name] = left
            homeTop[name] = top
            zlist.append({name: elementSpec})
            saveName(elementId, name)
        return None

    # Render text into a rectangle or ellipse
    def renderText(elementType, values, offset, args, family):
        global names
        left = getValue(args, values['left']) if 'left' in values else 0
        top = getValue(args, values['top']) if 'top' in values else 0
        left = offset['dx'] + left
        top = offset['dy'] + top
        width = getValue(args, values['width']) if 'width' in values else 100
        height = getValue(args, values['height']) if 'height' in values else 100
        right = left + width
        bottom = top + height
        shape = getValue(args, values['shape']) if 'shape' in values else 'rectangle'
        fill = getValue(args, values['fill']) if 'fill' in values else None
        outline = getValue(args, values['outline']) if 'outline' in values else None
        outlineWidth = getValue(args, values['outlineWidth']) if 'outlineWidth' in values else 0 if outline == None else 1
        color = getValue(args, values['color']) if 'color' in values else None
        text = getValue(args, values['text']) if 'text' in values else ''
        fontFace = getValue(args, values['fontFace']) if 'fontFace' in values else 'Helvetica'
        fontWeight = getValue(args, values['fontWeight']) if 'fontWeight' in values else 'normal'
        fontSize = round(height*2/5) if shape == 'ellipse' else round(height*3/5)
        scale = float(getValue(args, values['scale'])) if 'scale' in values else 1.0
        fontSize = round(fontSize * scale)
        fontTop = top + height/2
        if 'fontSize' in values:
            fontSize = getValue(args, values['fontSize'])
            fontTop = top + round(fontSize * 5 / 4)
        adjust = round(fontSize/5) if shape == 'ellipse' else 0
        align = getValue(args, values['align']) if 'align' in values else 'center'
        if align == 'left':
            xoff = round(fontSize/5)
            anchor = 'w'
        elif align == 'right':
            xoff = width - round(fontSize/5)
            anchor = 'e'
        else:
            xoff = width/2
            anchor = 'center'
        if xoff < 3:
            xoff = 3
        if shape == 'ellipse':
            containerId = getCanvas().create_oval(left, top, right, bottom, fill=fill, outline=outline, width=outlineWidth)
            if loglevel > 2:
                writeLog(f'Created ellipse text container, id={containerId}')
        else:
            containerId = getCanvas().create_rectangle(left, top, right, bottom, fill=fill, outline=outline, width=outlineWidth)
            if loglevel > 2:
                writeLog(f'Created rectangle text container, id={containerId}')
        textId = canvas.create_text(left + xoff, fontTop + adjust, fill=color, font=f'"{fontFace}" {fontSize} {fontWeight}', text=text, anchor=anchor)
        if loglevel > 2:
            writeLog(f'Created text, id={textId}, content \'{text}\'')
        family.append(textId)
        family.append(containerId)

        if 'name' in values:
            name = getValue(args, values['name'])
            elementSpec = {
                "id": textId,
                "type": elementType,
                "containerId": containerId,
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
            saveName(textId, name)
        return None

    # Render an image
    def renderImage(elementType, values, offset, args, family):
        global names, images, home
        left = getValue(args, values['left']) if 'left' in values else 0
        top = getValue(args, values['top']) if 'top' in values else 0
        left = offset['dx'] + left
        top = offset['dy'] + top
        width = getValue(args, values['width']) if 'width' in values else 100
        height = getValue(args, values['height']) if 'height' in values else 100
        right = left + width
        bottom = top + height
        src = getValue(args, values['src']) if 'src' in values else None
        containerId = getCanvas().create_rectangle(left, top, right, bottom, width=0)
        img = (Image.open(src))
        resized_image= img.resize((int(width), int(height)), Image.ANTIALIAS)
        new_image= ImageTk.PhotoImage(resized_image)
        imageId = getCanvas().create_image(left, top, anchor='nw', image=new_image)
        if loglevel > 2:
            writeLog(f'Created image, id={imageId}, source \'{src}\'')
        images[containerId] = {'id': imageId, "image": new_image}
        family.append(imageId)
        family.append(containerId)
        if 'name' in values:
            name = values['name']
            elementSpec = {
                "id": imageId,
                "type": elementType,
                "containerId": containerId,
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
        if elementType in ['rect', 'ellipse']:
            return renderIntoRectangle(elementType, element, offset, args, family)
        elif elementType == 'text':
            return renderText(elementType, element, offset, args, family)
        elif elementType == 'image':
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

    # If it's a 'dict', extract the spec and the args
    if type(spec) is dict:
        args = spec['args']
        return renderSpec(json.loads(spec['spec']), offset, args)

# Clear the screen
def clearScreen():
    global left
    canvas = getCanvas()
    for element in zlist:
        values = element.values()
        for value in values:
            id = value['id']
            containerId = value['containerId']
            canvas.delete(id)
            if containerId != None:
                canvas.delete(containerId)
    left = {}
    return

# Hide an element
def hideElement(name):
    global elements
    element = elements[name]
    getCanvas().moveto(element['id'], screen.winfo_screenwidth(), 0)
    return

# Show an element
def showElement(name):
    global elements, homeLeft, homeTop
    left = homeLeft[name]
    top = homeTop[name]
    element = elements[name]
    getCanvas().moveto(element['id'], left, top)
    return

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

# Get an attribute of an element
def getAttribute(name, attribute):
    element = getElement(name)
    return getCanvas().itemcget(element['id'], attribute)

# Set the content of a text element
def setText(name, value):
    getCanvas().itemconfig(getElement(name)['id'], text=value)

# Set the font of a text element
def setFont(name, value):
    getCanvas().itemconfig(getElement(name)['id'], font=value)

# Set the fill of a rectangle, ellipse or text
def setFill(name, value):
    id = getElement(name)['id']
    getCanvas().itemconfig(getElement(name)['id'], fill=value)

# Set the source of an image
def setSource(name, value):
    raise PicsonError('Changing image not yet implemented')

# Dispose of an element and all its children (recursively)
def dispose(name):
    global names
    element = getElement(name)
    for child in element['children']:
        if child in names:
            dispose(names[child])
    if element['containerId']:
        getCanvas().delete(element['containerId'])
    getCanvas().delete(element['id'])

# A test function for the "gtest" script command
def gtest(name):
    element = getElement(name)
    print(getCanvas().itemcget(element['id'], 'font'))
    newfont = '"Helvetica" 40 normal'
    getCanvas().itemconfig(element['id'], font=newfont)

# Write to the log file
def writeLog(text):
    f = open('log.txt', 'a')
    f.write(f'{text}\n')
    f.close()

#Define exceptions
class PicsonError(Exception):
    pass
