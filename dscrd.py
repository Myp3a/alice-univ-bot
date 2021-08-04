import asyncio
import websockets
import json
import aiohttp
from debugger import dbg

debug = False

class Event:
    def __init__(self,data):
        self.op = data['op']
        self.d = data.get('d',None)
        self.s = data.get('s',None)
        self.t = data.get('t',None)

class Heartbeater:
    def __init__(self,bot):
        self.bot = bot
    
    async def start(self):
        self.bot.loop.create_task(self.worker())
    
    async def worker(self):
        while True:
            print('hb')
            hb_str = json.dumps({"op": 1,"d":self.bot.s})
            self.bot.loop.create_task(self.bot.ws.send(hb_str))
            await asyncio.sleep(self.bot.hb_intrv/1000)

class User:
    def __init__(self,data):
        self.uid = data['id']
        self.username = data['username']

class Message:
    def __init__(self,data):
        self.attachments = data['attachments']
        self.author = User(data['author'])
        self.channel_id = data['channel_id']
        self.content = data['content']
        self.id = data['id']
        self.mentions = data['mentions']
        self.referenced_message = data['referenced_message']
    
class Bot:
    def __init__(self,token):
        self.token = token
        self.d = None
        self.hb_intrv = None
        self.s = None
        self.sess_id = None

    def start(self,bg=True):
        self.loop = asyncio.get_event_loop()
        if bg:
            self.loop.create_task(self.connect())
        else:
            self.loop.run_until_complete(self.connect())

    def event(self,func):
        setattr(self,func.__name__.split('___')[0],func)
        return func

    async def on_message(self,msg):
        pass     
    
    async def send_identify(self):
        data = {
            "op": 2,
            "d": {
                "token": self.token,
                "intents": 13824,
                "properties": {
                    "$os": "linux",
                    "$browser": "Alice",
                    "$device": "Alice"
                }
            }
        }
        await self.ws.send(json.dumps(data))
    
    async def connect(self):
        while not self.loop.is_closed():
            try:
                async with websockets.connect('wss://gateway.discord.gg/?v=8&encoding=json') as self.ws:
                    hello = Event(json.loads(await self.ws.recv()))
                    self.hb_intrv = hello.d['heartbeat_interval']
                    beater = Heartbeater(self)
                    await beater.start()
                    await self.send_identify()
                    async for wsmsg in self.ws:
                        json_msg = json.loads(wsmsg)
                        if debug:
                            dbg(json_msg,'json_msg')
                        wsmsg = Event(json_msg)
                        if wsmsg.s is not None:
                            self.s = wsmsg.s
                        if wsmsg.op == 0:
                            print('Event')
                            if wsmsg.t == 'READY':
                                self.sess_id = wsmsg.d['session_id']
                            elif wsmsg.t == 'MESSAGE_CREATE':
                                msg = Message(wsmsg.d)
                                await self.on_message(msg)
                        elif wsmsg.op == 11:
                            print('hb_back')
            except:
                #raise
                print(f'{"FUCK"*10}\n'*15)
    async def send(self,channel,text):
        async with aiohttp.ClientSession() as sess:
            async with sess.post(f'https://discord.com/api/channels/{channel}/messages',headers={'Authorization':f'Bot {self.token}'},data={'content':text}) as req:
                await req.read()
    

        