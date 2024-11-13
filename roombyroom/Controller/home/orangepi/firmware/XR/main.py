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

errorCount=0

if fileExists('debug'):
    import debug
    debug.run()

elif fileExists('config.json'):
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
            print(f'Error ({errorCount})',e)
            errorCount+=1
            if errorCount>20:
                f = open('update', 'w')
                f.write('1')
                f.close()
                machine.reset()
else:
    print('main: Run unconfigured')
    time.sleep(5)
    import unconfigured
    unconfigured.run()

