import hardware,machine,time

def restart(message):
    if message==None:
        print('Restart')
    else:
        print(message)
        hardware.writeFile('state',message)
    time.sleep(1)
    machine.reset()
    