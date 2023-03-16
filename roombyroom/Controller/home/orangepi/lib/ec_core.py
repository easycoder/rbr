import json, math, hashlib, os, requests, time, numbers
from datetime import datetime, timezone
from random import randrange
from ec_program import Program
from ec_classes import CompileError, ECRuntimeWarning, FatalError
from ec_handler import Handler
from ec_timestamp import getTimestamp

class Core(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'core'

    #############################################################################
    # Keyword handlers

    # add <value> to <variable>
    # add <value> to <value> giving <variable>
    def k_add(self, command):
        # Get the (first) value
        command['value1'] = self.nextValue()
        if self.nextToken() == 'to':
            if self.nextIsSymbol():
                symbolRecord = self.getSymbolRecord()
                if symbolRecord['valueHolder']:
                    command['value2'] = self.getValue()
                    if self.peek() == 'giving':
                        self.nextToken()
                        name = self.nextToken()
                        if (self.isSymbol()):
                            command['target'] = self.getToken()
                            self.add(command)
                            return True
                        CompileError(self.compiler, f'No such variable: "{name}"')
                    else:
                        # Here the variable is the target
                        command['target'] = self.getToken()
                        self.add(command)
                        return True
                self.warning(f'core.add: Expected value holder')
            else:
                # Here we have 2 values so 'giving' must come next
                command['value2'] = self.getValue()
                if self.nextToken() == 'giving':
                    command['target'] = self.nextToken()
                    self.add(command)
                    return True
                self.warning(f'core.add: Expected "giving"')
        return False

    def r_add(self, command):
        value1 = command['value1']
        try:
            value2 = command['value2']
        except:
            value2 = None
        target = self.getVariable(command['target'])
        if not target['valueHolder']:
            self.variableDoesNotHoldAValueError(target['name'])
            return None
        value = self.getSymbolValue(target)
        if value == None:
            value = {}
            value['type'] = 'int'
        if value2:
            v1 = int(self.getRuntimeValue(value1))
            v2 = int(self.getRuntimeValue(value2))
            value['content'] = v1+v2
        else:
#            if value['type'] != 'int' and value['content'] != None:
#                self.nonNumericValueError()
            v = self.getRuntimeValue(value)
            v = int(v)
            v1 = int(self.getRuntimeValue(value1))
            value['content'] = v+v1
        self.putSymbolValue(target, value)
        return self.nextPC()

    # append <value> to <variable>
    def k_append(self, command):
        command['value'] = self.nextValue()
        if self.nextIs('to'):
            if self.nextIsSymbol():
                symbolRecord = self.getSymbolRecord()
                if symbolRecord['valueHolder']:
                    command['target'] = symbolRecord['name']
                    self.add(command)
                    return True
                self.warning(f'Variable "{symbolRecord["name"]}" does not hold a value')
        return False

    def r_append(self, command):
        value = self.getRuntimeValue(command['value'])
        target = self.getVariable(command['target'])
        val = self.getSymbolValue(target)
        content = val['content']
        if content == '':
            content = []
        content.append(value)
        val['content'] = content
        self.putSymbolValue(target, val)
        return self.nextPC()

    # begin
    def k_begin(self, command):
        if self.nextToken() == 'end':
            cmd = {}
            cmd['domain'] = 'core'
            cmd['keyword'] = 'end'
            cmd['debug'] = True
            cmd['lino'] = command['lino']
            self.addCommand(cmd)
            return self.nextPC()
        else:
            return self.compileFromCurrentIndex(['end'])

    # clear <variable>
    def k_clear(self, command):
        if self.nextIsSymbol():
            target = self.getSymbolRecord()
            if target['valueHolder']:
                command['target'] = target['name']
                self.add(command)
                return True
        return False

    def r_clear(self, command):
        target = self.getVariable(command['target'])
        val = {}
        val['type'] = 'boolean'
        val['content'] = False
        self.putSymbolValue(target, val)
        # self.add(command)
        return self.nextPC()

    # close <file>
    def k_close(self, command):
        if self.nextIsSymbol():
            fileRecord = self.getSymbolRecord()
            if fileRecord['keyword'] == 'file':
                command['file'] = fileRecord['name']
                self.add(command)
                return True
        return False

    def r_close(self, command):
        fileRecord = self.getVariable(command['file'])
        fileRecord['file'].close()
        return self.nextPC()

    # create directory <name>
    def k_create(self, command):
        if self.nextIs('directory'):
            command['item'] = 'directory'
            command['path'] = self.nextValue()
            self.add(command)
            return True
        return False

    def r_create(self, command):
        if command['item'] == 'directory':
            path = self.getRuntimeValue(command['path'])
            if not os.path.exists(path):
                os.makedirs(path)
        return self.nextPC()

    # debug start/stop/program
    def k_debug(self, command):
        token = self.peek()
        if token in ['step', 'stop', 'program']:
            command['mode'] = token
            self.nextToken()
        else:
            command['mode'] = None
        self.add(command)
        return True

    def r_debug(self, command):
        if command['mode'] == 'step':
            self.program.debugStep = True
        elif command['mode'] == 'stop':
            self.program.debugStep = False
        elif command['mode'] == 'program':
            for item in self.code:
                print(json.dumps(item, indent = 2))
        return self.nextPC()

    # decrement <variable>
    def k_decrement(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['valueHolder']:
                command['target'] = self.getToken()
                self.add(command)
                return True
            self.warning(f'Variable "{symbolRecord["name"]}" does not hold a value')
        return False

    def r_decrement(self, command):
        return self.incdec(command, '-')

    # detach
    def k_detach(self, command):
        self.add(command)
        return True

    def r_detach(self, command):
        program = self.program
        parent= program.parent
        if parent == None:
            FatalError(program, f'Module {program.name} has no parent')
        print(f'{program.name} has detached')
        parent.enabled = True
        self.program.parentNext = None
        self.easyCoder.run(parent, parent.nextPC(), False)
        self.easyCoder.run(program, self.nextPC())

    # declare a 'dictionary' variable
    def k_dictionary(self, command):
        return self.compileVariable(command, 'dictionary')

    def r_dictionary(self, command):
        return self.nextPC()

    # divide <variable> by <value>
    # divide <value> by <value> giving <variable>
    def k_divide(self, command):
        # Get the (first) value
        command['value1'] = self.nextValue()
        if self.nextToken() == 'by':
            command['value2'] = self.nextValue()
            if self.peek() == 'giving':
                self.nextToken()
                name = self.nextToken()
                if (self.isSymbol()):
                    command['target'] = self.getToken()
                    self.add(command)
                    return True
                CompileError(self.compiler, f'No such variable: "{name}"')
            else:
                # First value must be a variable
                if command['value1']['type'] == 'symbol':
                    command['target'] = command['value1']['name']
                    self.add(command)
                    return True
                CompileError(self.compiler, 'First value must be a variable')
        return False

    def r_divide(self, command):
        value1 = command['value1']
        try:
            value2 = command['value2']
        except:
            value2 = None
        target = self.getVariable(command['target'])
        if not target['valueHolder']:
            self.variableDoesNotHoldAValueError(target['name'])
            return None
        value = self.getSymbolValue(target)
        if value == None:
            value = {}
            value['type'] = 'int'
        if value2:
            v1 = int(self.getRuntimeValue(value1))
            v2 = int(self.getRuntimeValue(value2))
            value['content'] = v1/v2
        else:
            if value['type'] != 'int' and value['content'] != None:
                self.nonNumericValueError(self.compiler, command['lino'])
            v = int(self.getRuntimeValue(value))
            v1 = int(self.getRuntimeValue(value1))
            value['content'] = v/v1
        self.putSymbolValue(target, value)
        return self.nextPC()

    # dummy
    def k_dummy(self, command):
        self.add(command)
        return True

    def r_dummy(self, command):
        return self.nextPC()

    # end
    def k_end(self, command):
        self.add(command)
        return True

    def r_end(self, command):
        return self.nextPC()

    # exit
    def k_exit(self, command):
        self.add(command)
        return True

    def r_exit(self, command):
        print(f'{self.program.name} has finished')
        parent= self.program.parent
        if parent == None:
            self.easyCoder.setRunning(False)
        elif parent.running:
            self.program.running = False
            parent.enabled = True
            if self.program.parentNext:
                self.easyCoder.run(parent, self.program.parentNext)
        return 0

    # Declare a 'file' variable
    def k_file(self, command):
        return self.compileVariable(command, 'file')

    def r_file(self, command):
        return self.nextPC()

    # fork [to] <label>
    def k_fork(self, command):
        if self.peek() == 'to':
            self.nextToken()
        command['fork'] = self.nextToken()
        self.add(command)
        return True

    def r_fork(self, command):
        next = self.nextPC()
        label = command['fork']
        try:
            self.easyCoder.run(self.program, self.symbols[f'{label}:'])
            return next
        except Exception as e:
            FatalError(self.program, f'There is no label "{label + ":"}"')

    # get <variable from <url> [or <statement>]
    def k_get(self, command):
        self.add(command)
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['valueHolder']:
                command['target'] = self.getToken()
            else:
                CompileError(self.compiler, f'Variable "{symbolRecord["name"]}" does not hold a value')
        if self.nextIs('from'):
            command['url'] = self.nextValue()
        command['or'] = None
        get = self.getPC()
        self.addCommand(command)
        if self.peek() == 'or':
            self.nextToken()
            self.nextToken()
            # Add a 'goto' to skip the 'or'
            cmd = {}
            cmd['lino'] = command['lino']
            cmd['domain'] = 'core'
            cmd['keyword'] = 'gotoPC'
            cmd['goto'] = 0
            cmd['debug'] = False
            skip = self.getPC()
            self.addCommand(cmd)
            # Process the 'or'
            self.getCommandAt(get)['or'] = self.getPC()
            self.compileOne()
            # Fixup the skip
            self.getCommandAt(skip)['goto'] = self.getPC()
        return True

    def r_get(self, command):
        global errorCode, errorReason
        retval = {}
        retval['type'] = 'text'
        retval['numeric'] = False
        url = self.getRuntimeValue(command['url'])
        target = self.getVariable(command['target'])
        try:
            response = requests.get(url, auth = ('user', 'pass'), timeout=5)
            if response.status_code >= 400:
                errorCode = response.status_code
                errorReason = response.reason
                if command['or'] != None:
                    return command['or']
                else:
                    FatalError(self.program, f'Error code {errorCode}: {errorReason}')
        except Exception as e:
            errorReason = str(e)
            if command['or'] != None:
                return command['or']
            else:
                FatalError(self.program, f'Error: {errorReason}')
        retval['content'] = response.text
        self.program.putSymbolValue(target, retval);
        return self.nextPC()

    # go [to] <label>
    def k_go(self, command):
        if self.peek() == 'to':
            self.nextToken()
            return self.k_goto(command)

    # goto <label>
    def k_goto(self, command):
        command['keyword'] = 'goto'
        command['goto'] = self.nextToken()
        self.add(command)
        return True

    def r_goto(self, command):
        try:
            label = f'{command["goto"]}:'
            if self.symbols[label]:
                return self.symbols[label]
        except:
            pass
        FatalError(self.program, f'There is no label "{label}"')

    def r_gotoPC(self, command):
        return command['goto']

    # gosub [to] <label>
    def k_gosub(self, command):
        if self.peek() == 'to':
            self.nextToken()
        command['gosub'] = self.nextToken()
        self.add(command)
        return True

    def r_gosub(self, command):
        try:
            label = command['gosub'] + ':'
            address = self.symbols[label]
            if address != None:
                self.stack.append(self.nextPC())
                return address
        except:
            pass
        FatalError(self.program, f'There is no label "{label}"')

    # if <condition> <statement> [else <statement>]
    def k_if(self, command):
        command['condition'] = self.nextCondition()
        self.addCommand(command)
        self.nextToken()
        pcElse = self.getPC()
        cmd = {}
        cmd['lino'] = command['lino']
        cmd['domain'] = 'core'
        cmd['keyword'] = 'gotoPC'
        cmd['goto'] = 0
        cmd['debug'] = False
        self.addCommand(cmd)
        # Get the 'then' code
        self.compileOne()
        if self.peek() == 'else':
            self.nextToken()
            # Add a 'goto' to skip the 'else'
            pcNext = self.getPC()
            cmd = {}
            cmd['lino'] = command['lino']
            cmd['domain'] = 'core'
            cmd['keyword'] = 'gotoPC'
            cmd['goto'] = 0
            cmd['debug'] = False
            self.addCommand(cmd)
            # Fixup the link to the 'else' branch
            self.getCommandAt(pcElse)['goto'] = self.getPC()
            # Process the 'else' branch
            self.nextToken()
            self.compileOne()
            # Fixup the pcNext 'goto'
            self.getCommandAt(pcNext)['goto'] = self.getPC()
        else:
            # We're already at the next command
            self.getCommandAt(pcElse)['goto'] = self.getPC()
        return True

    def r_if(self, command):
        test = self.program.condition.testCondition(command['condition'])
        if test:
            self.program.pc += 2
        else:
            self.program.pc += 1
        return self.program.pc

    # increment <variable>
    def k_increment(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['valueHolder']:
                command['target'] = self.getToken()
                self.add(command)
                return True
            self.warning(f'Variable "{symbolRecord["name"]}" does not hold a value')
        return False

    def r_increment(self, command):
        return self.incdec(command, '+')

    # import <type> <name> [and <type> <name>...]
    def k_import(self, command):
        exports = self.program.exports
        imports = []
        while True:
            variable = {}
            variable['type'] = self.nextToken()
            variable['name'] = self.nextToken()
            imports.append(variable)
            if self.peek() == 'and':
                self.nextToken()
            else:
                break
        if len(imports) != len(exports):
            CompileError(self.compiler, 'Imports do not match exports')
        for index, export in enumerate(exports):
            variable = imports[index]
            name = variable['name']
            if variable['type'] != export['keyword'] or name != export['name']:
                CompileError(self.compiler, f'Import "{name}" does not match export')
        return True

    def r_import(self, command):
        return self.nextPC()

    def k_log(self, command):
        value = self.nextValue()
        if value != None:
            command['value'] = value
            self.add(command)
            return True
        CompileError(self.compiler, 'I can\'t log this value')

    def r_log(self, command):
        def writeLog(text):
            f = open('log.txt', 'a')
            f.write(f'{text}\n')
            f.close()
            
        value = self.getRuntimeValue(command['value'])
        if value != None:
            writeLog(f'-> {value}')
        return self.nextPC()

    # index <variable> to <value>
    def k_index(self, command):
        # get the variable
        if self.nextIsSymbol():
            command['target'] = self.getToken()
            if self.nextToken() == 'to':
                # get the value
                command['value'] = self.nextValue()
                self.add(command)
                return True
        return False

    def r_index(self, command):
        symbolRecord = self.getVariable(command['target'])
        symbolRecord['index'] = self.getRuntimeValue(command['value'])
        return self.nextPC()

    # input <variable> with <prompt>
    def k_input(self, command):
        # get the variable
        if self.nextIsSymbol():
            command['target'] = self.getToken()
            value = {}
            value['type'] = 'text'
            value['numeric'] = 'false'
            value['content'] = ': '
            command['prompt'] = value
            if self.peek() == 'with':
                self.nextToken()
                command['prompt'] = self.nextValue()
            self.add(command)
            return True
        return False

    def r_input(self, command):
        symbolRecord = self.getVariable(command['target'])
        prompt = command['prompt']['content']
        value = {}
        value['type'] = 'text'
        value['numeric'] = False
        value['content'] = prompt+input(prompt)
        self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    # Declare a "module" variable
    def k_module(self, command):
        return self.compileVariable(command, 'module', True)

    def r_module(self, command):
        return self.nextPC()

    # multiply <variable> by <value>
    # multiply <value> by <value> giving <variable>
    def k_multiply(self, command):
        # Get the (first) value
        command['value1'] = self.nextValue()
        if self.nextToken() == 'by':
            command['value2'] = self.nextValue()
            if self.peek() == 'giving':
                self.nextToken()
                name = self.nextToken()
                if (self.isSymbol()):
                    command['target'] = self.getToken()
                    self.add(command)
                    return True
                CompileError(self.compiler, f'No such variable: "{name}"')
            else:
                # First value must be a variable
                if command['value1']['type'] == 'symbol':
                    command['target'] = command['value1']['name']
                    self.add(command)
                    return True
                CompileError(self.compiler, 'First value must be a variable')
        return False

    def r_multiply(self, command):
        value1 = command['value1']
        try:
            value2 = command['value2']
        except:
            value2 = None
        target = self.getVariable(command['target'])
        if not target['valueHolder']:
            self.variableDoesNotHoldAValueError(target['name'])
            return None
        value = self.getSymbolValue(target)
        if value == None:
            value = {}
            value['type'] = 'int'
        if value2:
            v1 = int(self.getRuntimeValue(value1))
            v2 = int(self.getRuntimeValue(value2))
            value['content'] = v1*v2
        else:
            if value['type'] != 'int' and value['content'] != None:
                self.nonNumericValueError()
                return None
            v = int(self.getRuntimeValue(value))
            v1 = int(self.getRuntimeValue(value1))
            value['content'] = v*v1
        self.putSymbolValue(target, value)
        return self.nextPC()

    # open <file> <path> for reading/writing/appending
    def k_open(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            command['target'] = symbolRecord['name']
            command['path'] = self.nextValue()
            if symbolRecord['keyword'] == 'file':
                if self.peek() == 'for':
                    self.nextToken()
                    token = self.nextToken()
                    if token == 'appending':
                        mode = 'a+'
                    elif token == 'reading':
                        mode = 'r'
                    elif token == 'writing':
                        mode = 'w'
                    else:
                        CompileError(self.compiler, 'Unknown file open mode {self.getToken()}')
                        return False
                    command['mode'] = mode
                    self.add(command)
                    return True
                else:
                    CompileError(self.compiler, f'Missing open mode (for reading/writing/appending)')
            else:
                CompileError(self.compiler, f'Variable "{self.getToken()}" is not a file')
        else:
            self.warning(f'core.open: Variable "{self.getToken()}" not declared')
        return False

    def r_open(self, command):
        symbolRecord = self.getVariable(command['target'])
        path = self.getRuntimeValue(command['path'])
        if command['mode'] == 'r' and os.path.exists(path) or command['mode'] != 'r':
            symbolRecord['file'] = open(path, command['mode'])
            return self.nextPC()
        FatalError(self.program, f"File {path} does not exist")

    # post [<content>] to <url> [or <statement>]
    def k_post(self, command):
        if self.nextIs('to'):
            command['value'] = self.getConstant('')
            command['url'] = self.getValue()
        else:
            command['value'] = self.getValue()
            if self.nextIs('to'):
                command['url'] = self.nextValue()
        if self.peek() == 'giving':
            self.nextToken()
            command['result'] = self.nextToken()
        else:
            command['result'] = None
        command['or'] = None
        post = self.getPC()
        self.addCommand(command)
        if self.peek() == 'or':
            self.nextToken()
            self.nextToken()
            # Add a 'goto' to skip the 'or'
            cmd = {}
            cmd['lino'] = command['lino']
            cmd['domain'] = 'core'
            cmd['keyword'] = 'gotoPC'
            cmd['goto'] = 0
            cmd['debug'] = False
            skip = self.getPC()
            self.addCommand(cmd)
            # Process the 'or'
            self.getCommandAt(post)['or'] = self.getPC()
            self.compileOne()
            # Fixup the skip
            self.getCommandAt(skip)['goto'] = self.getPC()
        return True

    def r_post(self, command):
        global errorCode, errorReason
        retval = {}
        retval['type'] = 'text'
        retval['numeric'] = False
        value = self.getRuntimeValue(command['value'])
        url = self.getRuntimeValue(command['url'])
        try:
            response = requests.post(url, value, timeout=5)
            retval['content'] = response.text
            if response.status_code >= 400:
                errorCode = response.status_code
                errorReason = response.reason
                if command['or'] != None:
                    return command['or']
                else:
                    FatalError(self.program, f'Error code {errorCode}: {errorReason}')
        except Exception as e:
            errorReason = str(e)
            if command['or'] != None:
                return command['or']
            else:
                FatalError(self.program, f'Error: {errorReason}')
        if command['result'] != None:
            result = self.getVariable(command['result'])
            self.program.putSymbolValue(result, retval);
        return self.nextPC()

    # print <value>
    def k_print(self, command):
        value = self.nextValue()
        if value != None:
            command['value'] = value
            self.add(command)
            return True
        CompileError(self.compiler, 'I can\'t print this value')

    def r_print(self, command):
        value = self.getRuntimeValue(command['value'])
        if value != None:
            print(f'-> {value}')
        return self.nextPC()

    # put <value> into <variable>
    # put <value> into <dictionary> as <key>
    def k_put(self, command):
        command['value'] = self.nextValue()
        if self.nextIs('into'):
            if self.nextIsSymbol():
                symbolRecord = self.getSymbolRecord()
                command['target'] = symbolRecord['name']
                if symbolRecord['valueHolder']:
                        self.add(command)
                        return True
                elif symbolRecord['keyword'] == 'dictionary':
                    if self.peek() == 'as':
                        self.nextToken()
                    command['keyword'] = 'putDict'
                    command['key'] = self.nextValue()
                    self.add(command)
                    return True
                else:
                    CompileError(self.compiler, f'Symbol {symbolRecord["name"]} is not a value holder')
            else:
                CompileError(self.compiler, f'No such variable: "{self.getToken()}"')
        return False

    def r_put(self, command):
        value = self.evaluate(command['value'])
        if value == None:
            FatalError(self.program, 'No value (probably an uninitilized variable)')
        symbolRecord = self.getVariable(command['target'])
        if not symbolRecord['valueHolder']:
            FatalError(self.program, f'Variable {symbolRecord["name"]} does not hold a value')
        self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    def r_putDict(self, command):
        key = self.getRuntimeValue(command['key'])
        value = self.getRuntimeValue(command['value'])
        symbolRecord = self.getVariable(command['target'])
        record = self.getSymbolValue(symbolRecord)
        if record == None:
            record = {}
            record['type'] = 'text'
            content = {}
        else:
            content = record['content']
        if content is None:
            content = {}
        record['type'] = 'int' if isinstance(value, int) else 'text'
        content[key] = value
        record['content'] = content
        self.putSymbolValue(symbolRecord, record)
        return self.nextPC()

    # read <variable> from <file>
    def k_read(self, command):
        if self.peek() == 'line':
            self.nextToken()
            command['line'] = True
        else:
            command['line'] = False
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['valueHolder']:
                if self.peek() == 'from':
                    self.nextToken()
                    if self.nextIsSymbol():
                        fileRecord = self.getSymbolRecord()
                        if fileRecord['keyword'] == 'file':
                            command['target'] = symbolRecord['name']
                            command['file'] = fileRecord['name']
                            self.add(command)
                            return True
            CompileError(self.compiler, f'Symbol "{symbolRecord["name"]}" is not a value holder')
        CompileError(self.compiler, f'Symbol "{self.getToken()}" has not been declared')

    def r_read(self, command):
        symbolRecord = self.getVariable(command['target'])
        fileRecord = self.getVariable(command['file'])
        line = command['line']
        file = fileRecord['file']
        if file.mode == 'r':
            value = {}
            content = file.readline() if line else file.read()
            value['type'] = 'text'
            value['numeric'] = False
            value['content'] = content
            self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    # replace <value> with <value> in <variable>
    def k_replace(self, command):
        original = self.nextValue()
        if self.peek() == 'with':
            self.nextToken()
            replacement = self.nextValue()
            if self.nextIs('in'):
                if self.nextIsSymbol():
                    templateRecord = self.getSymbolRecord()
                    command['original'] = original
                    command['replacement'] = replacement
                    command['target'] = templateRecord['name']
                    self.add(command)
                    return True
        return False

    def r_replace(self, command):
        templateRecord = self.getVariable(command['target'])
        content = self.getSymbolValue(templateRecord)['content']
        original = self.getRuntimeValue(command['original'])
        replacement = self.getRuntimeValue(command['replacement'])
        content = content.replace(original, f'{replacement}')
        value = {}
        value['type'] = 'text'
        value['numeric'] = False
        value['content'] = content
        self.putSymbolValue(templateRecord, value)
        return self.nextPC()

    # return
    def k_return(self, command):
        self.add(command)
        return True

    def r_return(self, command):
        return self.stack.pop()

    # run <name> with <variables> as <module> then <statement>
    def k_run(self, command):
        command['path'] = self.nextValue()
        command['variables'] = []
        command['module'] = None
        command['then'] = 0
        self.nextToken()
        while True:
            token = self.getToken()
            if token == 'with':
                variables = []
                while self.nextIsSymbol():
                    variable = self.getSymbolRecord()
                    variables.append(variable)
                    if not self.nextIs('and'):
                        break
                command['variables'] = variables
            elif token == 'as':
                name = self.nextToken()
                if self.isSymbol():
                    record = self.getSymbolRecord()
                    if record['keyword'] == 'module':
                        command['module'] = record['name']
                    else:
                        CompileError(self.compiler, f'"{name}" is not a module variable')
                else:
                    CompileError(self.compiler, f'"{name}" is not a variable')
            else:
                break
        if self.peek() == 'then':
            self.nextToken()
            command['then'] = self.getPC()
        self.add(command)
        return True

    def r_run(self, command):
        path = self.getRuntimeValue(command['path'])
        f = open(path)
        source = f.read()
        domains = []
        for domain in self.program.domains:
            domains.append(domain.__class__)
        # self.program.nextPC= self.nextPC()
        self.program.enabled = False
        program = Program(self.program.easyCoder, source, domains, self.program, command['variables'])
        module = self.getVariable(command['module'])
        if 'runnning' in module and module['running']:
            moduleName = module['name']
            FatalError(self.program, f'Module {moduleName} is already running')
        program.parentNext = self.program.nextPC()
        self.easyCoder.run(program, 0)
        return 0

    # script
    def k_script(self, command):
        self.program.name = self.nextToken()
        return True

    # set <variable>
    # set the elements of <variable> to <value>
    # set property <value> of <variable> to <value>
    # set element <value> of <variable> to <value>
    def k_set(self, command):
        if self.nextIsSymbol():
            target = self.getSymbolRecord()
            if target['valueHolder']:
                command['type'] = 'set'
                command['target'] = target['name']
                self.add(command)
                return True

        token = self.getToken()
        if token == 'the':
            token = self.nextToken()
        if token == 'elements':
            self.nextToken()
            if self.peek() == 'of':
                self.nextToken()
            if self.nextIsSymbol():
                command['type'] = 'elements'
                command['name'] = self.getToken()
                if self.peek() == 'to':
                    self.nextToken()
                command['elements'] = self.nextValue()
                self.add(command)
                return True

        if token == 'property':
            command['type'] = 'property'
            command['name'] = self.nextValue()
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    command['target'] = self.getSymbolRecord()['name']
                    if self.nextIs('to'):
                        command['value'] = self.nextValue()
                        self.add(command)
                        return True

        if token == 'element':
            command['type'] = 'element'
            command['index'] = self.nextValue()
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    command['target'] = self.getSymbolRecord()['name']
                    if self.nextIs('to'):
                        command['value'] = self.nextValue()
                        self.add(command)
                        return True

        return False

    def r_set(self, command):
        cmdType = command['type']
        if cmdType == 'set':
            target = self.getVariable(command['target'])
            val = {}
            val['type'] = 'boolean'
            val['content'] = True
            self.putSymbolValue(target, val)
            return self.nextPC()

        if cmdType == 'elements':
            symbolRecord = self.getVariable(command['name'])
            elements = self.getRuntimeValue(command['elements'])
            symbolRecord['elements'] = elements
            symbolRecord['value'] = [None] * elements
            return self.nextPC()

        if cmdType == 'property':
            value = self.getRuntimeValue(command['value'])
            name = self.getRuntimeValue(command['name'])
            target = command['target']
            targetVariable = self.getVariable(target)
            val = self.getSymbolValue(targetVariable)
            try:
                content = val['content']
            except:
                FatalError(self.program, f'{target} is not an object')
            if content == '':
                content = {}
            try:
                content[name] = value
            except:
                FatalError(self.program, f'{target} is not an object')
            val['content'] = content
            self.putSymbolValue(targetVariable, val)
            return self.nextPC()

        if cmdType == 'element':
            value = self.getRuntimeValue(command['value'])
            index = self.getRuntimeValue(command['index'])
            target = self.getVariable(command['target'])
            val = self.getSymbolValue(target)
            content = val['content']
            if content == '':
                content = []
            # else:
            # 	content = json.loads(content)
            content[index] = value
            val['content'] = content
            self.putSymbolValue(target, val)
            return self.nextPC()

    # split <variable> on <value>
    def k_split(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['valueHolder']:
                command['target'] = symbolRecord['name']
                command['on'] = '\n'
                if self.peek() == 'on':
                    self.nextToken()
                    command['on'] = self.nextValue()
                self.add(command)
                return True
        return False

    def r_split(self, command):
        target = self.getVariable(command['target'])
        value = self.getSymbolValue(target)
        content = value['content'].split(command['on']['content'])
        elements = len(content)
        target['elements'] = elements
        target['value'] = [None] * elements

        for index, item in enumerate(content):
            element = {}
            element['type'] = 'text'
            element['numeric'] = 'false'
            element['content'] = item
            target['value'][index] = element

        return self.nextPC()

    # stop
    def k_stop(self, command):
        self.add(command)
        return True

    def r_stop(self, command):
        return 0

    # system <command>
    def k_system(self, command):
        value = self.nextValue()
        if value != None:
            command['value'] = value
            self.add(command)
            return True
        CompileError(self.compiler, 'I can\'t give this command')

    def r_system(self, command):
        value = self.getRuntimeValue(command['value'])
        if value != None:
            os.system(value)
            return self.nextPC()

    # take <value> from <variable>
    # take <value> from <value> giving <variable>
    def k_take(self, command):
        # Get the (first) value
        command['value1'] = self.nextValue()
        if self.nextToken() == 'from':
            if self.nextIsSymbol():
                symbolRecord = self.getSymbolRecord()
                if symbolRecord['valueHolder']:
                    command['value2'] = self.getValue()
                    if self.peek() == 'giving':
                        self.nextToken()
                        name = self.nextToken()
                        if (self.isSymbol()):
                            command['target'] = self.getToken()
                            self.add(command)
                            return True
                        CompileError(self.compiler, f'No such variable: "{name}"')
                    else:
                        # Here the variable is the target
                        command['target'] = self.getToken()
                        self.add(command)
                        return True
                self.warning(f'core.take: Expected value holder')
            else:
                # Here we have 2 values so 'giving' must come next
                command['value2'] = self.getValue()
                if self.nextToken() == 'giving':
                    if (self.nextIsSymbol()):
                        command['target'] = self.getToken()
                        self.add(command)
                        return True
                    else:
                        CompileError(self.compiler, f'\'{self.getToken()}\' is not a symbol')
                else:
                    self.warning(f'core.take: Expected "giving"')
        return False

    def r_take(self, command):
        value1 = command['value1']
        try:
            value2 = command['value2']
        except:
            value2 = None
        target = self.getVariable(command['target'])
        if not target['valueHolder']:
            self.variableDoesNotHoldAValueError(target['name'])
            return None
        value = self.getSymbolValue(target)
        if value == None:
            value = {}
            value['type'] = 'int'
        if value2:
            v1 = int(self.getRuntimeValue(value1))
            v2 = int(self.getRuntimeValue(value2))
            value['content'] = v2-v1
        else:
            v = int(self.getRuntimeValue(value))
            v1 = int(self.getRuntimeValue(value1))
            value['content'] = v-v1
        self.putSymbolValue(target, value)
        return self.nextPC()

    # toggle <variable>
    def k_toggle(self, command):
        if self.nextIsSymbol():
            target = self.getSymbolRecord()
            if target['valueHolder']:
                command['target'] = target['name']
                self.add(command)
                return True
        return False

    def r_toggle(self, command):
        target = self.getVariable(command['target'])
        value = self.getSymbolValue(target)
        val = {}
        val['type'] = 'boolean'
        val['content'] = not value['content']
        self.putSymbolValue(target, val)
        self.add(command)
        return self.nextPC()

    # Declare a "variable" variable
    def k_variable(self, command):
        return self.compileVariable(command, 'variable', True)

    def r_variable(self, command):
        return self.nextPC()

    # wait <value> milli/millis/tick/ticks/second/seconds/minute/minutes
    def k_wait(self, command):
        command['value'] = self.nextValue()
        multipliers = {}
        multipliers['milli'] = 1
        multipliers['millis'] = 1
        multipliers['tick'] = 10
        multipliers['ticks'] = 10
        multipliers['second'] = 1000
        multipliers['seconds'] = 1000
        multipliers['minute'] = 60000
        multipliers['minutes'] = 60000
        command['multiplier'] = multipliers['second']
        token = self.peek()
        if token in multipliers:
            self.nextToken()
            command['multiplier'] = multipliers[token]
        self.add(command)
        return True

    def r_wait(self, command):
        value = self.getRuntimeValue(command['value']) * command['multiplier'] / 1000.0
        self.easyCoder.timer(value, self.program, self.nextPC())
        return 0

    # while <condition> <statement>
    def k_while(self, command):
        code = self.nextCondition()
        if code == None:
            return None
        # token = self.getToken()
        command['condition'] = code
        test = self.getPC()
        self.addCommand(command)
        # Set up a goto for when the test fails
        fail = self.getPC()
        cmd = {}
        cmd['lino'] = command['lino']
        cmd['domain'] = 'core'
        cmd['keyword'] = 'gotoPC'
        cmd['goto'] = 0
        cmd['debug'] = False
        self.addCommand(cmd)
        # Do the body of the while
        self.nextToken()
        if self.compileOne() == False:
            return False
        # Repeat the test
        cmd = {}
        cmd['lino'] = command['lino']
        cmd['domain'] = 'core'
        cmd['keyword'] = 'gotoPC'
        cmd['goto'] = test
        cmd['debug'] = False
        self.addCommand(cmd)
        # Fixup the 'goto' on completion
        self.getCommandAt(fail)['goto'] = self.getPC()
        return True

    def r_while(self, command):
        test = self.program.condition.testCondition(command['condition'])
        if test:
            self.program.pc += 2
        else:
            self.program.pc += 1
        return self.program.pc

    # write <value> to <file>
    def k_write(self, command):
        if self.peek() == 'line':
            self.nextToken()
            command['line'] = True
        else:
            command['line'] = False
        command['value'] = self.nextValue()
        if self.peek() == 'to':
            self.nextToken()
            if self.nextIsSymbol():
                fileRecord = self.getSymbolRecord()
                if fileRecord['keyword'] == 'file':
                    command['file'] = fileRecord['name']
                    self.add(command)
                    return True
        return False

    def r_write(self, command):
        value = self.getRuntimeValue(command['value'])
        fileRecord = self.getVariable(command['file'])
        file = fileRecord['file']
        if file.mode in ['w', 'w+', 'a+']:
            file.write(value)
            if command['line']:
                file.write('\n')
        return self.nextPC()

    #############################################################################
    # Support functions

    def incdec(self, command, mode):
        symbolRecord = self.getVariable(command['target'])
        if not symbolRecord['valueHolder']:
            FatalError(self.program, f'{symbolRecord["name"]} does not hold a value')
        value = self.getSymbolValue(symbolRecord)
        if mode == '+':
            value['content'] += 1
        else:
            value['content'] -= 1
        self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        value = {}
        value['domain'] = 'core'
        token = self.getToken()
        if self.isSymbol():
            value['name'] = token
            symbolRecord = self.getSymbolRecord()
            keyword = symbolRecord['keyword']
            if keyword == 'module':
                value['type'] = 'module'
                return value

            if keyword in ['variable', 'dictionary']:
                value['type'] = 'symbol'
                return value
            return None

        value['type'] = token

        if token == 'random':
            self.nextToken()
            value['range'] = self.getValue()
            return value

        if token in ['cos', 'sin', 'tan']:
            value['angle'] = self.nextValue()
            if self.nextToken() == 'radius':
                value['radius'] = self.nextValue()
                return value
            return None

        if token in ['now', 'today', 'newline', 'break', 'empty']:
            return value

        if token in ['date', 'encode', 'decode', 'stringify', 'json', 'lowercase', 'hash', 'float', 'integer']:
            value['content'] = self.nextValue()
            return value

        if (token in ['datime', 'datetime']):
            value['type'] = 'datime'
            value['timestamp'] = self.nextValue()
            if self.peek() == 'format':
                self.nextToken()
                value['format'] = self.nextValue()
            else:
                value['format'] = None
            return value

        if token == 'element':
            value['index'] = self.nextValue()
            if self.nextToken() == 'of':
                if self.nextIsSymbol():
                    symbolRecord = self.getSymbolRecord()
                    if symbolRecord['valueHolder']:
                        value['target'] = symbolRecord['name']
                        return value
                self.warning(f'Token \'{self.getToken()}\' does not hold a value')
            return None

        if token == 'property':
            value['name'] = self.nextValue()
            if self.nextToken() == 'of':
                if self.nextIsSymbol():
                    symbolRecord = self.getSymbolRecord()
                    if symbolRecord['valueHolder']:
                        value['target'] = symbolRecord['name']
                        return value
                self.warning(f'Token \'{self.getToken()}\' does not hold a value')
            return None

        if token == 'arg':
            value['content'] = self.nextValue()
            if self.getToken() == 'of':
                if self.nextIsSymbol():
                    symbolRecord = self.getSymbolRecord()
                    if symbolRecord['keyword'] == 'variable':
                        value['target'] = symbolRecord['name']
                        return value
            return None

        if token == 'trim':
            self.nextToken()
            value['content'] = self.getValue()
            return value

        if self.getToken() == 'the':
            self.nextToken()

        token = self.getToken()
        value['type'] = token

        if token == 'elements':
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    value['name'] = self.getToken()
                    return value
            return None

        if token == 'keys':
            if self.nextIs('of'):
                value['name'] = self.nextValue()
                return value
            return None

        if token == 'count':
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    value['name'] = self.getToken()
                    return value
            return None

        if token == 'index':
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    if self.peek() == 'in':
                        value['type'] = 'indexOf'
                        if self.nextIsSymbol():
                            value['target'] = self.getSymbolRecord()['name']
                            return value
                    else:
                        value['name'] = self.getToken()
                        return value
                else:
                    value['value1'] = self.getValue()
                    if self.nextIs('in'):
                        value['type'] = 'indexOf'
                        if self.nextIsSymbol():
                            value['target'] = self.getSymbolRecord()['name']
                            return value
            return None

        if token == 'value':
            value['type'] = 'valueOf'
            if self.nextIs('of'):
                value['content'] = self.nextValue()
                return value
            return None

        if token == 'length':
            value['type'] = 'lengthOf'
            if self.nextIs('of'):
                value['content'] = self.nextValue()
                return value
            return None

        if token in ['left', 'right']:
            value['count'] = self.nextValue()
            if self.nextToken() == 'of':
                value['content'] = self.nextValue()
                return value
            return None

        if token == 'from':
            value['start'] = self.nextValue()
            if self.peek() == 'to':
                self.nextToken()
                value['to'] = self.nextValue()
            else:
                value['to'] = None
            if self.nextToken() == 'of':
                value['content'] = self.nextValue()
                return value

        if token == 'position':
            if self.nextIs('of'):
                value['last'] = False
                if self.nextIs('the'):
                    if self.nextIs('last'):
                        self.nextToken()
                        value['last'] = True
                value['needle'] = self.getValue()
                if self.nextToken() == 'in':
                    value['haystack'] = self.nextValue()
                    return value

        if token == 'message':
            self.nextToken()
            return value

        if token == 'timestamp':
            value['format'] = None
            if self.peek() == 'of':
                self.nextToken()
                value['datime'] = self.nextValue()
                if self.peek() == 'format':
                    self.nextToken()
                    value['format'] = self.nextValue()
            return value

        if token == 'files':
            if self.nextIs('of'):
                value['target'] = self.nextValue()
                return value
            return None

        if token == 'weekday':
            value['type'] = 'weekday'
            return value

        if token == 'error':
            if self.peek() == 'code':
                self.nextToken()
                value['item'] = 'errorCode'
                return value
            if self.peek() == 'reason':
                self.nextToken()
                value['item'] = 'errorReason'
                return value

        if token == 'char':
            value['type'] = 'char'
            value['content'] = self.nextValue()
            return value

        # print(f'Unknown token {token}')
        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        if self.peek() == 'modulo':
            self.nextToken()
            mv = {}
            mv['domain'] = 'core'
            mv['type'] = 'modulo'
            mv['content'] = value
            mv['modval'] = self.nextValue()
            value = mv

        return value

    #############################################################################
    # Value handlers

    def v_boolean(self, v):
        value = {}
        value['type'] = 'boolean'
        value['content'] = v['content']
        return value

    def v_char(self, v):
        content = self.getRuntimeValue(v['content'])
        return {
            "type": "int",
            "content": chr(content)
        }

    def v_cos(self, v):
        angle = self.getRuntimeValue(v['angle'])
        radius = self.getRuntimeValue(v['radius'])
        value = {}
        value['type'] = 'int'
        value['content'] = round(math.cos(angle * 0.01745329) * radius)
        return value

    def v_datime(self, v):
        ts = self.getRuntimeValue(v['timestamp'])
        fmt = v['format']
        if fmt == None:
            fmt = '%b %d %Y %H:%M:%S'
        else:
            fmt = self.getRuntimeValue(fmt)
        value = {}
        value['type'] = 'text'
        value['content'] = datetime.fromtimestamp(ts/1000).strftime(fmt)
        return value

    def v_decode(self, v):
        value = {}
        value['type'] = 'text'
        value['content'] = self.program.decode(v['content'])
        return value

    def v_element(self, v):
        index = self.getRuntimeValue(v['index'])
        target = self.getVariable(v['target'])
        val = self.getSymbolValue(target)
        content = val['content']
        value = {}
        value['type'] = 'int' if isinstance(content, int) else 'text'
        if type(content) == list:
            value['content'] = content[index]
            return value
        lino = self.program.code[self.program.pc]['lino']
        FatalError(self.program, 'Variable "{target}" is not an array')

    def v_elements(self, v):
        value = {}
        value['type'] = 'int'
        value['content'] = self.getVariable(v['name'])['elements']
        return value

    def v_count(self, v):
        variable = self.getVariable(v['name'])
        content = variable['value'][variable['index']]['content']
        value = {}
        value['type'] = 'int'
        value['content'] = len(content)
        return value

    def v_empty(self, v):
        value = {}
        value['type'] = 'text'
        value['content'] = ''
        return value

    def v_encode(self, v):
        value = {}
        value['type'] = 'text'
        value['content'] = self.program.encode(v['content'])
        return value

    def v_error(self, v):
        global errorCode, errorReason
        value = {}
        if v['item'] == 'errorCode':
            value['type'] = 'int'
            value['content'] = errorCode
        elif v['item'] == 'errorReason':
            value['type'] = 'text'
            value['content'] = errorReason
        return value

    def v_stringify(self, v):
        item = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'text'
        try:
            value['content'] = json.dumps(item)
        except Exception as err:
            print(f'Error in item: {item}\n{err}')
            value['content'] = {}
        return value

    def v_json(self, v):
        item = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'object'
        try:
            value['content'] = json.loads(item)
        except Exception as err:
            print(f'Error in item: {item}\n{err}')
            value['content'] = {}
        return value

    def v_from(self, v):
        content = self.getRuntimeValue(v['content'])
        start = self.getRuntimeValue(v['start'])
        to = v['to']
        if not to == None:
            to = self.getRuntimeValue(to)
        value = {}
        value['type'] = 'text'
        try:
            if to == None:
                value['content'] = content[start:]
            else:
                value['content'] = content[start:to]
        except:
            FatalError(self.program, 'Index is not numeric')
        return value

    def v_hash(self, v):
        hashval = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'text'
        value['content'] = hashlib.sha256(hashval.encode('utf-8')).hexdigest()
        return value

    def v_float(self, v):
        val = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'float'
        try:
            value['content'] = float(val)
        except:
            ECRuntimeWarning(self.program, f'Value cannot be parsed as floating-point')
            value['content'] = 0.0
        return value

    def v_index(self, v):
        value = {}
        value['type'] = 'int'
        value['content'] = self.getVariable(v['name'])['index']
        return value

    def v_indexOf(self, v):
        value1 = v['value1']
        target = self.getVariable(v['target'])
        try:
            index = target['value'].index(value1)
        except:
            index = -1
        value = {}
        value['type'] = 'int'
        value['content'] = index
        return value

    def v_integer(self, v):
        val = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'int'
        value['content'] = int(val)
        return value

    def v_keys(self, v):
        value = {}
        value['type'] = 'int'
        value['content'] = list(self.getRuntimeValue(v['name']).keys())
        return value

    def v_left(self, v):
        content = self.getRuntimeValue(v['content'])
        count = self.getRuntimeValue(v['count'])
        value = {}
        value['type'] = 'text'
        value['content'] = content[0:count]
        return value

    def v_lengthOf(self, v):
        content = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'int'
        value['content'] = len(content)
        return value

    def v_lowercase(self, v):
        value = {}
        value['type'] = 'text'
        value['content'] = v['content']['content'].lower()
        return value

    def v_modulo(self, v):
        val = self.getRuntimeValue(v['content'])
        modval = self.getRuntimeValue(v['modval'])
        value = {}
        value['type'] = 'int'
        value['content'] = val % modval
        return value

    def v_newline(self, v):
        value = {}
        value['type'] = 'text'
        value['content'] = '\n'
        return value

    def v_now(self, v):
        value = {}
        value['type'] = 'int'
        value['content'] = getTimestamp(time.time())
        return value

    def v_position(self, v):
        needle = self.getRuntimeValue(v['needle'])
        haystack = self.getRuntimeValue(v['haystack'])
        last = v['last']
        value = {}
        value['type'] = 'int'
        value['content'] = haystack.rfind(needle) if last else haystack.find(needle)
        return value

    def v_property(self, v):
        name = self.getRuntimeValue(v['name'])
        target = self.getVariable(v['target'])
        targetSymbol = self.getSymbolValue(target)
        content = targetSymbol['content']

        value = {}
        if content != None and name in content:
            value['content'] = content.get(name)
            if isinstance(v, numbers.Number):
                value['type'] = 'int'
            else:
                value['type'] = 'text'
        else:
            tn = target['name']
            value['type'] = 'text'
            value['content'] = ''
        return value

    def v_random(self, v):
        range = self.getRuntimeValue(v['range'])
        value = {}
        value['type'] = 'int'
        value['content'] = randrange(range)
        return value

    def v_right(self, v):
        content = self.getRuntimeValue(v['content'])
        count = self.getRuntimeValue(v['count'])
        value = {}
        value['type'] = 'text'
        value['content'] = content[-count:]
        return value

    def v_sin(self, v):
        angle = self.getRuntimeValue(v['angle'])
        radius = self.getRuntimeValue(v['radius'])
        value = {}
        value['type'] = 'int'
        value['content'] = round(math.sin(angle * 0.01745329) * radius)
        return value

    def v_tan(self, v):
        angle = self.getRuntimeValue(v['angle'])
        radius = self.getRuntimeValue(v['radius'])
        value = {}
        value['type'] = 'int'
        value['content'] = round(math.tan(angle * 0.01745329) * radius)
        return value

    def v_timestamp(self, v):
        value = {}
        value['type'] = 'int'
        fmt = v['format']
        if fmt == None:
            value['content'] = int(time.time())
        else:
            fmt = self.getRuntimeValue(fmt)
            dt = self.getRuntimeValue(v['datime'])
            spec = datetime.strptime(dt, fmt)
            t = datetime.now().replace(hour=spec.hour, minute=spec.minute, second=spec.second, microsecond=0)
            value['content'] = int(t.timestamp())
        return value

    def v_today(self, v):
        value = {}
        value['type'] = 'int'
        value['content'] = int(datetime.combine(datetime.now().date(),datetime.min.time()).timestamp())*1000
        return value

    def v_symbol(self, symbolRecord):
        result = {}
        if symbolRecord['keyword'] == 'variable':
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

    def v_valueOf(self, v):
        v = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'int'
        value['content'] = int(v)
        return value

    def v_files(self, v):
        v = self.getRuntimeValue(v['target'])
        value = {}
        value['type'] = 'text'
        value['content'] = os.listdir(v)
        return value

    def v_trim(self, v):
        v = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'text'
        value['content'] = v.strip()
        return value

    def v_weekday(self, v):
        value = {}
        value['type'] = 'int'
        value['content'] = datetime.today().weekday()
        return value

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        token = self.getToken()
        if token == 'not':
            condition['type'] = 'not'
            condition['value'] = self.nextValue()
            return condition
        elif token == 'file':
            path = self.nextValue()
            if self.peek() == 'exists':
                condition['type'] = 'exists'
                condition['path'] = path
                self.nextToken()
                return condition
            return None
        elif token in ['disabled', 'enabled']:
            condition['type'] = token
            self.nextToken()
            return condition
        value = self.getValue()
        if value == None:
            return None
        condition['value1'] = value
        token = self.peek()
        condition['type'] = token
        if token == 'includes':
            condition['value2'] = self.nextValue()
            return condition
        elif token == 'has':
            token = self.nextToken()
            if self.nextIs('property'):
                property = self.nextValue()
                condition['type'] = 'property'
                condition['property'] = property
                return condition
            return None
        elif token == 'is':
            token = self.nextToken()
            if self.peek() == 'not':
                self.nextToken()
                condition['negate'] = True
            else:
                condition['negate'] = False
            token = self.nextToken()
            condition['type'] = token
            if token in ['numeric', 'even', 'odd', 'boolean', 'empty']:
                return condition
            if token in ['greater', 'less']:
                if self.nextToken() == 'than':
                    condition['value2'] = self.nextValue()
                    return condition
            condition['type'] = 'is'
            condition['value2'] = self.getValue()
            return condition
        elif condition['value1']:
            # It's a boolean if
            condition['type'] = 'boolean'
            return condition

        self.warning(f'I can\'t get a conditional:')
        return None

    def isNegate(self):
        token = self.getToken()
        if token == 'not':
            self.nextToken()
            return True
        return False

    #############################################################################
    # Condition handlers

    def c_boolean(self, condition):
        value = self.getRuntimeValue(condition['value1'])
        if type(value) == bool:
            return value;
        return False

    def c_numeric(self, condition):
        return isinstance(self.getRuntimeValue(condition['value1']), int)

    def c_not(self, condition):
        return not self.getRuntimeValue(condition['value1'])

    def c_even(self, condition):
        return self.getRuntimeValue(condition['value1']) % 2 == 0

    def c_odd(self, condition):
        return self.getRuntimeValue(condition['value1']) % 2 == 1

    def c_is(self, condition):
        comparison = self.program.compare(condition['value1'], condition['value2'])
        return comparison != 0 if condition['negate'] else comparison == 0

    def c_greater(self, condition):
        comparison = self.program.compare(condition['value1'], condition['value2'])
        return comparison <= 0 if condition['negate'] else comparison > 0

    def c_less(self, condition):
        comparison = self.program.compare(condition['value1'], condition['value2'])
        return comparison >= 0 if condition['negate'] else comparison < 0

    def c_includes(self, condition):
        value1 = self.getRuntimeValue(condition['value1'])
        value2 = self.getRuntimeValue(condition['value1'])
        return value1 in value2

    def c_empty(self, condition):
        value = self.getRuntimeValue(condition['value1'])
        if value == None:
            comparison = True
        else:
            comparison = len(value) == 0
        return not comparison if condition['negate'] else comparison

    def c_exists(self, condition):
        path = self.getRuntimeValue(condition['path'])
        return os.path.exists(path)

    def c_property(self, condition):
        property = self.getRuntimeValue(condition['property'])
        value = self.getRuntimeValue(condition['value1'])
        return property in value
    
    def c_disabled(self, condition):
        return not self.program.enabled
    
    def c_enabled(self, condition):
        return self.program.enabled
