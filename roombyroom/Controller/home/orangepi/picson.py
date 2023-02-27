# Picson.py

import sys, json
import tkinter as tk
from PIL import Image, ImageTk

elements = {}
homeLeft = {}
homeTop = {}
zlist = []
images = {}
onTick = None

# Get the canvas
def setCanvas(c):
    global canvas
    canvas = c

# Get the canvas
def getCanvas():
    global canvas
    return canvas

def createScreen(values):
    global screen, canvas, screenLeft, screenTop, running, loglevel
    running = True
    screen = tk.Tk()
    screen.title('RBR Simulator')
    if values['fullscreen']:
        width = screen.winfo_screenwidth()
        height = screen.winfo_screenheight()
        screen.attributes('-fullscreen', True)
    else:
        # screen.overrideredirect(True)
        width = values['width']['content'] if 'width' in values else 800
        height = values['height']['content'] if 'height' in values else 460
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
                        element['cb']()
                        break
                else:
                    RuntimeError(None, f'Element \'{id}\' does not exist')

    screen.bind('<Button-1>', onClick)

    fill = values['fill']['content'] if 'fill' in values else 'white'
    canvas = tk.Canvas(master=screen, width=width, height=height, bg=fill)
    canvas.place(x=0, y=0)
    setCanvas(canvas)

# Close the screen
def closeScreen():
    global screen
    screen.destroy()

# Set up a click handler in an element
def setOnClick(id, cb):
    global elements
    if id in elements:
        elements[id]['cb'] = cb
    else:
        RuntimeError(None, f'Element \'{id}\' does not exist')
    return

# Set up the tick handler
def setOnTick(cb):
    global onTick
    onTick = cb

# Show the screen and check every second if it's still running
def showScreen():
    global screen, onTick
    def afterCB(screen):
        if onTick != None:
            onTick()
        screen.after(100, lambda: afterCB(screen))
    screen.after(1000, lambda: afterCB(screen))
    screen.config(cursor="none")
    screen.mainloop()
    sys.exit()

# Render a graphic specification
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
    def renderIntoRectangle(elementType, values, offset, args):
        global zlist
        left = getValue(args, values['left']) if 'left' in values else 10
        top = getValue(args, values['top']) if 'top' in values else 10
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

        if 'name' in values:
            name = getValue(args, values['name'])
            elementSpec = {
                "id": elementId,
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

        if '#' in values:
            for item in values['#']:
                result = renderWidget(item, {'dx': left, 'dy': top}, args)
                if result != None:
                    writeLog(f'Error: {result}')

        return None

    # Render text into a rectangle or ellipse
    def renderText(values, offset, args):
        left = getValue(args, values['left']) if 'left' in values else 10
        top = getValue(args, values['top']) if 'top' in values else 10
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
        scale = getValue(args, values['scale']) if 'scale' in values else 1.0
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

        if 'name' in values:
            name = getValue(args, values['name'])
            elementSpec = {
                "id": textId,
                "containerId": containerId,
                "left": left,
                "top": top,
                "width": width,
                "height": height
            }
            elements[name] = elementSpec
            homeLeft[name] = left
            homeTop[name] = top
            zlist.append({name: elementSpec})
        return None

    # Render an image
    def renderImage(values, offset, args):
        global images, home
        left = getValue(args, values['left']) if 'left' in values else 10
        top = getValue(args, values['top']) if 'top' in values else 10
        left = offset['dx'] + left
        top = offset['dy'] + top
        width = getValue(args, values['width']) if 'width' in values else 100
        height = getValue(args, values['height']) if 'height' in values else 100
        right = left + width
        bottom = top + height
        src = getValue(args, values['src']) if 'src' in values else None
        containerId = getCanvas().create_rectangle(left, top, right, bottom, width=0)
        img = (Image.open(src))
        resized_image= img.resize((width, height), Image.ANTIALIAS)
        new_image= ImageTk.PhotoImage(resized_image)
        imageId = getCanvas().create_image(left, top, anchor='nw', image=new_image)
        if loglevel > 2:
            writeLog(f'Created image, id={imageId}, source \'{src}\'')
        images[containerId] = {'id': imageId, "image": new_image}
        if 'name' in values:
            name = values['name']
            elementSpec = {
                "id": imageId,
                "containerId": containerId,
                "left": left,
                "top": top,
                "width": width,
                "height": height
            }
            elements[name] = elementSpec
            homeLeft[name] = left
            homeTop[name] = top
            zlist.append({name: elementSpec})
            if src == None:
                return f'No image source given for \'{id}\''
        return None

    # Create a canvas or render an element
    def renderWidget(element, offset, args):
        elementType = element['type']
        if elementType in ['rect', 'ellipse']:
            return renderIntoRectangle(elementType,element, offset, args)
        elif elementType == 'text':
            return renderText(element, offset, args)
        elif elementType == 'image':
            return renderImage(element, offset, args)

    # Render a complete specification
    def renderSpec(spec, offset, args):
        # If a list, iterate it
        if type(spec) is list:
            for element in spec:
                result = renderWidget(element, offset, args)
                if result != None:
                    return result
        # Otherwise, process the single element
        else:
            return renderWidget(spec, offset, args)

    # Main entry point
    offset = {'dx': 0, 'dy': 0}
    if parent != 'screen':
        writeLog('Can\'t yet render into an existing element')
        RuntimeError(None, 'Can\'t yet render into an existing element')

    # If it'a string, process it
    if type(spec) is str:
        return renderSpec(json.loads(spec), offset, {})

    # If it's a 'dict', extract the spec and the args
    if type(spec) is dict:
        args = spec['args']
        spec = json.loads(spec['spec'])
        return renderSpec(spec, offset, args)

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
        RuntimeError(None, f'Element \'{name}\' does not exist')

# Set the content of a text element
def setText(name, value):
    getCanvas().itemconfig(getElement(name)['id'], text=value)

# Set the background of a rectangle or ellipse element
def setBackground(name, value):
    id = getElement(name)['id']
    getCanvas().itemconfig(getElement(name)['id'], fill=value)

# Write to the log file
def writeLog(text):
    f = open('log.txt', 'a')
    f.write(f'{text}\n')
    f.close()

#Define exceptions
class PicsonError(Exception):
    def __init__(self, message="Undefined Picson error"):
        self.message = message
        super().__init__(self.message)
