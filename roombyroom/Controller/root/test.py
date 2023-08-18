#! /bin/python

import requests

try:
	response = requests.get('http://172.24.1.90/on?type=r1&id=101', auth = ('user', 'pass'), timeout=5)
	# print(f'Code: {response.status_code}')
	# if response.status_code >= 400:
	# 	errorCode = response.status_code
	# 	errorReason = response.reason
	# 	if command['or'] != None:
	# 		return command['or']
	# 	else:
	# 		print('RuntimeError')
	# 		RuntimeError(self.program, f'Error code {errorCode}: {errorReason}')
except Exception as e:
	print(f'Exception: {e}')

print(f'Response: {response.text}')
