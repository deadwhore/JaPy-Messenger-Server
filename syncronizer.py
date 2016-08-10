import subprocess
import time
import random
import os

# This class for subprocessing "listeners" (sockets for new users), control their attributes,
# get messages from chat files etc
class User():
    def __init__(self, id):
        self.user_id = id
        self.user_nick = ''
        self.user_port = ''
        self.working = False
        self.connected = False
        self.msg_id = 0
        self.process = None
        self.proc_pid = 0
        self.chat_file_name = ''

    # creating new subprocess for new "listener" and drop it's console output to NULL, we don't need it
    def start_proc(self, port_num):
        self.user_port = port_num
        self.process = subprocess.Popen(
            "python listener.py {} {}".format(port_num, 'chat-'+port_num+'.tmp'),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # remember chat filename
        self.chat_file_name = 'chat'+port_num+'.tmp'
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

        # let's check user connection by looking for chat_name.tmp file
        if self.chat_file_name in os.listdir(path='.'):
            self.connected = True
        return [self.working, self.connected]

    # if we need to understand what's going on - get all attributes
    def show_attr(self):
        print('user_id ', self.user_id)
        print('user_nick ', self.user_nick)
        print('user_port ', self.user_port)
        print('establish', self.working)
        print('connected', self.connected)
        print('msg_id', self.msg_id)
        print('process', self.process)
        print('proc_pid', self.proc_pid)

# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-


# процессы
processes = []
# номера портов
# ports_list = ['25901', '25902', '25903', '25904', '25905', '25906', '25907', '25908', '25909', '25910']
ports_list = ['25901']
# последнее сообщение, порт, ник
users = []

# we should delete all old .tmp files with old chat logs.
list_tmp_files = [x for x in os.listdir(path='.') if x.endswith('.tmp')]
for tmp_file in list_tmp_files:
    os.remove(tmp_file)


for port in ports_list:
    # # стартуем процессы
    # proc = subprocess.Popen("python listener.py {} {}".format(port, 'chat'+port+'.txt'))
    # processes.append([proc, proc.pid, port])
    # print('proc = ', proc.pid)
    # print('process', processes)
    new_user = User(random.randint(0, 100))
    users.append(new_user)
    new_user.start_proc(port)
    # new_user.show_attr()

print(users)

for user in users:
    print('before kill',user.check_proc())
    time.sleep(10.0)
    print('kill!')
    user.stop_proc()
    print('after kill',user.check_proc())


print('END')