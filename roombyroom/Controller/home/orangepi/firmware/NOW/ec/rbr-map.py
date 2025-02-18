from easycoder import Handler, FatalError, math

class Map(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'map'

    #############################################################################
    # Keyword handlers

    def k_map(self, command):
        return self.compileVariable(command, False)

    def r_map(self, command):
        return self.nextPC()

    # load {map} from {json value}
    def k_load(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['keyword'] == 'map':
                command['name'] = symbolRecord['name']
                if self.nextIs('from'):
                    command['value'] = self.nextValue()
                    self.add(command)
                    return True
        return False

    def r_load(self, command):
        mapRecord = self.getVariable(command['name'])
        value = self.getRuntimeValue(command['value'])
        mapRecord['map'] = value
        return self.nextPC()

    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        value = {}
        value['domain'] = self.getName()
        token = self.getToken()
        if self.isSymbol():
            value['name'] = token
            symbolRecord = self.getSymbolRecord()
            keyword = symbolRecord['keyword']
            if keyword in ['map', 'profile', 'room', 'calendar']:
                value['type'] = 'symbol'
                value['keyword'] = keyword
                return value
            return None

        value['type'] = token

        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

    #############################################################################
    # Value handlers

    # This is used by the expression evaluator to get the value of a symbol
    def v_symbol(self, v):
        symbolRecord = self.getVariable(v['name'])
        if symbolRecord['keyword'] == 'map':
            value = {}
            value['type'] = 'text'
            value['content'] = symbolRecord['map']
            return value
        return None

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers
