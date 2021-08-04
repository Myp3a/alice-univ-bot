import sqlite3
import json
import datetime

class DB:
    def __init__(self,name):
        self.db = None
        self.cur = None
        self.name = name
    
    def connect(self):
        self.db = sqlite3.connect(self.name)
        self.cur = self.db.cursor()

    def disconnect(self):
        self.db.close()
        self.db = None
        self.cur = None
    
    def commit(self):
        self.db.commit()


class UnivDB(DB):
    def __init__(self,name):
        super().__init__(name)
        self.connect()
        try:
            self.cur.execute("SELECT * FROM universities;")
        except:
            self.cur.execute('CREATE TABLE universities (name text, bells text);')
            self.commit()

    def list_univ(self):
        arr = []
        self.cur.execute("SELECT rowid, name, bells FROM universities;")
        for row in self.cur.fetchall():
            arr.append(University(row[0],row[1],row[2]))
        return arr

    def get_univ(self,univ_id=None):
        if univ_id is None:
            return University(None)
        else:
            self.cur.execute(f'SELECT rowid, name, bells FROM universities WHERE rowid=?;',(univ_id,))
            rows = self.cur.fetchall()
            if len(rows) == 0:
                raise ValueError
            elif len(rows) == 1:
                row = rows[0]
                bells = row[2]
                if bells is not None:
                    bells = eval(bells)
                return University(row[0],row[1],bells)
            else:
                raise ValueError

    def set_univ(self,univ_obj):
        univ_id = univ_obj._univ_id
        univ_name = univ_obj.name
        univ_bells_obj = univ_obj.bells
        univ_bells_arr = []
        for item in univ_bells_obj:
            univ_bells_arr.append([item[0].strftime('%H:%M'),item[1].strftime('%H:%M')])
        univ_bells = str(univ_bells_arr)
        if univ_id is None:
            self.cur.execute(f'INSERT INTO universities (name,bells) VALUES (?,?);',(univ_name,univ_bells))
        else:
            self.cur.execute(f'UPDATE universities SET name=?, bells=? WHERE rowid=?;',(univ_name,univ_bells,univ_id))
        self.commit()


class UserDB(DB):
    def __init__(self,name):
        super().__init__(name)
        self.connect()
        try:
            self.cur.execute("SELECT * FROM users;")
        except:
            self.cur.execute("CREATE TABLE users (vk text, discord text, tlgrm text, univ_id text, group_id text, overrides text, done text);")
            self.commit()

    def get_user(self,user_id=None,source=None):
        print(f'{source} - {user_id}')
        if user_id is None:
            return User(None)
        else:
            self.cur.execute(f'SELECT rowid, vk, discord, tlgrm, univ_id, group_id, overrides, done FROM users WHERE {source}=?;',(user_id,))
            rows = self.cur.fetchall()
            if len(rows) == 0:
                return User(None)
            elif len(rows) == 1:
                row = rows[0]
                print(row)
                overrides = row[6]
                if overrides is not None:
                    overrides = eval(overrides)
                else:
                    overrides = {'lessons':{},'names':{}}
                done = row[7]
                if done is not None:
                    done = eval(done)
                else:
                    done = []
                return User(row[0],vk=row[1],dscrd=row[2],tlgrm=row[3],univ_id=row[4],group_id=row[5],overrides=overrides,done=done)
            else:
                raise ValueError

    def set_overrides(self,user):
        if user._uid is None:
            raise ValueError
        else:
            if user.overrides is not None:
                overrides = str(user.overrides)
                self.cur.execute(f'UPDATE users SET overrides=? WHERE rowid=?;',(overrides,user._uid))
                self.commit()
            else:
                raise ValueError

    def set_done(self,user):
        if user._uid is None:
            raise ValueError
        else:
            if user.done is not None:
                done = str(user.done)
                self.cur.execute(f'UPDATE users SET done=? WHERE rowid=?;',(done,user._uid))
                self.commit()
            else:
                raise ValueError
        
    def reg(self,user_obj):
        if user_obj._uid is None:
            self.cur.execute(f'INSERT INTO users (vk, discord, tlgrm, univ_id, group_id) VALUES (?,?,?,?,?);',(user_obj._vk,user_obj._dscrd,user_obj._tlgrm,user_obj.univ_id,user_obj.group_id))
        else:
            #print(user_obj._vk,user_obj._dscrd,user_obj._tlgrm,user_obj.univ_id,user_obj.group_id,user_obj.overrides,user_obj._uid)
            self.cur.execute(f'UPDATE users SET vk=?, discord=?, tlgrm=?, univ_id=?, group_id=? WHERE rowid=?;',(user_obj._vk,user_obj._dscrd,user_obj._tlgrm,user_obj.univ_id,user_obj.group_id,user_obj._uid))
        self.commit()


