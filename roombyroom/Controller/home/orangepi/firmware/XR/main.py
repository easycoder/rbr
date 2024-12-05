import os,time,state

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
            time.sleep(2)
            import updater
            updater.run(value)
        except Exception as e:
            state.restart(str(e))

    else:
        try:
            import configured
            print('main: Run configured')
            time.sleep(2)
            configured.run()
        except Exception as e:
            state.restart(str(e))

else:
    print('main: Run unconfigured')
    time.sleep(2)
    import unconfigured
    unconfigured.run()

