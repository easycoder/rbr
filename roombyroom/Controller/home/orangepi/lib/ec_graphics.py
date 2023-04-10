from ec_classes import CompileError, FatalError
from ec_handler import Handler
from picson import *

class Graphics(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'graphics'

    #############################################################################
    # Keyword handlers

    def k_attach(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            command['name'] = record['name']
            if self.nextIs('to'):
                value = self.nextValue()
                command['id'] = value
            self.add(command)
            return True
        self.compiler.warning('No valid symbol specified')
        return False

    def r_attach(self, command):
        target = self.getVariable(command['name'])
        id = self.getRuntimeValue(command['id'])
        element = getElement(id)
        if element == None:
            FatalError(self.program, f'There is no screen element with id \'{id}\'')
        target['id'] = [None] * target['elements']
        target['id'][target['index']] = id
        self.putSymbolValue(target, {'type': 'text', 'content': id})
        return self.nextPC()

    def k_clear(self, command):
        if self.nextIs('screen'):
            self.add(command)
            return True
        return False

    def r_clear(self, command):
        clearScreen()
        return self.nextPC()

    def k_close(self, command):
        if self.nextIs('screen'):
            self.add(command)
            return True
        return False

    def r_close(self, command):
        closeScreen()
        return self.nextPC()

    def k_create(self, command):
        if self.nextIs('screen'):
            command['fullscreen'] = False
            command['loglevel'] = 0
            while True:
                token = self.peek()
                if token == 'at':
                    self.nextToken()
                    command['left'] = self.nextValue()
                    command['top'] = self.nextValue()
                elif token == 'size':
                    self.nextToken()
                    command['width'] = self.nextValue()
                    command['height'] = self.nextValue()
                elif token == 'fill':
                    self.nextToken()
                    command['fill'] = self.nextValue()
                elif token == 'fullscreen':
                    self.nextToken()
                    command['fullscreen'] = True
                elif token == 'loglevel':
                    self.nextToken()
                    command['loglevel'] = self.nextToken()
                else:
                    break
            self.add(command)
            return True
        return False

    def r_create(self, command):
        command['program'].debugHook = writeLog
        createScreen(command)
        return self.nextPC()

    def k_dispose(self, command):
        command['name'] = self.nextValue()
        self.add(command)
        return True

    def r_dispose(self, command):
        dispose(self.getRuntimeValue(command['name']))
        return self.nextPC()

    def k_element(self, command):
        return self.compileVariable(command, 'element')

    def r_element(self, command):
        return self.nextPC()

    def k_ellipse(self, command):
        return self.compileVariable(command, 'ellipse')

    def r_ellipse(self, command):
        return self.nextPC()

    def k_gtest(self, command):
        command['name'] = self.nextValue()
        self.add(command)
        return True

    def r_gtest(self, command):
        gtest(self.getRuntimeValue(command['name']))
        return self.nextPC()

    def k_hide(self, command):
        self.nextToken()
        if self.getToken() == 'cursor':
            command['name'] = 'cursor'
            self.add(command)
            return True
        if self.isSymbol():
            command['name'] = self.getToken()
            self.add(command)
            return True
        return False

    def r_hide(self, command):
        if command['name'] == 'cursor':
            hideCursor()
            return self.nextPC()
        variable = self.getVariable(command['name'])
        id = variable['id'][variable['index']]
        hideElement(id)
        return self.nextPC()

    def k_image(self, command):
        return self.compileVariable(command, 'image')

    def r_image(self, command):
        return self.nextPC()

    def k_on(self, command):
        def setupCommand(command):
            command['goto'] = self.getPC() + 2
            self.add(command)
            self.nextToken()
            pcNext = self.getPC()
            cmd = {}
            cmd['domain'] = 'core'
            cmd['lino'] = command['lino']
            cmd['keyword'] = 'gotoPC'
            cmd['goto'] = 0
            cmd['debug'] = False
            self.addCommand(cmd)
            self.compileOne()
            cmd = {}
            cmd['domain'] = 'core'
            cmd['lino'] = command['lino']
            cmd['keyword'] = 'stop'
            cmd['debug'] = False
            self.addCommand(cmd)
            # Fixup the link
            self.getCommandAt(pcNext)['goto'] = self.getPC()
            return

        token = self.nextToken()
        command['type'] = token
        if token == 'click':
            if self.peek() == 'in':
                self.nextToken()
            if self.nextIs('screen'):
                command['target'] = None
            elif self.isSymbol():
                target = self.getSymbolRecord()
                command['target'] = target['name']
            else:
                CompileError(self.compiler, f'{self.getToken()} is not a screen element')
            setupCommand(command)
            return True
        elif token in ['init', 'tick']:
            setupCommand(command)
            return True
        return False

    def r_on(self, command):
        def click(id, program, pc):
            # print(f'ID = {id}')
            program.clicked = id
            self.easyCoder.run(program, pc)
            return

        program = command['program']
        pc = command['goto']
        if command['type'] == 'click':
            target = command['target']
            if target == None:
                value = 'screen'
            else:
                widget = self.getVariable(target)
            value = widget['value'][widget['index']]
            l = lambda id:  click(id, program, pc)
            setOnClick(value['content'], l)
        elif command['type'] == 'init':
            setOnInit(lambda: self.easyCoder.run(program, pc))
        elif command['type'] == 'tick':
            setOnTick(lambda: self.easyCoder.run(program, pc))
        return self.nextPC()

    def k_rectangle(self, command):
        return self.compileVariable(command, 'rectangle')

    def r_rectangle(self, command):
        return self.nextPC()

    def k_render(self, command):
        command['value'] = self.nextValue()
        if self.peek() == 'in':
            self.nextToken()
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                type = record['keyword']
                name = record['name']
                if type in ['rectangle', 'ellipse']:
                    command['parent'] = record['name']
                    self.add(command)
                    return True
                else:
                    self.warning(f'{name} cannot be a parent of another element')
                    return False
        command['parent'] = 'screen'
        self.add(command)
        return True

    def r_render(self, command):
        value = self.getRuntimeValue(command['value'])
        parent = command['parent']
        try:
            if parent != 'screen':
                record = self.getVariable(parent)
                parent = record['id'][record['index']]
            result = render(value, parent)
        except Exception as err:
            FatalError(command['program'], err)
        if result != None:
            FatalError(command['program'], f'Rendering error: {result}')
        return self.program.nextPC()

    def k_set(self, command):
        if self.peek() == 'the':
            self.nextToken()
        token = self.peek()
        command['variant'] = token
        if token in ['text', 'font', 'source']:
            self.nextToken()
            if self.peek() == 'of':
                self.nextToken()
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                command['name'] = record['name']
                if token in ['text', 'font'] and record['keyword'] != 'text':
                    CompileError(self.compiler, f'Symbol type is not \'text\'')
                if token in ['source'] and record['keyword'] != 'image':
                    CompileError(self.compiler, f'Symbol type is not \'image\'')
                if self.peek() == 'to':
                    self.nextToken()
                    command['value'] = self.nextValue()
                    self.add(command)
                    return True
            name = self.getToken()
            CompileError(self.compiler, f'Unknown symbol \'{name}\'')
        elif token == 'fill':
            self.nextToken()
            if self.peek() == 'color':
                self.nextToken()
            if self.peek() == 'of':
                self.nextToken()
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                command['name'] = record['name']
                if not record['keyword'] in ['rectangle', 'ellipse', 'text']:
                    CompileError(self.compiler, f'Symbol type is not \'rectangle\' or \'ellipse\'')
                if self.peek() == 'to':
                    self.nextToken()
                    command['value'] = self.nextValue()
                    self.add(command)
                return True
            return False
        return False

    def r_set(self, command):
        variant = command['variant']
        variable = self.getVariable(command['name'])
        element = self.getSymbolValue(variable)
        value = self.getRuntimeValue(command['value'])
        if variant == 'text':
            setText(element['content'], value)
        elif variant == 'font':
            setFont(element['content'], value)
        elif variant == 'fill':
            setFill(element['content'], value)
        elif variant == 'source':
            setSource(element['content'], value)
        return self.nextPC()

    def k_show(self, command):
        if self.nextIs('screen'):
            command['name'] = None
            self.add(command)
            return True
        else:
            if self.isSymbol():
                command['name'] = self.getToken()
                self.add(command)
                return True
        return False

    def r_show(self, command):
        if command['name'] == None:
            showScreen()
        else:
            variable = self.getVariable(command['name'])
            id = variable['id'][variable['index']]
            showElement(id)
        return self.nextPC()

    def k_spec(self, command):
        return self.compileVariable(command, 'spec', True)

    def r_spec(self, command):
        return self.nextPC()

    def k_text(self, command):
        return self.compileVariable(command, 'text')

    def r_text(self, command):
        return self.nextPC()

    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        value = {}
        value['domain'] = 'graphics'
        token = self.getToken()
        if self.isSymbol():
            value['name'] = token
            symbolRecord = self.getSymbolRecord()
            keyword = symbolRecord['keyword']
            if keyword == 'module':
                value['type'] = 'module'
                return value

            if symbolRecord['valueHolder'] == True or keyword == 'dictionary':
                value['type'] = 'symbol'
                return value
            return None
        
        if self.tokenIs('attribute'):
            attribute = self.nextValue()
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    symbolRecord = self.getSymbolRecord()
                    if symbolRecord['keyword'] in ['element', 'text', 'image']:
                        value['name'] = symbolRecord['name']
                    else:
                        return None
                else:
                    value['id'] = self.nextValue()
                value['attribute'] = attribute
                value['type'] = 'attributeOf'
                return value
            return None

        if self.tokenIs('the'):
            self.nextToken()
        token = self.getToken()
        if token == 'id':
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    symbolRecord = self.getSymbolRecord()
                    value['type'] = 'idOf'
                    value['name'] = symbolRecord['name']
                    return value
            return None
        
        if token == 'screen':
            token = self.nextToken()
            if token == 'width':
                value['type'] = 'screenWidth'
                return value
            if token == 'height':
                value['type'] = 'screenHeight'
                return value
        
        if token == 'clicked':
            if self.nextIs('element'):
                value['type'] = 'clicked'
                return value

        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

    #############################################################################
    # Value handlers

    def v_symbol(self, symbolRecord):
        result = {}
        if symbolRecord['valueHolder']:
            symbolValue = self.getSymbolValue(symbolRecord)
            if symbolValue == None:
                return None
            result['type'] = symbolValue['type']
            content = symbolValue['content']
            if content == None:
                return ''
            result['content'] = content
            return result
        else:
            return ''

    def v_idOf(self, v):
        variable = self.getVariable(v['name'])
        symbolValue = self.getSymbolValue(variable)
        return {
            "type": "int",
            "content": getElement(symbolValue['content'])['id']
        }

    def v_screenWidth(self, v):
        return {
            "type": "int",
            "content": getScreenWidth()
        }

    def v_screenHeight(self, v):
        return {
            "type": "int",
            "content": getScreenHeight()
        }
    
    def v_clicked(self, v):
        return {
            "type": "text",
            "content": self.program.clicked
        }
    
    def v_attributeOf(self, v):
        if 'name' in v:
            variable = self.getVariable(v['name'])
            id = variable['id'][variable['index']]
        else:
            id = self.getRuntimValue(v['id'])
        attribute = self.getRuntimeValue(v['attribute'])
        return {
            "type": "text",
            "content": getAttribute(id, attribute)
        }

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers
