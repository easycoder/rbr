import asyncio,hardware,gc
import uaiohttpclient as aiohttp

async def httpGET(url):
    gc.collect()
    hardware.setLED(True)
    resp = await aiohttp.request("GET", url)
    response=(await resp.read()).decode()
    hardware.setLED(False)
    return response
