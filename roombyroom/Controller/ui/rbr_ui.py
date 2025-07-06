from easycoder import Handler, FatalError, RuntimeError
from qwerty import TextReceiver
from widgets import (
    RBRWindow,
    Room,
    Menu,
    Keyboard,
    ModeDialog
)

# This is the package that handles the RBR user interface.

class RBR_UI(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'rbr_ui'

    def clearWidget(self, widget):
        layout = widget.layout()
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                child_widget = item.widget()
                if child_widget is not None:
                    child_widget.setParent(None)
                    child_widget.deleteLater()
                else:
                    # If it's a layout, clear it recursively
                    child_layout = item.layout()
                    if child_layout is not None:
                        self.clearWidget(child_layout)

    #############################################################################
    # Keyword handlers

    # add {room} to {rbrwin}
    def k_add(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            keyword = record['keyword']
            if keyword == 'room':
                command['room'] = record['name']
                self.skip('to')
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    keyword = record['keyword']
                    if keyword == 'rbrwin':
                        command['window'] = record['name']
                        self.add(command)
                        return True

        return False
        
    def r_add(self, command):
        if 'room' in command:
            record = self.getVariable(command['room'])
            room = record['value'][record['index']]
            window = self.getVariable(command['window'])['window']
            window.rooms.addWidget(room)
        return self.nextPC()

    # attach {element} [to element] {name} of {rbrwin}/{widget}
    def k_attach(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['keyword'] in ['element', 'button']:
                command['target'] = record['name']
                self.skip('to')
                self.skip('element')
                command['value'] = self.nextValue()
                self.skip('of')
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    if record['keyword'] in ['rbrwin', 'element', 'room']:
                        command['item'] = record['name']
                        self.add(command)
                        return True
        return False
    
    def r_attach(self, command):
        target = self.getVariable(command['target'])
        value = self.getRuntimeValue(command['value'])
        item = self.getVariable(command['item'])
        keyword = item['keyword']
        if keyword == 'rbrwin':
            window = item['window']
            target['widget'] = window.getElement(value)
        elif keyword == 'element':
            target['widget'] = item['widget'].getElement(value)
        elif keyword == 'room':
            if value == 'mode':
                target['widget'] = item['value'][item['index']].modeButton
            elif value == 'tools':
                target['widget'] = item['value'][item['index']].toolsButton
        return self.nextPC()

    def k_button(self, command):
        return self.compileVariable(command)

    def r_button(self, command):
        return self.nextPC()

    # clear {rbrwin}
    def k_clear(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['keyword']== 'rbrwin':
                command['name'] = record['name']
                self.add(command)
            return True
        return False
    
    def r_clear(self, command):
        record = self.getVariable(command['name'])
        window = record['window']
        self.clearWidget(window.content)
        window.initContent()
        return self.nextPC()

    # create {rbrwin} at {left} {top} size {width} {height}
    # create {room} {name} {mode} {height}
    # create keyboard with {field}
    def k_create(self, command):
        token = self.nextToken()
        if self.isSymbol():
            record = self.getSymbolRecord()
            command['varname'] = record['name']
            keyword = record['keyword']
            if keyword == 'rbrwin':
                x = None
                y = None
                w = self.compileConstant(600)
                h = self.compileConstant(1024)
                while True:
                    token = self.peek()
                    if token in ['title', 'at', 'size']:
                        self.nextToken()
                        if token == 'title': command['title'] = self.nextValue()
                        elif token == 'at':
                            x = self.nextValue()
                            y = self.nextValue()
                        elif token == 'size':
                            w = self.nextValue()
                            h = self.nextValue()
                        else: return False
                    else: break
                command['x'] = x
                command['y'] = y
                command['w'] = w
                command['h'] = h
                self.add(command)
                return True

            elif keyword == 'room':
                while True:
                    token = self.peek()
                    if token in ['spec', 'height', 'index']:
                        self.nextToken()
                        if token == 'spec':
                            command['spec'] = self.nextValue()
                        elif token == 'height':
                            command['height'] = self.nextValue()
                        elif token == 'index':
                            command['index'] = self.nextValue()
                    else: break
                self.add(command)
                return True

        elif token == 'keyboard':
            self.skip('with')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'element':
                    command['keyboard'] = record['name']
                    self.skip('in')
                    if self.nextIsSymbol():
                        record = self.getSymbolRecord()
                        if record['keyword'] == 'rbrwin':
                            command['window'] = record['name']
                            self.add(command)
                            return True

        return False

    def r_create(self, command):
        if 'keyboard' in command:
            field = self.getVariable(command['keyboard'])['widget']
            window = self.getVariable(command['window'])['window']
            Keyboard(self.program, receiver = TextReceiver(field), parent=window)
            return self.nextPC()

        record = self.getVariable(command['varname'])
        keyword = record['keyword']
        if keyword == 'rbrwin':
            title = self.getRuntimeValue(command['title'])
            w = self.getRuntimeValue(command['w'])
            h = self.getRuntimeValue(command['h'])
            x = command['x']
            y = command['y']
            if title == '':
                x = 0
                y = 0
            else:
                if x == None: x = (self.program.screenWidth - w) / 2
                else: x = self.getRuntimeValue(x)
                if y == None: y = (self.program.screenHeight - h) / 2
                else: y = self.getRuntimeValue(y)

            window = RBRWindow(self.program, title, x, y, w, h)
            record['window'] = window
            return self.nextPC()
        
        elif keyword == 'room':
            spec = self.getRuntimeValue(command['spec'])
            height = self.getRuntimeValue(command['height'])
            index = self.getRuntimeValue(command['index'])
            room = Room(self.program, spec, height, index)
            if not 'rooms' in record:
                record['value'][record['index']] = room
            return self.nextPC()

        return 0

    # get {variable} from {dialog} [with {value}]
    def k_get(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['hasValue']:
                command['target'] = record['name']
                self.skip('from')
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    keyword = record['keyword']
                    if keyword == 'modeDialog':
                        command['dialog'] = record['name']
                        if self.peek() == 'with':
                            self.nextToken()
                            if self.nextIsSymbol():
                                record = self.getSymbolRecord()
                                if not record['hasValue']: return False
                                command['with'] = self.getValue()
                            else: return False
                        self.add(command)
                        return True
        return False
    
    def r_get(self, command):
        target = self.getVariable(command['target'])
        dialog = self.getVariable(command['dialog'])
        data = self.getRuntimeValue(command['with']) if 'with' in command else None
        keyword = dialog['keyword']
        if keyword == 'modeDialog':
            value = ModeDialog(self.program, data).showDialog()
        v = {}
        v['type'] = 'text'
        v['content'] = value
        self.putSymbolValue(target, v)
        return self.nextPC()

    def k_modeDialog(self, command):
        return self.compileVariable(command)

    def r_modeDialog(self, command):
        return self.nextPC()

    def k_element(self, command):
        return self.compileVariable(command)

    def r_element(self, command):
        return self.nextPC()

    # on click {pushbutton}
    def k_on(self, command):
        def setupOn():
            command['goto'] = self.getPC() + 2
            self.add(command)
            self.nextToken()
            # Step over the click handler
            pcNext = self.getPC()
            cmd = {}
            cmd['domain'] = 'core'
            cmd['lino'] = command['lino']
            cmd['keyword'] = 'gotoPC'
            cmd['goto'] = 0
            cmd['debug'] = False
            self.add(cmd)
            # This is the click handler
            self.compileOne()
            cmd = {}
            cmd['domain'] = 'core'
            cmd['lino'] = command['lino']
            cmd['keyword'] = 'stop'
            cmd['debug'] = False
            self.add(cmd)
            # Fixup the goto
            self.getCommandAt(pcNext)['goto'] = self.getPC()

        token = self.nextToken()
        command['type'] = token
        if token == 'click':
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'button':
                    command['name'] = record['name']
                    setupOn()
                    return True
        return False
    
    def r_on(self, command):
        record = self.getVariable(command['name'])
        widget = record['widget']
        keyword = record['keyword']
        if keyword == 'button':
            widget.onClick = (command['goto'])
        return self.nextPC()

    def k_rbrwin(self, command):
        return self.compileVariable(command)

    def r_rbrwin(self, command):
        return self.nextPC()

    def k_room(self, command):
        return self.compileVariable(command, 'gui')

    def r_room(self, command):
        return self.nextPC()

   # select {choice} from menu {title} [with] {choices}
    def k_select(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['hasValue']:
                command['choice'] = record['name']
                if self.nextIs('from'):
                    if self.nextIs('menu'):
                        command['title'] = self.nextValue()
                        self.skip('with')
                        if self.nextIsSymbol():
                            record = self.getSymbolRecord()
                            if record['hasValue']:
                                command['choices'] = record['name']
                                self.add(command)
                                return True
        return False
    
    def r_select(self, command):
        target = self.getVariable(command['choice'])
        title = self.getRuntimeValue(command['title'])
        var = self.getVariable(command['choices'])
        choices = var['value'][var['index']]['content']
        choice = Menu(self.program, 50, self.program.rbrwin, title, choices).show()
        v = {}
        v['type'] = 'text'
        v['content'] = choice
        self.putSymbolValue(target, v)
        return self.nextPC()

   # set attribute {attr} [of] {window}/{room} [to] {value}
    def k_set(self, command):
        if self.nextIs('attribute'):
            command['attribute'] = self.nextValue()
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                keyword = record['keyword']
                if keyword in ['rbrwin', 'room']:
                    command['name'] = record['name']
                    self.skip('to')
                    command['value'] = self.nextValue()
                    self.add(command)
                    return True
        return False
    
    def r_set(self, command):
        if 'attribute' in command:
            attribute = self.getRuntimeValue(command['attribute'])
            record = self.getVariable(command['name'])
            value = self.getRuntimeValue(command['value'])
            keyword = record['keyword']
            if keyword == 'rbrwin':
                window = record['window']
                if attribute == 'system name':
                    profiles = window.profiles
                    profiles.setSystemName(value)
                elif attribute == 'profile':
                    profiles = window.profiles
                    profiles.setProfile(value)
            elif keyword == 'room':
                room = record['value'][record['index']]
                if attribute == 'temperature':
                    room.setTemperature(value)
            return self.nextPC()
        return 0

    # show {rbrwin}
    def k_show(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            keyword = record['keyword']
            command[keyword] = record['name']
            if keyword in ['rbrwin']:
                self.add(command)
                return True
        return False
        
    def r_show(self, command):
        if 'rbrwin' in command:
            window = self.getVariable(command['rbrwin'])['window']
            self.program.rbrwin = window
            window.show()
        return self.nextPC()

    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        value = {}
        value['domain'] = self.getName()
        token = self.getToken()
        value['name'] = token
        if self.isSymbol():
            record =self.getSymbolRecord()
            if record['extra'] == 'gui' or record['keyword'] == 'element':
                value['type'] = 'symbol'
                return value

            return None
        
        if token == 'the': token = self.nextToken()
        value['type'] = token

        if token == 'attribute':
            value['attr'] = self.nextValue()
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] in ['room', 'button']:
                    value['name'] = record['name']
                    return value

        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

    #############################################################################
    # Value handlers

    def v_symbol(self, value):
        v = {}
        v['type'] = 'text'
        record = self.getVariable(value['name'])
        if record['keyword'] == 'element':
            v['content'] = record['widget'].text()
        else:
            value = record['value'][record['index']]
            name = value.getName()
            mode = value.getMode()
            temp = value.getTemperature()
            v['content'] = f'{name} {mode} {temp}'
        return v
    
    def v_attribute(self, value):
        record = self.getVariable(value['name'])
        attr = self.getRuntimeValue(value['attr'])
        v = {}
        if attr == 'index':
            v['type'] = 'int'
            v['content'] = self.program.roomIndex
        else:
            keyword = record['keyword']
            if record['keyword'] == 'room':
                if attr == 'name':
                    type = 'text'
                    content = record['value'][record['index']].name
                elif attr == 'mode':
                    type = 'text'
                    content = record['value'][record['index']].mode
                else:
                    RuntimeError(self.program, f'Item has no attribute "{attr}"')
                v['type'] = type
                v['content'] = content
            else:
                RuntimeError(self.program, f'Element type "{keyword}" does not have attributes')
        return v

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers
