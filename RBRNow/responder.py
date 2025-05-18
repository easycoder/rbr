import asyncio

class Responder():
    
    def __init__(self,config):
        self.config=config

    async def respond(self,response,writer):
#        print('Responder:',response)
        responseBytes = str(response).encode()
        await writer.awrite(b"HTTP/1.0 200 OK\r\n")
        await writer.awrite(b"Content-Type: text/plain\r\n")
        await writer.awrite(f"Content-Length: {len(responseBytes)}\r\n".encode())
        await writer.awrite(b"\r\n")
        await writer.awrite(str(response).encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        return None

    async def sendDefaultResponse(self,writer):
        ms='M' if self.config.isMaster() else 'S'
        response=f'{self.config.getMAC()} {ms} {self.config.getName()}'
        return await self.respond(response,writer)
