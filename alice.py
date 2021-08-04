#!/usr/bin/python3
# -*- coding: utf-8 -*-
import asyncio
import websockets
import json
import datetime
import sqlite3
import re
from debugger import dbg

import discord

#import dscrd
import vk as vk_bot
import timetable
import db
import waiters
import contents

days_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота','Воскресенье']

univ_db = db.UnivDB('universities.db')
users_db = db.UserDB('users.db')
groups_db = db.GroupDB('groups.db')
hw_db = db.HwDB('hw.db')

import tokens
dscrd_key = tokens.dscrd_key
vk_key = tokens.vk_key

bot_discord = discord.Client()
vk = vk_bot.Bot(vk_key)

@bot_discord.event
async def on_message(msg):
    text = msg.content
    user = msg.author
    channel = msg.channel
    resp = await msg_handler(text,user,'discord',channel)
    if resp is not None:
        retval = await fmttr(resp,'discord')
        rettext = retval['text']
        await reply('discord',channel,rettext,None)

@vk.event
async def on_message___vk(msg):
    text = msg.body
    user = msg.author
    chat = msg.source
    user.set_name(await vk.username(user.uid))
    resp = await msg_handler(text,user,'vk',chat)
    if resp is not None:
        retval = await fmttr(resp,'vk')
        rettext = retval['text']
        await reply('vk',chat,rettext,user.username,buttons=retval['special']['buttons'])

@vk.event
async def on_msg_event___vk(event):
    if event.payload['text'] in ['teachers','places','reload','prevday','nextday']:
        curuser = users_db.get_user(user_id=event.user_id,source='vk')
        univ = univ_db.get_univ(curuser.univ_id)
        group = groups_db.get_group(curuser.group_id)
        day = datetime.datetime.strptime(event.payload['day'],'%d.%m.%y')
        if event.payload['text'] == 'teachers':
            rettable = await tt_parser(univ,group,curuser,day,teachers=True)
        elif event.payload['text'] == 'places':
            rettable = await tt_parser(univ,group,curuser,day,places=True)
        elif event.payload['text'] == 'reload':
            rettable = await tt_parser(univ,group,curuser,day)
        elif event.payload['text'] == 'nextday':
            rettable = await tt_parser(univ,group,curuser,day+datetime.timedelta(days=1))
        elif event.payload['text'] == 'prevday':
            rettable = await tt_parser(univ,group,curuser,day-datetime.timedelta(days=1))
    username = await vk.username(event.user_id)
    retval = await fmttr(rettable,'vk')
    rettext = retval['text']
    await vk.edit(event.peer_id,rettext,username,event.conversation_message_id,buttons=retval['special']['buttons'])

async def fmttr(obj,target):
    retval = {'text':"",'special':{"buttons":[]}}
    def parse_text(r):
        rtext = r.content
        if r.bold:
            if target == 'discord':
                rtext = f'**{rtext}**'
        if r.italic:
            if target == 'discord':
                rtext = f'*{rtext}*'
        return rtext
    def parse_text_multi(r):
        rtext = ""
        for textpart in r:
            rtext += parse_text(textpart)
        return rtext
    def parse_sentence(r):
        if type(r) is contents.Text:
            rtext = parse_text(r)
        elif type(r) is tuple:
            rtext = parse_text_multi(r)
        return rtext
    if type(obj) is tuple:
        newt = []
        for part in obj:
            if type(part) is contents.Text or type(part) is contents.MultilineText or type(part) is tuple or type(part) is contents.Table:
                newt.append(part)
            elif type(part) is contents.Button:
                retval['special']['buttons'].append(part)
        obj = tuple(newt)
        if len(obj) == 1:
            obj = obj[0]
    if type(obj) is contents.Text or type(obj) is tuple:
        rettext = parse_sentence(obj)
    elif type(obj) is contents.MultilineText:
        rettext = ""
        for line in obj.lines:
            rettext += parse_sentence(line)
            rettext += '\n'
    elif type(obj) is contents.Table:
        rettext = parse_sentence(obj.header)
        if target == 'discord':
            rettext += '\n```\n'
        elif target == 'vk':
            rettext += '\n'
        for row in range(len(obj.rows)):
            for ind in obj.cols:
                if target == 'discord':
                    rettext += f"{obj.cols[ind][row]:<{obj.max_len(ind)}}"
                elif target == 'vk':
                    rettext += f"{obj.cols[ind][row]}"
                rettext += " "
            rettext += "\n"
        if target == 'discord':
            rettext += '```'
    retval['text'] = rettext
    return retval

