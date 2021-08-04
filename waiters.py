import asyncio
import json
import re
import datetime
import inspect
import random

class Awaitable:
    def __init__(self,reason,userid,**kwargs):
        self.reason = reason
        self.userid = userid
        self.data = kwargs.get('data',None)
        self.stage = kwargs.get('stage',None)
        if (time := kwargs.get('time',None)) is not None:
            self.timer = time
        else:
            self.time = None
        if (task := kwargs.get('task',None)) is not None:
            self.task = task
            self.parameters = kwargs.get('parameters',None)
        else:
            self.task = None
            self.parameters = None

        self.aio_task = None
        self.res = None
        self.completed = False

    def set_callback(self,task,parameters=None):
        self.task = task
        #print(inspect.iscoroutinefunction(self.task))
        self.parameters = parameters

    async def runner(self):
        await asyncio.sleep(self.time)
        if inspect.iscoroutinefunction(self.task):
            if self.parameters is None:
                res = await self.task()
            else:
                res = await self.task(*self.parameters)
        else:
            if self.parameters is None:
                res = self.task()
            else:
                res = self.task(*self.parameters)
        self.res = res
        self.completed = True

    @property
    def timer(self):
        return self.time

    @timer.setter
    def timer(self,time):
        #print(time)
        if type(time) is int:
            self.time = time
        else:
            raise TypeError

    def start(self):
        if self.task is not None and self.aio_task is None and self.time is not None:
            self.aio_task = asyncio.create_task(self.runner())

    def cancel(self):
        self.aio_task.cancel()
        self.aio_task = None

    # @property
    # def data(self):
    #     return self.mydata

    # @data.setter
    # def data(self,new_data):
    #     self.mydata = new_data

    # @property
    # def stage(self):
    #     return self._stage

    # @stage.setter
    # def stage(self,newstage):
    #     self._stage = newstage


class BellsAwaitable(Awaitable):
    def __init__(self,userid,**kwargs):
        super().__init__('bells',userid,**kwargs)
        self.stage = 'initial'

    def add_time(self,number,order):
        try:
            number = int(number)
        except:
            pass
        #print(number)
        #print(type(number))
        if type(number) is str:
            time = re.findall(r'[0-2]?[0-9]:[0-9]{2}',number)
            if len(time) == 0:
                raise ValueError
            else:
                time = time[0].split(':')
                hours = int(time[0])
                mins = int(time[1])
                delta = datetime.timedelta(hours=hours,minutes=mins)
        elif type(number) is int:
            delta = datetime.timedelta(minutes=number)
        else:
            raise TypeError
        if self.stage == 'initial':
            lesson = [datetime.datetime.fromtimestamp(75600)+delta,None]
            bells = [lesson]
            self.data = bells
        elif self.stage == 'end':
            self.data[-1][1] = self.data[-1][0] + delta
        elif self.stage == 'start':
            self.data.append([self.data[-1][1]+delta,None])
        self.stage = order

    def get_time(self):
        times_arr = []
        for times in self.data:
            times_arr.append([times[0].time(),times[1].time()])
        return times_arr
        
        
class RegAwaitable(Awaitable):
    def __init__(self,userid,**kwargs):
        super().__init__('reg',userid,**kwargs)
        self.stage = 'univ'


class LinkAwaitable(Awaitable):
    def __init__(self,userid,**kwargs):
        super().__init__('link',userid,**kwargs)
        value = random.randint(0,4294967295)
        padding = 8
        self.code = f"{value:#0{padding}x}".replace('0x','lnk-',1)


class NameAwaitable(Awaitable):
    def __init__(self,userid,**kwargs):
        super().__init__('nameoverride',userid,**kwargs)
        self.stage = 'type'


class LessonAwaitable(Awaitable):
    def __init__(self,userid,**kwargs):
        super().__init__('lessonoverride',userid,**kwargs)
        self.stage = 'type'
        self.data = {"day":None,"name":None,"teacher":None,"type":None,"time_start":None,"time_end":None,"num":None}


class HwAwaitable(Awaitable):
    def __init__(self,userid,**kwargs):
        super().__init__('hw',userid,**kwargs)
        self.stage = 'lesson'
        self.data = {'lesson':None,'time':None,'contents':None}