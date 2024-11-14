import os,machine,time

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
            print('main: Update to version',value)
            time.sleep(5)
            import updater
            updater.run(value)
        except:
            machine.reset()

    else:
        try:
            print('main: Run configured')
            time.sleep(5)
            import configured
            configured.run()
        except Exception as e:
            print('Error:',e)
            machine.reset()
else:
    print('main: Run unconfigured')
    time.sleep(5)
    import unconfigured
    unconfigured.run()

