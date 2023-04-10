class CompileError():
	def __init__(self, compiler, message):
		program = compiler.program
		lino = compiler.tokens[compiler.index].lino
		script = program.script.lines[lino].strip()
		compiler.showWarnings()
		print(f'Compile error in {program.name} at line {lino + 1} ({script}): {message}')
		raise SystemExit

class FatalError:
	def __init__(self, program, message):
		if program == None:
			print(f'Runtime Error: {message}')
			raise SystemExit
		else:
			code = program.code[program.pc]
			lino = code['lino']
			script = program.script.lines[lino].strip()
			print(f'Runtime Error in {program.name} at line {lino + 1} ({script}): {message}')
			raise SystemExit

class ECRuntimeWarning:
	def __init__(self, program, message):
		if program == None:
			print(f'Warning: {message}')
		else:
			code = program.code[program.pc]
			lino = code['lino']
			script = program.script.lines[lino].strip()
			print(f'Runtime warning in {program.name} at line {lino + 1} ({script}): {message}')

class Script:
	def __init__(self, source):
		self.lines = source.splitlines()
		self.tokens = []

class Token:
	def __init__(self, lino, token):
		self.lino = lino
		self.token = token
