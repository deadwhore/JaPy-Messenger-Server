import subprocess
from datetime import datetime
import time
import random
import os
import json
import sqlite3


# This class for subprocessing "listeners" (sockets for new users), control their attributes,
# get messages from chat files etc
class User():
    def __init__(self, id):
        self.user_id = id
        self.user_ip = ''
        self.user_nick = ''
        self.user_port = ''
        self.working = False
        self.connected = False
        self.msg_id = 0
        # subprocess object!
        self.process = None
        self.proc_pid = 0
        self.chat_file_name = ''
        self.login = ''

    # creating new subprocess for new "listener" and drop it's console output to NULL, we don't need it
    def start_proc(self, port_num):
        self.user_port = port_num
        # remember chat filename
        self.chat_file_name = 'chat-'+port_num+'.tmp'
        # and creating new
        self.process = subprocess.Popen(
            "python listener.py {} {}".format(port_num, 'chat-'+port_num+'.tmp'),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # subprocess object we create
        self.proc_pid = self.process.pid
        # checking subprocess work status by method
        return self.check_proc()

    # killing subprocess
    def stop_proc(self):
        self.process.kill()

    # checking subprocess status, (if None - it's still working), connection user status
    def check_proc(self):
        # process still working?
        if self.process.poll() is None:
            self.working = True
        else:
            self.working = False

        # if don't know about client connection
        if self.connected is False:
            # let's check user connection by looking for chat_name.tmp file
            if self.chat_file_name in os.listdir(path='.'):
                self.connected = True
                # and let's take IP of connected client
                with open(self.chat_file_name, 'r') as chat_file:
                    for line in chat_file.readlines():
                        deserial_line = json.loads(line)
                        if 'User connected from' in deserial_line['msg_text']:
                            self.user_ip = deserial_line['msg_text'][20:]
                            chat_file.close()
                            self.login = get_time()
                            print('IP -', self.user_ip)
                            break
        return [self.working, self.connected]

    # getting messages from chat file
    def get_msg(self):
        with open(self.chat_file_name, 'r') as chat_file:
            # list of all messages
            msg_read = list()
            # list of last messages
            msg_last = list()
            for line in chat_file.readlines():
                # convert json strings to dict and add them to list
                msg_read.append(json.loads(line))
            chat_file.close()

            # have to parse list of messages to control msg_id and return only newest messages
            for msg in msg_read:
                if msg['msg_id'] > self.msg_id or msg['msg_id'] == -1:
                    msg_last.append(msg)
                    self.msg_id = msg['msg_id']

            return msg_last

    # if we need to understand what's going on - get all attributes
    def show_attr(self):
        return {
            'user_id': self.user_id,
            'user_nick': self.user_nick,
            'user_port': self.user_port,
            'establish': self.working,
            'connected': self.connected,
            'msg_id': self.msg_id,
            'process': self.process,
            'proc_pid': self.proc_pid,
            'user_ip': self.user_ip,
            'login': self.login
        }


# deleting msg_id from message and adding srv_msg_id
def change_msg_to_srv_id(message, id):
    message.pop('msg_id')
    message['srv_msg_id'] = id
    message['cl_id'] = message['user_id']
    return message


# sorting dictionaries by date
def sort_by_date(input_dict):
    return input_dict['lstnr_time']


# method for getting date and time
def get_time():
    now_time = datetime.now()
    date = now_time.date()
    hour = now_time.hour
    minutes = now_time.minute
    seconds = now_time.second
    return '{} {}:{}:{}'.format(date, hour, minutes, seconds)


# creating sqlite database
def creating_sql():
    global cursor
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS Account (
        user_ip TEXT,
        user_nick TEXT,
        user_login TEXT,
        user_logout TEXT
    );

    CREATE TABLE IF NOT EXISTS Messages (
        srv_msg_id INTEGER NOT NULL PRIMARY KEY UNIQUE,
        srv_tag INTEGER,
        lstnr_msg_id INTEGER,
        lstnr_time TEXT,
        user_nick TEXT,
        msg_text TEXT
    );
    ''')


# commiting sqlite database
def commit_sql():
    global sql_connection
    print('Commiting SQL')
    sql_connection.commit()


# inserting user information
def insert_sql_acc(user_ip, user_nick, login, logout):
    global cursor
    cursor.execute('''INSERT INTO Account (user_ip, user_nick, user_login, user_logout) VALUES (?, ?, ?, ?)''',
                   (user_ip, user_nick, login, logout))
    commit_sql()


# inserting new messages to sqlite database
def insert_sql_msg(srv_id, dic_msg):
    global cursor
    cursor.execute('''INSERT INTO Messages (srv_msg_id, srv_tag, lstnr_msg_id, lstnr_time, user_nick, msg_text)
    VALUES (?, ?, ?, ?, ?, ?)''', (srv_id, dic_msg["srv_tag"], dic_msg["msg_id"], dic_msg["lstnr_time"],
                                   dic_msg["user_nick"], dic_msg["msg_text"]))



# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-


# list of ports
# ports_list = ['25901', '25902', '25903', '25904', '25905', '25906', '25907', '25908', '25909', '25910']
ports_list = ['25901', '25902', '25903']
# list of busied ports
ports_avail = [False, False, False]
# list of user=processes=ports=messages=etc
users = []
# list of last messages
lst_raw = list()
# syncronized chat file name
sync_chat_file_name = 'chat.txt'
# sqlite datebase file name
sqlite_file_name = 'history.sqlite'
# syncronizer messages counter
srv_msg_id = 0

# creating sqlite
sql_connection = sqlite3.connect(sqlite_file_name)
cursor = sql_connection.cursor()
creating_sql()

# we should delete all old .tmp files with old chat logs.
list_tmp_files = [x for x in os.listdir(path='.') if x.endswith('.tmp')]
for tmp_file in list_tmp_files:
    os.remove(tmp_file)


# starting first listener before loop
new_user = User(random.randint(0, 100))
# adding this object to array with processes
users.append(new_user)
# starting new process
new_user.start_proc(ports_list[0])
# checking subprocess starting if OK - write it
if new_user.check_proc()[0]:
    ports_avail[0] = True

i = 0

# open resulting chat file where was all chat
with open(sync_chat_file_name, 'a') as chat_file:
    # starting working loop
    while i < 10:
        # clear list of last messages
        lst_raw = []

        print('!!!! NEW LOOP !!!!')
        # checking how many ports are busy
        ports_busy = 0
        # and how many processes are
        process_active = 0
        for user in users:
            checking_result = user.check_proc()
            print(user.show_attr()['user_port'])
            print(checking_result)
            if checking_result[1]:
                ports_busy += 1

                # working zone starts here! =)
                # vvvvvvvvvvvvvvvvvvvvvvvvvvvv

                # getting all last messages from files
                msgs = user.get_msg()
                if isinstance(msgs, list):
                    for dic in msgs:
                        srv_msg_id += 1
                        lst_raw.append(change_msg_to_srv_id(dic, srv_msg_id))
                else:
                    srv_msg_id += 1
                    lst_raw.append(change_msg_to_srv_id(msgs, srv_msg_id))

                # every 10 msgs commiting database
                if srv_msg_id % 10 == 0:
                    commit_sql()

                # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                # working zone stops here! =(

            if checking_result[0]:
                process_active += 1

        # sorting all messages if new comes
        if len(lst_raw) > 0:
            lst_raw.sort(key=sort_by_date)
            for msg in lst_raw:
                chat_file.write('\n' + json.dumps(msg))
            chat_file.flush()
        else:
            print('no new msgs??')

        print(ports_busy, 'port(s) busy and', process_active, 'processes active')
        # if all ports are busy we should open new port
        if ports_busy == len(users):
            print('Creating new listener')
            # let's find out next free port from ports_list
            next_port = None
            port_number = 0
            for port in ports_avail:
                if port is False:
                    next_port = ports_list[ports_avail.index(port)]
                    break
                port_number += 1

            # if we got next free port:
            if next_port is not None:
                new_user = User(random.randint(0, 100))
                users.append(new_user)

                # checking subprocess starting if OK - change False state of ports_avail to True
                new_user.start_proc(next_port)
                # add +1 to active processes or it will be killed
                process_active += 1
                if new_user.check_proc()[0]:
                    ports_avail[port_number] = True

        time.sleep(3.0)
        i += 1

        # if we have more users than subprocesses let's deleting from user array useless objects
        if len(users) > process_active:
            for user in users:
                if user.check_proc()[0] is False:
                    # get port of usefull (closed) subprocess
                    user_attr = user.show_attr()
                    print('removing listener', user_attr['user_port'])
                    # change port status to False
                    ports_avail[ports_list.index(user_attr['user_port'])] = False
                    # and remove object from array
                    users.remove(user)
                    # removing chat file from disk
                    try:
                        os.remove('chat-'+user_attr['user_port']+'.tmp')
                        insert_sql_acc(user_attr['user_ip'], user_attr['user_nick'], user_attr['login'], get_time())
                    except OSError:
                        print("ERROR: try to delete chat file, but can't found it")

    chat_file.close()

print('Loops ENDED')
time.sleep(6.0)

# stopping processes
for user in users:
    user.stop_proc()

time.sleep(10.0)
for user in users:
    print(user)
    print('now?', user.check_proc())

commit_sql()
print('END')