async def reply(source,chat,text,reply_to,buttons=None):
    if source == 'discord':
        await chat.send(text)
    elif source == 'vk':
        await vk.send(chat,text,reply_to,buttons=buttons)

async def tt_parser(univ,group,curuser,day,teachers=False,places=False):
    tt = None
    if univ.name == 'Университет Дубна':
        tt = await timetable.parse_dubn_tt(group.name)
    if tt is None:
        return contents.Text('Расписание данной группы не найдено')
    buttarr = [contents.Button("🎓",{'text':'teachers'}),contents.Button("🚪",{'text':'places'}),contents.Button("🔄",{'text':'reload'}),contents.Button("◀",{'text':'prevday'}),contents.Button("▶",{'text':'nextday'})]
    for but in buttarr:
        but.callback['day'] = day.strftime("%d.%m.%y")
    tt.bells = univ.bells
    week_tmpl = timetable.SpecificWeek(tt,day,group_overrides=group.overrides,user_overrides=curuser.overrides,bells=univ.bells)
    week = week_tmpl.get()
    day_lessons = week.day(day.isoweekday())
    day_name = days_names[day.weekday()]
    if day_lessons is None:
        rettext = contents.MultilineText()
        rettext.add_line((contents.Text(f'{day_name}:',bold=True),contents.Text(" "),contents.Text(f"({day.strftime('%d.%m.%y')})",italic=True)))
        rettext.add_line(contents.Text("В этот день не учимся."))
        return tuple([rettext,] + buttarr)
    newtable = contents.Table()
    newtable.set_header((contents.Text(f'{day_name}:',bold=True),contents.Text(" "),contents.Text(f"({day.strftime('%d.%m.%y')})",italic=True)))
    cols = ['time','lesson']
    if teachers:
        cols.append('teacher')
    elif places:
        cols.append('place')
    else:
        cols.append('type')
    newtable.set_cols(cols)
    for less_id in sorted(day_lessons.lessons):
        less = day_lessons.lessons[less_id]
        row = {"time":f"{less.times[0]} - {less.times[1]}:","lesson":less.name}
        if teachers:
            row['teacher'] = "(" + less.teacher + ")"
        elif places:
            row['place'] = "(" + less.place + ")"
        else:
            row['type'] = "(" + less.l_type.pretty + ")"
        newtable.add_row(row)
    
    return tuple([newtable,] + buttarr)