class GroupDB(DB):
    def __init__(self,name):
        super().__init__(name)
        self.connect()
        try:
            self.cur.execute("SELECT * FROM groups;")
        except:
            self.cur.execute("CREATE TABLE groups (name text, univ_id text, overrides text);")
            self.commit()

    def get_group(self,group_id=None):
        if group_id is None:
            return Group(None)
        else:
            self.cur.execute(f'SELECT rowid, name, univ_id, overrides FROM groups WHERE rowid=?;',(group_id,))
            rows = self.cur.fetchall()
            if len(rows) == 0:
                return Group(None)
            elif len(rows) == 1:
                row = rows[0]
                print(row)
                overrides = row[3]
                if overrides is not None:
                    overrides = eval(overrides)
                else:
                    overrides = {'lessons':{},'names':{}}
                return Group(row[0],name=row[1],univ_id=row[2],overrides=overrides)
            else:
                raise ValueError

    def set_group(self,group_obj):
        group_id = group_obj._gid
        group_name = group_obj.name
        group_univ = group_obj.univ_id
        if group_obj.overrides is not None:
            group_overrides = str(group_obj.overrides)
        else:
            group_overrides = None
        if group_id is None:
            self.cur.execute(f'INSERT INTO groups (name,univ_id,overrides) VALUES (?,?,?);',(group_name,group_univ,group_overrides))
        else:
            self.cur.execute(f'UPDATE groups SET name=?, univ_id=?, overrides=? WHERE rowid=?;',(group_name,group_univ,group_overrides,group_id))
        self.commit()

    def list_groups(self,univ_id):
        arr = []
        self.cur.execute("SELECT rowid, name, univ_id, overrides FROM groups WHERE univ_id=?;",(univ_id,))
        for row in self.cur.fetchall():
            arr.append(Group(row[0],row[1],row[2],row[3]))
        arr.append(Group('н',"Создать",univ_id,None))
        return arr

    def set_overrides(self,group):
        if group._gid is None:
            raise ValueError
        else:
            if group.overrides is not None:
                overrides = str(group.overrides)
                self.cur.execute(f'UPDATE groups SET overrides=? WHERE rowid=?;',(overrides,group._gid))
                self.commit()
            else:
                raise ValueError


class HwDB(DB):
    def __init__(self,name):
        super().__init__(name)
        self.connect()

    def get_hw(self,user,also_done=False):
        gid = user._group_id
        uid = user._univ_id
        done = user.done
        try:
            self.cur.execute(f'SELECT rowid, name, time, task FROM "{uid}:::{gid}";')
            lines = self.cur.fetchall()
        except:
            lines = []
        todo = []
        for item in lines:
            if not item[0] in done or also_done:
                todo.append(Task(item[1],item[2],item[3],item[0]))
        return todo
    
    def add_hw(self,user,task):
        gid = user._group_id
        uid = user._univ_id
        self.cur.execute(f'CREATE TABLE IF NOT EXISTS "{uid}:::{gid}" (name text, time text, task text);')
        self.commit()
        print(f'adding {task.name}')
        self.cur.execute(f'INSERT INTO "{uid}:::{gid}" (name,time,task) VALUES (?,?,?);',(task.name,task.time_text,task.content))
        print(f'addedd {task.content}')
        self.commit()
        print('FUCK DBS')
        

class Task:
    def __init__(self,name,time,content,task_id=None):
        self.name = name
        time = datetime.datetime.strptime(time,"%d.%m.%y")
        self.time = time.date()
        self.content = content
        self.task_id = task_id

    @property
    def passed(self):
        today = datetime.date.today()
        if self.time < today:
            return True
        else:
            return False

    @property
    def time_text(self):
        return self.time.strftime("%d.%m.%y")

class Group:
    def __init__(self,group_id,name=None,univ_id=None,overrides=None):
        self._gid = group_id
        self.name = name
        self._overrides = overrides        
        self._univ_id = univ_id

    @property
    def univ_id(self):
        return self._univ_id

    @univ_id.setter
    def univ_id(self,newid):
        self._univ_id = newid

    @property
    def overrides(self):
        return self._overrides

    @overrides.setter
    def overrides(self,overrides):
        self._overrides = overrides


class University:
    def __init__(self,univ_id,name=None,bells=None):
        self._univ_id = univ_id
        self._name = name
        self._bells = bells

    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self,newname):
        self._name = newname
    
    @property
    def bells(self):
        return self._bells

    @bells.setter
    def bells(self,bells):
        if bells[-1][1] is None:
            delta = bells[-2][1].hour*60 + bells[-2][1].minute - bells[-2][0].hour*60 - bells[-2][0].minute
            mins = bells[-1][0].hour*60 + bells[-1][0].minute + delta
            hours = mins // 60
            mins = mins % 60
            delta = datetime.timedelta(hours=hours,minutes=mins)
            bells[-1][1] = datetime.datetime.fromtimestamp(75600)+delta
        for less_num in range(len(bells)):
            bells[less_num][0] = bells[less_num][0]
        self._bells = bells


class User:
    def __init__(self,uid=None,vk=None,dscrd=None,tlgrm=None,univ_id=None,group_id=None,overrides=None,done=None):
        self._uid = uid
        self._vk = vk
        self._dscrd = dscrd
        self._tlgrm = tlgrm
        self._univ_id = univ_id
        self._group_id = group_id
        self._overrides = overrides
        if done is None:
            self.done = []
        else:
            self.done = done

    @property
    def univ_id(self):
        return self._univ_id

    @univ_id.setter
    def univ_id(self,univ_id):
        self._univ_id = univ_id

    @property
    def group_id(self):
        return self._group_id

    @group_id.setter
    def group_id(self,group_id):
        self._group_id = group_id
    
    def set_messenger_id(self,msg_id,source,remove=False):
        if msg_id is not None or remove:
            if source == 'discord':
                self._dscrd = msg_id
            elif source == 'vk':
                self._vk = msg_id
            elif source == 'tlgrm':
                self._tlgrm = msg_id

    @property
    def overrides(self):
        return self._overrides

    @overrides.setter
    def overrides(self,overrides):
        self._overrides = overrides
