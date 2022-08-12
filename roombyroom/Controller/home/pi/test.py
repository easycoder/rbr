import pytz, time
from datetime import datetime

def getTimestamp(t):
    tz = pytz.timezone('Europe/London')
    dt = datetime.fromtimestamp(t)
    return int(t) + tz.dst(dt).seconds

print(getTimestamp(time.time()))
