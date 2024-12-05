from incoming import Devices

if __name__ == "__main__":
    devices=Devices()
    devices.addDevice('Room1:100')
    devices.addDevice('Room2:200')
    devices.addDevice('Room3:300')
    print(devices.toString())
    devices.replace('Room1','Room1:1010')
    devices.replace('Room4','Room4:400')
    devices.replace('Room2','Room2:205')
    print(devices.toString())


