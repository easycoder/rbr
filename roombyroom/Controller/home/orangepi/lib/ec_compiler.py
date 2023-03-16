from ec_classes import Token, CompileError
from ec_value import Value
from ec_condition import Condition

class Compiler:

	def __init__(self, program):
		self.program = program
		self.domains = self.program.domains
		self.value = Value(self)
		self.condition = Condition(self)
		self.marker = 0
		self.script = self.program.script
		self.tokens = self.script.tokens
		self.symbols = self.program.symbols
		self.code = self.program.code
		self.warnings = []
		self.program.compiler = self
		self.addCommand = self.program.add

	def getPC(self):
		return len(self.program.code)

	def getIndex(self):
		return self.index

	# Move the index along
	def next(self):
		self.index += 1

	# Get the current token
	def getToken(self):
		if self.index >= len(self.tokens):
			CompileError(self.program, 'Premature end of script')
		return self.tokens[self.index].token

	# Get the next token
	def nextToken(self):
		self.index += 1
		return self.getToken()

	def peek(self):
		try:
			return self.tokens[self.index + 1].token
		except:
			return None

	# Get a value
	def getValue(self):
		return self.value.compileValue()

	# Get the next value
	def nextValue(self):
		self.index += 1
		return self.value.compileValue()

	# Get a constant
	def getConstant(self, token):
		self.index += 1
		return self.value.compileConstant(token)

	# Get a condition
	def getCondition(self):
		return self.condition.compileCondition()

	# Get the next condition
	def nextCondition(self):
		self.index += 1
		return self.condition.compileCondition()

	def tokenIs(self, value):
		return self.getToken() == value

	def nextIs(self, value):
		return self.nextToken() == value

	def getCommandAt(self, pc):
		return self.program.code[pc]

	def isSymbol(self):
		token=self.getToken()
		try:
			self.symbols[token]
		except:
			return False
		return True

	def nextIsSymbol(self):
		self.next()
		return self.isSymbol()

	def rewindTo(self, index):
		self.index = index

	def getLino(self):
		if self.index >= len(self.tokens):
			return 0
		return self.tokens[self.index].lino

	def warning(self, message):
		program = self.program
		lino = self.tokens[self.index].lino
		script = program.script.lines[lino].strip()
		self.warnings.append(f'Compile warning in {program.name} at line {lino + 1} ({script}): {message}')

	def showWarnings(self):
		if len(self.warnings) > 0:
			print('Warnings:')
			for warning in self.warnings:
				print(warning)

	def getSymbolRecord(self):
		token = self.getToken()
		symbol = self.symbols[token]
		if symbol != None:
			symbolRecord = self.code[symbol]
			symbolRecord['used'] = True
			return symbolRecord
		return None

	def compileLabel(self, command):
		return self.compileSymbol(command, None, self.getToken())

	def compileVariable(self, command, keyword, valueHolder=False):
		return self.compileSymbol(command, keyword, self.nextToken(), valueHolder)

	def compileSymbol(self, command, keyword, name, valueHolder=False):
		try:
			v = self.symbols[name]
		except:
			v = None
		if v:
			CompileError(self.program.compiler, f'Duplicate symbol name "{name}"')
			return False
		self.symbols[name] = self.getPC()
		command['type'] = 'symbol'
		command['keyword'] = keyword
		command['name'] = name
		command['elements'] = 1
		command['index'] = 0
		command['value'] = [None]
		command['valueHolder'] = valueHolder
		command['used'] = False
		command['debug'] = False
		self.addCommand(command)
		return True

	# Compile the current token
	def compileToken(self):
		token = self.getToken()
		# print(f'Compile {token}')
		if not token:
			return False
		mark = self.getIndex()
		for domain in self.domains:
			handler = domain.keywordHandler(token)
			if handler:
				command = {}
				command['domain'] = domain.getName()
				command['lino'] = self.tokens[self.index].lino
				command['keyword'] = token
				command['type'] = None
				command['debug'] = True
				result = handler(command)
				if result:
					return result
				else:
					self.rewindTo(mark)
			else:
				self.rewindTo(mark)
		CompileError(self, f'No handler found for "{token}"')
		return False

	# Compile a single command
	def compileOne(self):
		keyword = self.getToken()
		if not keyword:
			return False
		# print(f'Compile keyword "{keyword}"')
		if keyword.endswith(':'):
			command = {}
			command['domain'] = None
			command['lino'] = self.tokens[self.index].lino
			return self.compileLabel(command)
		else:
			return self.compileToken()

	# Compile from a specific PC address
	def compileFrom(self, index, parent, stopOn):
		self.index = index
		self.parent = parent
		while True:
			token = self.tokens[self.index]
#			keyword = token.token
#			line = self.script.lines[token.lino]
#			print(f'{keyword} - {line}')
			if self.compileOne() == True:
				if self.index == len(self.tokens) - 1:
					return True
				token = self.nextToken()
				if token in stopOn:
					return True
			else:
				return False

	def compileFromCurrentIndex(self, stopOn):
		return self.compileFrom(self.getIndex(), None, stopOn)

	# Compile the script
	def compileScript(self, parent):
		exports = self.program.exports
		if (exports):
			for export in exports:
				name = export['name']
				self.symbols[name] = self.getPC()
				self.addCommand(export)
		return self.compileFrom(0, parent, [])
