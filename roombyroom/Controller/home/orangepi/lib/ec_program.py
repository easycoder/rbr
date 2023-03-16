import time, threading
from copy import copy
from collections import deque
from ec_main import Main
from ec_classes import Script, Token, CompileError, FatalError
from ec_compiler import Compiler

class Program:

	def __init__(self, easyCoder, source, domains, parent = None, exports = None):

		# print(f'Run {source}')
		self.easyCoder = easyCoder
		self.domains = []
		self.parent = parent
		self.exports = exports
		self.domainIndex = {}
		self.name = '<anon>'
		self.code = []
		self.symbols = {}
		self.onError = 0
		self.pc = 0
		self.debugStep = False
		self.debugHook = None
		self.timerHook = None
		self.script = Script(source)
		self.stack = []
		self.compiler = Compiler(self)
		self.value = self.compiler.value
		self.condition = self.compiler.condition
		for domain in domains:
			handler = domain(self.compiler)
			self.domains.append(handler)
			self.domainIndex[handler.getName()] = handler
		self.queue = deque()
		self.enabled = True
		self.running = True

		startCompile = time.time()
		self.tokenise(self.script)
		if self.compiler.compileScript(parent):
			finishCompile = time.time()
			s = len(self.script.lines)
			t = len(self.script.tokens)
			print(f'Compiled {self.name}: {s} lines ({t} tokens) in ' +
				f'{round((finishCompile - startCompile) * 1000)} ms')
			for name in self.symbols.keys():
				record = self.code[self.symbols[name]]
				if name[-1] != ':' and not record['used']:
					print(f'Variable "{name}" not used')
			if parent == None:
				print(f'Run {self.name}')
				easyCoder.run(self, 0)
		self.compiler.showWarnings()

	# Add a command to the code list
	def add(self, command):
		self.code.append(command)

	def getSymbolRecord(self, name):
		try:
			target = self.code[self.symbols[name]]
		except:
			FatalError(self.compiler.program, f'Unknown symbol \'{name}\'')
			return None

		return target

	def doValue(self, value):
		if value == None:
			CompileError(self.compiler, f'Undefined value (variable not initialized?)')

		result = {}
		valType = value['type']
		if valType in ['boolean', 'int', 'text', 'object']:
			result = value
		elif valType == 'cat':
			content = ''
			for part in value['parts']:
				val = self.doValue(part)
				if val == None:
					return None
				if val != '':
					val = str(val['content'])
					if val == None:
						return None
					content += val
			result['type'] = 'text'
			result['content'] = content
		elif valType == 'symbol':
			name = value['name']
			symbolRecord = self.getSymbolRecord(name)
			if symbolRecord['value'] == [None]:
				FatalError(self.compiler.program, f'Variable "{name}" has no value')
				return None
			handler = self.domainIndex[symbolRecord['domain']].valueHandler('symbol')
			result = handler(symbolRecord)
		else:
			# Call the given domain to handle a value
			domain = self.domainIndex[value['domain']]
			handler = domain.valueHandler(value['type'])
			if handler:
				result = handler(value)

		return result

	def constant(self, content, numeric):
		result = {}
		result['type'] = 'int' if numeric else 'text'
		result['content'] = content
		return result

	def evaluate(self, value):
		if value == None:
			result = {}
			result['type'] = 'text'
			result['content'] = ''
			return result

		return self.doValue(value)

	def getValue(self, value):
		return self.evaluate(value).content

	def getRuntimeValue(self, value):
		v = self.evaluate(value)
		if v != None and v != '':
			try:
				content = v['content']
			except:
				FatalError(self, 'No content')
			if v['type'] == 'boolean':
				return True if content else False
			if v['type'] in ['int', 'float', 'text', 'object']:
				return content
			return ''
		return None

	def getSymbolValue(self, symbolRecord):
		value = copy(symbolRecord['value'][symbolRecord['index']])
		return value

	def putSymbolValue(self, symbolRecord, value):
		symbolRecord['value'][symbolRecord['index']] = value

	def encode(self, value):
		return value

	def decode(self, value):
		return value

	# Tokenise the script
	def tokenise(self, script):
		index = 0
		lino = 0
		for line in script.lines:
			length = len(line)
			token = ''
			inSpace = True
			n = 0
			while n < length:
				c = line[n]
				if len(c.strip()) == 0:
					if (inSpace):
						n += 1
						continue
					script.tokens.append(Token(lino, token))
					index += 1
					token = ''
					inSpace = True
					n += 1
					continue
				inSpace = False
				if c == '`':
					m = n
					n += 1
					while n < len(line) - 1:
						if line[n] == '`':
							break
						n += 1
					# n += 1
					token = line[m:n+1]
				elif c == '!':
					break
				else:
					token += c
				n += 1
			if len(token) > 0:
				script.tokens.append(Token(lino, token))
				index += 1
			lino += 1
		return

	def nonNumericValueError(self):
		CompileError(self.compiler, 'Non-numeric value')

	def variableDoesNotHoldAValueError(self, name):
		raise CompileError(self.compiler, f'Variable "{name}" does not hold a value')

	def compare(self, value1, value2):
		# print(f'Compare {value1} with {value2}')
		val1 = self.evaluate(value1)
		val2 = self.evaluate(value2)
		if val1 == None or val2 == None:
			return 0
		v1 = val1['content']
		v2 = val2['content']
		if type(v1) == dict or type(v2) == dict:
			FatalError(self, f'Can only compare strings or integers')
		if v1 == None and v2 != None or v1 != None and v2 == None:
			return 0
		if v1 != None and val1['type'] == 'int':
			if not val2['type'] == 'int':
				if type(v2) is str:
					try:
						v2 = int(v2)
					except:
						lino = self.code[self.pc]['lino'] + 1
						FatalError(self, f'Line {lino}: \'{v2}\' is not an integer')
		else:
			if val2['type'] == str and v2 != None and val2['type'] == 'int':
				v2 = str(v2)
			if v1 == None:
				v1 = ''
			if v2 == None:
				v2 = ''
		if v1 > v2:
			return 1
		if v1 < v2:
			return -1
		return 0

	def nextPC(self):
		return self.pc + 1
