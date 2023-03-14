import threading
from collections import deque

class Main:

	def __init__(self):
		self.queue = deque()
		self.running = True

	# Queue and run
	def run(self, program, pc, queue = True):
		# print(f'Run {program.name} from {pc}')
		self.queue.append({"program": program, "pc": pc})
		if not queue:
			print(f'Program {program.name} queued')
			return

		while len(self.queue) and self.running:
			item = self.queue.popleft()
			program = item['program']
			program.pc = item['pc']
			# print(f'Run program {program.name} from {program.pc}')
			while len(program.code) > program.pc:
				command = program.code[program.pc]
				domainName = command['domain']
				if domainName == None:
					program.pc += 1
				else:
					keyword = command['keyword']
					if program.debugStep and command['debug']:
						lino = command['lino'] + 1
						line = program.script.lines[command['lino']].strip()
						message = f'{program.name}: Line {lino}: PC: {program.pc} {domainName}:{keyword}:  {line}'
						print(message)
						if program.debugHook:
							program.debugHook(message)
					domain = program.domainIndex[domainName]
					handler = domain.runHandler(keyword)
					if handler:
						command['program'] = program
						program.pc = handler(command)
						if program.pc == 0 or program.pc >= len(program.code):
							# print(f'{program.name} stopped')
							break
				if program.pc < 0:
					print(f'{program.name} aborted')
					return -1
		# print('Queue empty')
		return program.pc

	# Run a timer
	def timer(self, value, program, pc):
		threading.Timer(value, lambda: (self.run(program, pc))).start()