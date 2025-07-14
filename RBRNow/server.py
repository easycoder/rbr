import asyncio

class Server():
    
    def __init__(self,config):
        self.config=config

    async def respond(self,response,writer):
        try:
            responseBytes = str(response).encode()
            await writer.awrite(b'HTTP/1.0 200 OK\r\n')
            await writer.awrite(b'Content-Type: text/plain\r\n')
            await writer.awrite(f'Content-Length: {len(responseBytes)}\r\n'.encode())
            await writer.awrite(b'\r\n')
            await writer.awrite(str(response).encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f'server.respond: {e}')
        return None

    async def sendDefaultResponse(self,writer):
        ms='M' if self.config.isMaster() else 'S'
        mac=self.config.getMAC()
        espComms=self.config.getESPComms()
        response=f'{mac} {ms} {self.config.getName()} {self.config.getUptime()}'
        if ms=='S': response=f'{response} {espComms.getRSS(mac)}'
        await self.respond(response,writer)
        return None

    async def handleClient(self,reader, writer):
        try:
            handler=self.config.getHandler()
            request = await reader.read(1024)
            request = request.decode().split(' ')
            if len(request) > 1:
                peer = None
                msg=None
                ack=False
#                print('handleClient:',request[1])
                request=request[1].split('?')
                if len(request)<2:
                    return await self.sendDefaultResponse(writer)
                items=request[1].split('&')
                for n in range(0, len(items)):
                    item = items[n].split('=')
                    if len(item)<2 or item[0]=='channel':
                        response=handler.handleMessage(items[n])
                        return await self.respond(response,writer)
                    if item[0]=='mac': peer=item[1]
                    elif item[0]=='msg': espmsg=item[1]
                if peer==None:
                    response=handler.handleMessage(request)
                else:
                    if peer==self.config.getMAC():
                        # This is for the master (me)
                        response=handler.handleMessage(espmsg)
                    else:
                        # This is for one of my peers
                        if espmsg!=None:
                            response=await(self.messagePeer(peer,espmsg))
    #                        print('sta response:',response)
                        else:
                            print('Can\'t send message')
                            response='Can\'t send message'
            else: response=''
            self.config.kickWatchdog()
            return await self.config.respond(response,writer)
        except Exception as e:
            print("Error in client handler:", e)
        finally:
            await writer.wait_closed()

    async def messagePeer(self,peer,espmsg):
        response=await self.config.send(peer,espmsg)
        return response

    def startup(self):
        self.server=asyncio.create_task(asyncio.start_server(self.handleClient,'0.0.0.0',80))
