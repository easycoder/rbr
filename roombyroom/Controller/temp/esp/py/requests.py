import urequests as requests
import ujson

def post(request_url, a, b):
    if not wifi.isconnected():
        return ''
    post_data = ujson.dumps({ "a": a, "b": b})
    headers = { "content-type": 'application/json; charset=utf-8', "devicetype": '1'}
    res = requests.post(request_url, headers, data = post_data)
    return res.text

class Session():
    pass