wait_queue = []
async def msg_handler(text,author,source,chat=None):
    if source == 'vk':
        username = author.username
        userid = author.uid
    elif source == 'discord':
        username = author.name
        userid = author.id
    if userid == "818721157460656129":
        print(f"{source}: {username} (me) - {text}")
        return
    print(f"{source}: {username} - {text}")
    nopunc = re.sub('\W', ' ', text.lower())
    text_parsable = f" {nopunc} "
    #print(text_parsable)
    curuser = users_db.get_user(userid,source)
    curuser.set_messenger_id(userid,source)
    curgroup = groups_db.get_group(curuser.group_id)
    for wait in wait_queue:
        if wait.completed:
            wait_queue.remove(wait)
        else:
            if wait.reason == 'link':
                code = text.replace('!link ','')
                if code == wait.code:
                    wait.cancel()
                    wait_queue.remove(wait)
                    if curuser._uid is None:
                        return contents.Text('Данный аккаунт не зарегистрирован.')
                    newuser = wait.data
                    curuser.set_messenger_id(newuser._vk,'vk')
                    curuser.set_messenger_id(newuser._dscrd,'discord')
                    curuser.set_messenger_id(newuser._tlgrm,'vk')
                    users_db.reg(curuser)
                    return contents.Text('Успешно соединено!')
            if userid == wait.userid:
                wait.cancel()
                if wait.reason == 'bells':
                    stage = wait.stage
                    if text_parsable == ' все ':
                        wait_queue.remove(wait)
                        univ = univ_db.get_univ(curuser.univ_id)
                        univ.bells = wait.data
                        univ_db.set_univ(univ)
                        return contents.Text(f'Готово. {str(wait.get_time())}')
                    elif stage == 'initial' or stage == 'start':
                        try:
                            wait.add_time(text,'end')
                        except:
                            return contents.Text("Неверное время.")
                        else:
                            wait.start()
                            return contents.Text(f"Введите время окончания {len(wait.data)} пары.")
                    elif stage == 'end':
                        try:
                            wait.add_time(text,'start')
                        except:
                            wait.start()
                            return contents.Text("Неверное время.")
                        else:
                            wait.start()
                            return contents.Text(f"Введите время начала {len(wait.data)+1} пары.")
                elif wait.reason == 'reg':
                    if wait.stage == 'univ':
                        select = text
                        try:
                            select = int(select)
                        except:
                            wait.start()
                            return contents.Text('Неправильный выбор')
                        for univ in wait.data:
                            if univ._univ_id == select:
                                groups = groups_db.list_groups(univ._univ_id)
                                if len(groups) == 1:
                                    wait.stage = 'create'
                                    wait.data = [db.Group(None,'fake',univ._univ_id,None)]
                                    wait.start()
                                    return contents.Text("Введите название новой группы")
                                wait.data = groups
                                wait.stage = 'group'
                                group_text = contents.MultilineText()
                                group_text.add_line(contents.Text("Пожалуйста, выберите группу:"))
                                for group in groups:
                                    group_text.add_line(contents.Text(f'{group._gid}: {group.name}',italic=True))
                                wait.start()
                                return group_text
                        wait.start()
                        return contents.Text("Такого варианта нет.")
                    elif wait.stage == 'group':
                        select = text
                        if select.lower() == 'н':
                            wait.stage = 'create'
                            wait.start()
                            return contents.Text("Введите название новой группы")
                        try:
                            select = int(select)
                        except:
                            wait.start()
                            return contents.Text('Неправильный выбор')
                        for group in wait.data:
                            if group._gid == select:
                                curuser.group_id = select
                                curuser.univ_id = group.univ_id
                                users_db.reg(curuser)
                                wait_queue.remove(wait)
                                return contents.Text("Готово!")
                    elif wait.stage == 'create':
                        name = text
                        univ_id = wait.data[0].univ_id
                        group = db.Group(None,name,univ_id,None)
                        groups_db.set_group(group)
                        groups = groups_db.list_groups(univ_id)
                        for group in groups:
                            if group.name == name:
                                break
                        curuser.univ_id = univ_id
                        curuser.group_id = group._gid
                        users_db.reg(curuser)
                        wait_queue.remove(wait)
                        return contents.Text("Готово!")
                elif wait.reason == 'nameoverride':
                    if wait.stage == 'type':
                        if text == '1':
                            wait.stage = 'from_user'
                            wait.start()
                            return contents.Text("Что меняем?")
                        elif text == '2':
                            wait.stage = 'from_group'
                            wait.start()
                            return contents.Text("Что меняем?")
                        elif text == '3' or text == '4':
                            userover = curuser.overrides.get('names',{})
                            groupover = curgroup.overrides.get('names',{})
                            rettext = contents.MultilineText()
                            rettext.add_line(contents.Text('Пользователь:',bold=True))
                            if len(userover) > 0:
                                for over in userover:
                                    rettext.add_line((contents.Text(f'{over}: '), contents.Text(userover[over],italic=True)))
                            else:
                                rettext.add_line('Переименований нет.')
                            rettext.add_line(contents.Text(""))
                            rettext.add_line(contents.Text('Группа:',bold=True))
                            if len(groupover) > 0:
                                for over in groupover:
                                    rettext.add_line((contents.Text(f'{over}: '), contents.Text(groupover[over],italic=True)))
                            else:
                                rettext.add_line(contents.Text('Переименований нет.'))
                            if text == '4':
                                wait.stage = 'remove'
                                rettext.add_line(contents.Text(""))
                                rettext.add_line(contents.Text('Введите ID для удаления (слева от ":"):'))
                                wait.start()
                                return rettext
                            else:
                                wait_queue.remove(wait)
                                return rettext
                        else:
                            wait.start()
                            return contents.Text("Неверный ввод.")
                    elif wait.stage == 'remove':
                        userover_all = curuser.overrides
                        userover = userover_all.get('names',{})
                        groupover_all = curgroup.overrides
                        groupover = groupover_all.get('names',{})
                        #print(userover)
                        #print(groupover)
                        try:
                            userover.pop(text)
                            userover_all['names'] = userover
                            curuser.overrides = userover_all
                            users_db.set_overrides(curuser)
                            wait_queue.remove(wait)
                            return (contents.Text(text,bold=True), contents.Text(" удалено из пользовательских замен!"))
                        except:
                            try:
                                groupover.pop(text)
                                #print('rmvd')
                                groupover_all['names'] = groupover
                                curgroup.overrides = groupover_all
                                groups_db.set_overrides(curgroup)
                                wait_queue.remove(wait)
                                return (contents.Text(text,bold=True), contents.Text(" удалено из групповых замен!"))
                            except:
                                wait.start()
                                return contents.Text("Неверный выбор.")
                    elif wait.stage.startswith('from'):
                        if 'user' in wait.stage:
                            wait.stage = 'to_user'
                        elif 'group' in wait.stage:
                            wait.stage = 'to_group'
                        wait.data = text
                        wait.start()
                        return contents.Text("На что меняем?")
                    elif wait.stage.startswith('to'):
                        namefrom = wait.data
                        nameto = text
                        curgroup = groups_db.get_group(curuser.group_id)
                        if 'user' in wait.stage:
                            overrides = curuser.overrides
                            overrides['names'][namefrom.lower().replace(' ','')] = nameto
                            curuser.overrides = overrides
                            users_db.set_overrides(curuser)
                        elif 'group' in wait.stage:
                            overrides = curgroup.overrides
                            overrides['names'][namefrom.lower().replace(' ','')] = nameto
                            curgroup.overrides = overrides
                            groups_db.set_overrides(curgroup)
                        wait_queue.remove(wait)
                        return (contents.Text(namefrom,bold=True), contents.Text(" изменено на "), contents.Text(nameto,bold=True))
                elif wait.reason == 'lessonoverride':
                    if wait.stage == 'type':
                        if text == '1':
                            wait.stage = 'tt_type'
                            wait.start()
                            rettext = contents.MultilineText()
                            rettext.add_line(contents.Text("Установить для себя или для группы?"))
                            rettext.add_line(contents.Text("1. Только для себя",italic=True))
                            rettext.add_line(contents.Text("2. Для всей группы",italic=True))
                            return rettext
                        elif text == '2':
                            wait.stage = 'fac_day'
                            wait.start()
                            return contents.Text("Выберите день недели (1-7, Понедельник-Воскресенье)")
                        elif text == '3' or text == '4':
                            u_overrides = curuser.overrides['lessons']
                            g_overrides = curgroup.overrides['lessons']
                            rettext = contents.MultilineText()
                            rettext.add_line(contents.Text('Вы:',bold=True))
                            if len(u_overrides) > 0:
                                for day_id in u_overrides:
                                    for over_id in u_overrides[day_id]:
                                        if type(over_id) is int:
                                            fmt_id = over_id + 1
                                        else:
                                            fmt_id = over_id
                                        if u_overrides[day_id][over_id] is None:
                                            rettext.add_line(contents.Text(f'\nu-{day_id+1}-{fmt_id}: '),contents.Text('Скрыто',italic=True))
                                        else:
                                            rettext.add_line(contents.Text(f'\nu-{day_id+1}-{fmt_id}: '),contents.Text(u_overrides[day_id][over_id]["name"],italic=True))
                            else:
                                rettext.add_line(contents.Text('Нет замен.'))
                            rettext.add_line(contents.Text(""))
                            rettext.add_line(contents.Text('Группа:',bold=True))
                            if len(g_overrides) > 0:
                                for day_id in g_overrides:
                                    print(g_overrides)
                                    print(day_id)
                                    for over_id in g_overrides[day_id]:
                                        if type(over_id) is int:
                                            fmt_id = over_id + 1
                                        else:
                                            fmt_id = over_id
                                        if g_overrides[day_id][over_id] is None:
                                            rettext.add_line(contents.Text(f'\ng-{day_id+1}-{fmt_id}: '),contents.Text('Скрыто',italic=True))
                                        else:
                                            rettext.add_line(contents.Text(f'\ng-{day_id+1}-{fmt_id}: '),contents.Text(g_overrides[day_id][over_id]["name"],italic=True))
                            if text == '4':
                                wait.stage = 'remove'
                                rettext.add_line(contents.Text(""))
                                rettext.add_line(contents.Text('Введите ID для удаления (слева от ":"):'))
                                wait.start()
                                return rettext
                            else:
                                wait_queue.remove(wait)
                                return rettext
                        else:
                            wait.start()
                            return contents.Text("Неверный ввод.")
                    elif wait.stage == 'tt_type':
                        if text == '1':
                            wait.stage = 'tt_day_user'
                            wait.start()
                            return contents.Text("Выберите день недели (1-7, Понедельник-Воскресенье)")
                        elif text == '2':
                            wait.stage = 'tt_day_group'
                            wait.start()
                            return contents.Text("Выберите день недели (1-7, Понедельник-Воскресенье)")
                        else:
                            wait.start()
                            return contents.Text("Неверный ввод.")
                    elif 'remove' in wait.stage:
                        if text.startswith('u-'):
                            try:
                                hdr, day, oid = text.split('-')
                                try:
                                    oid = int(oid) - 1
                                except:
                                    pass
                                day = int(day) - 1
                                #print('vars')
                                overrides = curuser.overrides
                                #print(overrides)
                                #print(hdr, day, oid)
                                overrides['lessons'][day].pop(oid)
                                #print('rmv')
                                curuser.overrides = overrides
                                users_db.set_overrides(curuser)
                                #print('db')
                                wait_queue.remove(wait)
                                return contents.Text("Готово!")
                            except:
                                wait.start()
                                return contents.Text("Неверный ввод")
                        elif text.startswith('g-'):
                            try:
                                hdr, day, oid = text.split('-')
                                try:
                                    oid = int(oid) - 1
                                except:
                                    pass
                                day = int(day) - 1
                                overrides = curgroup.overrides
                                overrides['lessons'][day].pop(oid)
                                curgroup.overrides = overrides
                                groups_db.set_overrides(curgroup)
                                wait_queue.remove(wait)
                                return contents.Text("Готово!")
                            except:
                                wait.start()
                                return contents.Text("Неверный ввод")
                        else:
                            wait.start()
                            return contents.Text("Неверный ввод")
                    elif 'day' in wait.stage:
                        if text.capitalize() in days_names:
                            day = days_names.index(text.capitalize())+1
                        elif text in ['1','2','3','4','5','6','7']:
                            day = text
                        else:
                            wait.start()
                            return contents.Text("Неверный выбор.")
                        wait.data["day"] = day
                        if wait.stage.startswith('tt'):
                            if 'user' in wait.stage:
                                wait.stage = 'tt_num_user'
                            elif 'group' in wait.stage:
                                wait.stage = 'tt_num_group'
                            wait.start()
                            return contents.Text("Какую пару меняем? (1-6)")
                            #Выводить список пар
                        elif wait.stage.startswith('fac'):
                            wait.stage = 'fac_time_start'
                            wait.start()
                            return contents.Text("Когда начинается?")
                    elif 'num' in wait.stage:
                        if text in ['1','2','3','4','5','6']:
                            wait.data["num"] = text
                            wait.stage = wait.stage.replace('num','type')
                            wait.start()
                            rettext = contents.MultilineText()
                            rettext.add_line(contents.Text("Что будет?"))
                            rettext.add_line(contents.Text("1. Лекция",italic=True))
                            rettext.add_line(contents.Text("2. Семинар",italic=True))
                            rettext.add_line(contents.Text("3. Иностранный язык",italic=True))
                            rettext.add_line(contents.Text("4. Физкультура",italic=True))
                            rettext.add_line(contents.Text("5. Неизвестно",italic=True))
                            if not 'fac' in wait.stage:
                                rettext.add_line(contents.Text("6. Удалить пару",italic=True))
                            return rettext
                        else:
                            wait.start()
                            return contents.Text("Неверный выбор.")
                    elif 'type' in wait.stage:
                        if text == '1':
                            typ = timetable.LessonType.LECTURE
                        elif text == '2':
                            typ = timetable.LessonType.SEMINAR
                        elif text == '3':
                            typ = timetable.LessonType.FOREIGN_LANG
                        elif text == '4':
                            typ = timetable.LessonType.PHYSICAL
                        elif text == '5':
                            typ = timetable.LessonType.UNK
                        elif text == '6' and not 'fac' in wait.stage:
                            if 'user' in wait.stage:
                                overrides = curuser.overrides
                            elif 'group' in wait.stage:
                                overrides = curgroup.overrides
                            if overrides['lessons'].get(int(wait.data["day"])-1,None) is None:
                                overrides['lessons'][int(wait.data["day"])-1] = {}
                            #print(wait.data["day"])
                            overrides['lessons'][int(wait.data["day"])-1][int(wait.data["num"])-1] = None
                            if 'user' in wait.stage:
                                curuser.overrides = overrides
                                users_db.set_overrides(curuser)
                            elif 'group' in wait.stage:
                                curgroup.overrides = overrides
                                groups_db.set_overrides(curgroup)
                            wait_queue.remove(wait)
                            return contents.Text("Готово!")
                        else:
                            wait.start()
                            return contents.Text("Неверный выбор.")
                        wait.data["type"] = typ
                        wait.stage = wait.stage.replace('type','name')
                        wait.start()
                        return contents.Text("Как называется?")
                    elif 'time_start' in wait.stage:
                        ts = re.findall(r'[0-2]?[0-9]:[0-9]{2}',text)
                        if len(ts) != 1:
                            wait.start()
                            return contents.Text("Неверное время")
                        else:
                            if int((ntime := ts[0]).split(':')[0]) > 23:
                                wait.start()
                                return contents.Text("Неверное время")
                            wait.data["time_start"] = ntime
                            wait.stage = 'fac_time_end'
                            wait.start()
                            return contents.Text("Когда / через сколько минут заканичваем?")
                    elif 'time_end' in wait.stage:
                        try:
                            ntime = int(text)
                        except:
                            ntime = re.findall(r'[0-2]?[0-9]:[0-9]{2}',text)
                            if len(ntime) != 1:
                                wait.start()
                                return contents.Text("Неверное время.")
                        else:
                            hrs = int(wait.data["time_start"].split(':')[0])
                            mnt = int(wait.data["time_start"].split(':')[1])
                            mnt += ntime
                            hrs += mnt // 60
                            mnt = mnt % 60
                            ntime = f'{hrs:02}:{mnt:02}'
                        wait.data["time_end"] = ntime
                        wait.stage = 'fac_name'
                        wait.start()
                        return contents.Text("Как называется?")
                    elif 'name' in wait.stage:
                        wait.data["name"] = text
                        wait.stage = wait.stage.replace('name','place')
                        wait.start()
                        return contents.Text("Где будет?")
                    elif 'place' in wait.stage:
                        wait.data['place'] = text
                        wait.stage = wait.stage.replace('place','teacher')
                        wait.start()
                        return contents.Text('Кто ведет?')
                    elif 'teacher' in wait.stage:
                        wait.data['teacher'] = text
                        if 'fac' in wait.stage or 'user' in wait.stage:
                            overrides = curuser.overrides
                        elif 'group' in wait.stage:
                            overrides = curgroup.overrides
                        if 'fac' in wait.stage:
                            lid = wait.data['name']
                        else:
                            lid = int(wait.data['num']) - 1
                        if wait.data['type'] is None:
                            wait.data['type'] = timetable.LessonType.UNK
                        newless = {"name":wait.data['name'],'teacher':wait.data['teacher'],"place":wait.data['place'],'type':wait.data['type'].value,
                        'start':wait.data['time_start'],'end':wait.data['time_end']}
                        if overrides['lessons'].get(int(wait.data["day"])-1,None) is None:
                            overrides['lessons'][int(wait.data["day"])-1] = {}
                        overrides['lessons'][int(wait.data["day"])-1][lid] = newless
                        if 'fac' in wait.stage or 'user' in wait.stage:
                            curuser.overrides = overrides
                            users_db.set_overrides(curuser)
                        elif 'group' in wait.stage:
                            curgroup.overrides = overrides
                            groups_db.set_overrides(curgroup)
                        wait_queue.remove(wait)
                        return contents.Text("Готово!")
                elif wait.reason == 'hw':
                    if wait.stage == 'lesson':
                        wait.data['lesson'] = text
                        wait.stage = 'contents'
                        wait.start()
                        return contents.Text("Что задали?")
                    elif wait.stage == 'contents':
                        wait.data['contents'] = text
                        wait.stage = 'time'
                        wait.start()
                        return contents.Text("На когда? (ДД.ММ.ГГ)")
                    elif wait.stage == 'time':
                        try:
                            time = datetime.datetime.strptime(text,'%d.%m.%y')
                        except:
                            wait.start()
                            return contents.Text("Неверный ввод.")
                        hw_db.add_hw(curuser,db.Task(wait.data['lesson'],text,wait.data['contents']))
                        wait_queue.remove(wait)
                        return contents.Text(f'Добавлено задание по {wait.data["lesson"]} на {text}')

    if text == '!bells':
        if curuser._uid is None:
            return (contents.Text("Вы не зарегистрированы. Используйте "), contents.Text("!reg",bold=True), contents.Text(" для создания нового аккаунта или !link для подключения к существующему."))
        bells_await = waiters.BellsAwaitable(userid,task=reply,parameters=(source,chat,contents.Text('Не вижу ответа.')),time=60)
        bells_await.start()
        wait_queue.append(bells_await)
        return contents.Text("Введите время начала учебы.")
    elif text == '!reg':
        univs = univ_db.list_univ()
        rettext = contents.MultilineText()
        rettext.add_line(contents.Text("Пожалуйста, выберите университет:"))
        for univ in univs:
            rettext.add_line(contents.Text(f'\n{univ._univ_id}: {univ.name}',italic=True))
        reg_await = waiters.RegAwaitable(userid,task=reply,parameters=(source,chat,contents.Text('Не вижу ответа.')),time=60,data=univs)
        reg_await.start()
        wait_queue.append(reg_await)
        return rettext
    elif text == '!link':
        link_await = waiters.LinkAwaitable(userid,task=reply,parameters=(source,chat,contents.Text('Вышло время.')),time=300,data=curuser)
        code = link_await.code
        link_await.start()
        wait_queue.append(link_await)
        rettext = contents.MultilineText()
        rettext.add_line(contents.Text(f'Введите "!link {code}" на втором аккаунте. Код действителен в течение пяти минут.'))
        if curuser._uid is not None:
            rettext.add_line(contents.Text('Аккаунт не пустой, все данные будут заменены.'))
        return rettext
    elif text == '!alias':
        if curuser._uid is None:
            return contents.Text("Вы не зарегистрированы. Используйте !reg для создания нового аккаунта или !link для подключения к существующему.")
        name_await = waiters.NameAwaitable(userid,task=reply,parameters=(source,chat,'Не вижу ответа.'),time=60,data=curuser)
        name_await.start()
        wait_queue.append(name_await)
        rettext = contents.MultilineText()
        rettext.add_line(contents.Text("Установить для себя или для группы?"))
        rettext.add_line(contents.Text("1. Только для себя",italic=True))
        rettext.add_line(contents.Text("2. Для всей группы",italic=True))
        rettext.add_line(contents.Text("3. Показать существующие",italic=True))
        rettext.add_line(contents.Text("4. Удалить замену",italic=True))
        return rettext
    elif text == '!override':
        if curuser._uid is None:
            return contents.Text("Вы не зарегистрированы. Используйте !reg для создания нового аккаунта или !link для подключения к существующему.")
        less_await = waiters.LessonAwaitable(userid,task=reply,parameters=(source,chat,'Не вижу ответа.'),time=60,data=curuser)
        less_await.start()
        wait_queue.append(less_await)
        rettext = contents.MultilineText()
        rettext.add_line(contents.Text("Изменить основное расписание или факультативы?"))
        rettext.add_line(contents.Text("1. Основное",italic=True))
        rettext.add_line(contents.Text("2. Факультативы",italic=True))
        rettext.add_line(contents.Text("3. Показать существующие",italic=True))
        rettext.add_line(contents.Text("4. Удалить замену",italic=True))
        return rettext
    elif text.startswith('!hw'):
        if curuser._uid is None:
            return contents.Text("Вы не зарегистрированы. Используйте !reg для создания нового аккаунта или !link для подключения к существующему.")
        if text == '!hw get':
            tasks = hw_db.get_hw(curuser)
            rettext = contents.MultilineText()
            werehw = False
            for task in tasks:
                werehw = True
                if task.passed:
                    rettext.add_line(contents.Text(f"{task.task_id} - {task.name}: {task.content} ({task.time_text})",bold=True))
                else:
                    rettext.add_line(contents.Text(f"{task.task_id} - {task.name}: {task.content} ({task.time_text})"))
            if not werehw:
                rettext.add_line(contents.Text("Все сделано!"))
            return rettext
        elif text == '!hw add':
            hw_await = waiters.HwAwaitable(userid,task=reply,parameters=(source,chat,'Не вижу ответа.'),time=60)
            hw_await.start()
            wait_queue.append(hw_await)
            return contents.Text("По какому предмету?")
    elif text.startswith('!done'):
        if curuser._uid is None:
            return contents.Text("Вы не зарегистрированы. Используйте !reg для создания нового аккаунта или !link для подключения к существующему.")
        task_id = text.replace('!done ','')
        try:
            task_id = int(task_id)
        except:
            return contents.Text("Нет такого задания.")
        tasks = hw_db.get_hw(curuser)
        found = False
        for task in tasks:
            if task.task_id == task_id:
                found = True
                break
        if found:
            curuser.done.append(task_id)
            users_db.set_done(curuser)
            return contents.Text(f"Задание {task_id} отмечено сделанным.")
        else:
            return contents.Text("Нет такого задания.")
    elif text.startswith('!help'):
        rettable = contents.Table()
        rettable.set_header(contents.Text("Что я могу?"))
        rettable.set_cols(('command','descr'))
        rettable.add_row({'command':"Расписание на...",'descr':' - получить расписание на указанный день'})
        rettable.add_row({'command':'!hw get','descr':' - получить домашнее задание'})
        rettable.add_row({'command':'!hw add','descr':' - добавить домашнее задание'})
        rettable.add_row({'command':'!done (ID)','descr':' - отметить задание выполненным'})
        rettable.add_row({'command':'','descr':''})
        rettable.add_row({'command':'!alias','descr':' - поменять название предмета'})
        rettable.add_row({'command':'!override','descr':' - изменить расписание'})
        rettable.add_row({'command':'!bells','descr':' - изменить расписание звонков'})
        rettable.add_row({'command':'','descr':''})
        rettable.add_row({'command':'!reg','descr':' - создать новый аккаунт'})
        rettable.add_row({'command':'!link','descr':' - соединить новый аккаунт с существующим'})
        rettable.add_row({'command':'!help','descr':' - ты это сейчас читаешь!'})
        rettable.add_row({'command':'!v','descr':' - кто я вообще такая?'})
        return rettable
    elif text.startswith('!v'):
        rettext = contents.MultilineText()
        rettext.add_line(contents.Text('Элис v.1.2.5'))
        rettext.add_line((contents.Text('Курсовая работа по дисциплине '),contents.Text('ПЯВУ',bold=True)))
        rettext.add_line(contents.Text('Городничин Константин Олегович, 1281, ИСАУ.'))
        return rettext
    elif text.startswith('!say'):
        return contents.Text(text.replace('!say ','',1))
    elif " расписос " in text_parsable or " расписан" in text_parsable:
        if curuser._uid is None:
            return contents.Text("Вы не зарегистрированы. Используйте !reg для создания нового аккаунта или !link для подключения к существующему.")


        today = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=3)))
        #detailed = False
        day = None
        delta = None
        if " завтра " in text_parsable:
            delta = datetime.timedelta(days=1)
        elif " послезавтра " in text_parsable:
            delta = datetime.timedelta(days=2)
        elif " сегодня " in text_parsable:
            delta = datetime.timedelta(days=0)
        elif " вчера " in text_parsable:
            delta = datetime.timedelta(days=-1)
        elif " позавчера " in text_parsable:
            delta = datetime.timedelta(days=-2)
        
        elif " понедельник " in text_parsable:
            day = 1
        elif " вторник " in text_parsable:
            day = 2
        elif " сред" in text_parsable:
            day = 3
        elif " четверг " in text_parsable:
            day = 4
        elif " пятниц" in text_parsable:
            day = 5
        elif " суббот" in text_parsable:
            day = 6
        elif " воскресенье " in text_parsable:
            day = 7
        if day is not None:
            if day > currday:
                delta = datetime.timedelta(days=day-currday)
            else:
                delta = datetime.timedelta(days=day-currday+7)
        try:
            day = today + delta
        except:
            return


        univ = univ_db.get_univ(curuser.univ_id)
        group = groups_db.get_group(curuser.group_id)
        rettable = await tt_parser(univ,group,curuser,day)
        return rettable

loop = asyncio.get_event_loop()
loop.create_task(bot_discord.start(dscrd_key))
vk.start()
print('duck')
try:
    asyncio.get_event_loop().run_forever()
except KeyboardInterrupt:
    univ_db.disconnect()
    users_db.disconnect()
    groups_db.disconnect()
    hw_db.disconnect()
    print('shutdown.')
