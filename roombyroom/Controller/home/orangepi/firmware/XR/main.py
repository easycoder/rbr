import os,machine

print('Running main.py')

###################################################################################
# Select the operating mode

def fileExists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

if fileExists('config.json'):
    if fileExists('update'):
        f = open('update','r')
        value=f.read()
        f.close()
        try:
            import updater
            updater.run(value)
        except:
            machine.reset()

    else:
        try:
            import configured
            configured.run()
        except:
            f = open('update', 'w')
            f.write('1')
            f.close()
            machine.reset()
else:
    import unconfigured
    unconfigured.run()
