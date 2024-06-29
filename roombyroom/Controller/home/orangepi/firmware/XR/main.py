import os

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
        import updater
        f = open('update','r')
        value=f.read()
        f.close()
        updater.run(value)
    else:
        import configured
        configured.run()
else:
    import unconfigured
    unconfigured.run()

