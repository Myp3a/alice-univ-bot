import asyncio
import aiohttp
import json
import random
from debugger import dbg

debug = False

class Bot:
    def __init__(self,token):
        self.token = token
        self.server = None
        self.key = None
        self.ts = None
        self.group_id = 203390587
        self.wait = 10
        self.v = "5.130"

    async def on_message(self,msg):
        pass

    async def on_msg_event(self,event):
        pass

    def event(self,func):
        setattr(self,func.__name__.split('___')[0],func)
        return func

    def start(self,bg=True):
        self.loop = asyncio.get_event_loop()
        if bg:
            self.loop.create_task(self.connect())
        else:
            self.loop.run_until_complete(self.connect())
    
    async def connect(self):
        while not self.loop.is_closed():
            try:
                async with aiohttp.ClientSession() as sess:
                    async with sess.get('https://api.vk.com/method/groups.getLongPollServer',params={'group_id':self.group_id,'access_token':self.token,'v':self.v}) as LPserv:
                        LPserv_data = await LPserv.json()
                        self.server = LPserv_data['response']['server']
                        self.key = LPserv_data['response']['key']
                        self.ts = LPserv_data['response']['ts']
                    while True:
                        async with sess.get(f'{self.server}',params={'act':'a_check','key':self.key,'ts':self.ts,'wait':self.wait}) as resp:
                            resp = Response(await resp.json())
                            if resp.ts is not None:
                                self.ts = resp.ts
                            print(resp.updates)
                            if resp.updates is not None:
                                for upd in resp.updates:
                                    ev = Event(upd)
                                    if ev.type == 'message_new':
                                        print(ev.object)
                                        msg = Message(ev.object['message'])
                                        #if msg.payload is not None:
                                        #    msgev = Msg_Event({'user_id':msg.author.uid,'peer_id':msg.source,'payload':msg.payload,'conversation_message_id':msg.conversation_message_id})
                                        #    await self.on_msg_event(msgev)
                                        #else:
                                        await self.on_message(msg)
                                    if ev.type == 'message_event':
                                        print(ev.object)
                                        msgev = Msg_Event(ev.object)
                                        await self.on_msg_event(msgev)
            except:
                #raise
                print(f'{"CRAP"*10}\n'*15)

    async def send(self,chat,text,reply,buttons=None):
        try:
            async with aiohttp.ClientSession() as sess:
                data = {'peer_id':chat,'message':reply+',\n'+text,'random_id':random.randint(-2000000000,2000000000),'access_token':self.token,'v':self.v}
                print(data)
                if buttons is not None:
                    kbd = {"one_time":False,"buttons":[[]],"inline":True}
                    for button in buttons:
                        kbd["buttons"][0].append({'action':{'type':'callback','label':button.text,'payload':button.callback}})
                        data['keyboard'] = json.dumps(kbd)
                async with sess.post('https://api.vk.com/method/messages.send',params=data) as req:
                    print(await req.text())
        except:
            raise

    async def answer_event(self,event,data):
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post('https://api.vk.com/method/messages.sendMessageEventAnswer',params={'event_id':event.event_id,'user_id':event.user_id,'peer_id':event.peer_id,'event_data':data,'access_token':self.token,'v':self.v}) as req:
                    print(await req.text())
        except:
            raise
    
    async def edit(self,chat,text,reply,msgid,buttons=None):
        try:
            async with aiohttp.ClientSession() as sess:
                data = {'peer_id':chat,'message':reply+',\n'+text,'conversation_message_id':msgid,'access_token':self.token,'v':self.v}
                if buttons is not None:
                    kbd = {"one_time":False,"buttons":[[]],"inline":True}
                    for button in buttons:
                        kbd["buttons"][0].append({'action':{'type':'callback','label':button.text,'payload':button.callback}})
                        data['keyboard'] = json.dumps(kbd)
                async with sess.post('https://api.vk.com/method/messages.edit',params=data) as req:
                    print(await req.text())
        except:
            raise

    async def username(self,userid):
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post('https://api.vk.com/method/users.get',params={'user_ids':userid,'access_token':self.token,'v':self.v}) as req:
                    r = await req.json()
                    return r['response'][0]['first_name']
        except:
            raise

class Response:
    def __init__(self,data):
        self.failed = data.get('failed',0)
        self.ts = data.get('ts',None)
        self.updates = data.get('updates',None)
        if self.updates == []:
            self.updates = None


class Event:
    def __init__(self,data):
        #data = json.loads(data)
        self.type = data['type']
        self.object = data['object']


class Author:
    def __init__(self,data):
        self.uid = data['id']
        self.username = data['username']
    
    def set_name(self,name):
        self.username = name


class Message:
    def __init__(self,data):
        self.id = data['id']
        self.date = data['date']
        self.out = data['out']
        self.author = Author({"id":data['from_id'],"username":None})
        self.body = data['text']
        self.source = data['peer_id']
        self.payload = data.get('payload',None)
        if self.payload is not None:
            self.payload = json.loads(self.payload)
        self.conversation_message_id = data['conversation_message_id']

# {'user_id': 185795956, 'peer_id': 2000000002, 'event_id': '174bc6839d96', 'payload': {'text': 'teachers'}, 'conversation_message_id': 90}
class Msg_Event:
    def __init__(self,data):
        self.user_id = data['user_id']
        self.peer_id = data['peer_id']
        self.event_id = data.get('event_id',None)
        self.payload = data['payload']
        self.conversation_message_id = data['conversation_message_id']
