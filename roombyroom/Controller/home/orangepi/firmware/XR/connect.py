import network
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect('PLUSNET-N7C3KC','Ur4nXVQKJPrQcJ')
sta_if.isconnected()
station=sta_if.ifconfig()
print('Connected to',station)
