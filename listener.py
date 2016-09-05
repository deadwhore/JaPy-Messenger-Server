# -*- coding: utf-8 -*-
import socket
import argparse
import json
from datetime import datetime
import time


def telprint(connection, telsend):
    print('>>> SENDING: ' + telsend)
    # отсылаем строку
    telsend += '\r\n'
    try:
        # with open('log.txt', 'a') as log:
        #     if isinstance(telsend, list):
        #         for elem in telsend:
        #             log.write(elem)
        #         else:
        #             log.write(telsend)
            connection.send(telsend.encode(encoding='utf-8', errors='strict'))
            # log.close()
            return True
    except ConnectionResetError:
        print('Remote host disconnected!')
        return False
    except ConnectionAbortedError:
        print('Remote host disconnected!')
        return False


def telinput(connection, chat_file):
    # рисуем курсор
    # try:
    #     connection.send('> '.encode(encoding='utf-8', errors='strict'))
    # except ConnectionAbortedError:
    #     return ["Remote host disconnected!", False]
    # создаём переменную, в которую будем сливать декодированные данные
    data_utf = ''

    # цикл получения данных
    while True:
        # переменная для байт
        data = b''
        # запихиваем туда всё, что прилетело в сокет. проблема в том, что каждый телнет клиент передаёт многое ненужное
        # поэтому мы получаем в цикле все данные, все строки (ибо виндовый телнет клиент, например, передаёт каждую
        # букву новой строкой)
        try:
            data += connection.recv(1024)
        # таймаут
        except socket.timeout:
            print('Session timeout!')
            return ['SessionTimeout', False]
        except ConnectionResetError:
            print('Remote host disconnected!')
            return ["Remote host disconnected!", False]

        # если разорвано соединение вываливаемся из цикла
        if not data:
            print('User abort session by ^Z')
            return ['SessionAborted', False]

        # если мы можем декодировать по utf-8
        try:
            # декодируем и кидаем в переменную
            data_utf += data.decode('utf-8')
            # если обнаружили в ней перевод строки - вываливаемся из цикла - данные приняты
            if '\n' in data_utf:
                break
        # если декодировать по utf-8 не смогли - вываливаемся с ошибкой
        except UnicodeDecodeError:
            print('UnicodeDecodeError')
            return ['SessionAborted', False]

    # новая переменная, где уже не будет лишних нечитаемых символов
    norm_string = ''

    # идём по каждому символу, если они не нечитаемые - добавляем в норм_стринг
    for symbol in data_utf:
        if not symbol.isspace() or ' ':
            norm_string += symbol
    # запишем в лог что ввёл пользователь
    print('>>> user input [' + str(norm_string).strip() + ']')

    # now I think that we don't need a client's time, we need listener time, so adding that time
    # I won't remove clients time for now, maybe in future.
    from_json = json2string(norm_string)
    from_json['lstnr_time'] = get_time()

    # writing it to chat file if we have not usefull update_request messages and return
    if from_json['msg_text'] != 'UPDATE_REQUEST':
        chat_write(chat_file, json.dumps(from_json))
    return [from_json, True]

    # chat_write(chat_file, norm_string)
    # return [json2string(norm_string), True]


# метод получения параметров из JSON
def json2string(in_json):
    return json.loads(in_json)


# пишем в фаил
def chat_write(file, string):
    file.write(string + '\n')
    file.flush()


# method for getting date and time
def get_time():
    now_time = datetime.now()
    date = now_time.date()
    hour = now_time.hour
    minutes = now_time.minute
    seconds = now_time.second
    return '{} {}:{}:{}'.format(date, hour, minutes, seconds)


# to provide some listener information to file in json
def lstnr_print2json(chat_filename, id, port, string):
    date = get_time()
    msg_id = id
    cl_time = 'Unknown'
    srv = True
    user = 'Listener' + str(port)
    chat_write(chat_filename, json.dumps(
        {'cl_time': cl_time,
         'msg_id': msg_id,
         'srv_tag': srv,
         'user_nick': user,
         'lstnr_time': date,
         'msg_text': string}
    ))


# to send some service information to client
def lstnr_send_srv(port, string):
    date = get_time()
    msg_id = 0
    cl_time = 'Unknown'
    srv = True
    user = 'Listener' + str(port)
    return json.dumps(
        [{'cl_time': cl_time,
         'msg_id': msg_id,
         'srv_tag': srv,
         'user_nick': user,
         'lstnr_time': date,
         'msg_text': string}]
    )


# open syncronized chat and get new messages
def get_new_messages(msg_id):
    # flag of new messages
    new_msg_flag = False
    # start find from ours last msg id
    num_srv_msg_id = msg_id
    # new empty string
    messages = []
    with open('chat.txt', 'r') as chat_file:
        for line in chat_file.readlines():
            # deserialize json
            print(line)
            deserial_line = json.loads(line)
            # got a new message?
            if deserial_line['srv_msg_id'] > num_srv_msg_id:
                print('NEW MESSAGE')
                new_msg_flag = True
                messages.append(deserial_line)
                num_srv_msg_id = deserial_line['srv_msg_id']
    chat_file.close()
    if new_msg_flag:
        return [json.dumps(messages), num_srv_msg_id]
    else:
        return ['', num_srv_msg_id]

# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

# # если надо работать с программой вручную
# sock_port = 25901
# chat_file_name = "chat-" + str(sock_port) + ".tmp"

# если работаем в подпроцессорном режиме
# получаем данные из параметров вызова
parser = argparse.ArgumentParser()
parser.add_argument("port")
parser.add_argument("file")
args = parser.parse_args()
# назначаем переменным данные из параметров
sock_port = int(args.port)
chat_file_name = args.file



# number of message in global chat
srv_msg_id = 0



# with open(chat_file_name, 'w', encoding='utf-8') as chat_file:
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# chat_write(chat_file, 'Open socket ' + str(sock_port))

# с какого IP и порта будут ожидаться подключения, если айпи пуст - со всех возможных адресов
try:
    sock.bind(('', sock_port))
except OSError:
    print('Port ', sock_port, 'is busy!')

sock.setblocking(1)
# ждём подключения, только один может встать в очередь, остальных кикнет
sock.listen(0)

# подключился кто-то
conn, address = sock.accept()
sock.close()
try:

    # ставим таймаут подключения в 10 минут
    conn.settimeout(600)
    with open(chat_file_name, 'w', encoding='utf-8') as chat_file:
        print("User connected from " + address[0])
        lstnr_print2json(chat_file, 0, sock_port, "User connected from " + address[0])

        # ждём ввода каких-нибудь первых данных и пишем приветствие.
        # ждём данных потому что путти сразу посылает какие-то служебные данные

        # стартуем цикл принятия первых данных
        enter = ['', True]
        # while enter[1]:
        while True:
            # ждём данных
            enter = telinput(conn, chat_file)
            # checking, no errors in input
            if enter[1]:
                # service message comes
                if enter[0]['srv_tag']:
                    print('SERVICE TAG!')
                    if enter[0]['msg_text'] == 'COMING!':
                        lstnr_print2json(chat_file, 0, sock_port, "NEW USER:" + enter[0]['user_nick'])
                #
                new_messages = get_new_messages(srv_msg_id)
                # we have new messages?
                if len(new_messages[0]) > 0:
                    srv_msg_id = new_messages[1]
                    telprint(conn, new_messages[0])
                else:
                    print(lstnr_send_srv(sock_port, 'NO_NEW_MESSAGES'))
                    telprint(conn, lstnr_send_srv(sock_port, 'NO_NEW_MESSAGES'))
            else:
                break

        print('-----------------------------------')
        print('Session closed')
        lstnr_print2json(chat_file, -1, sock_port, "User disconnected")

finally:
    # завершаем подключение и сокет
    # chat_write(chat_file, "User disconnected ")
    conn.close()
    # sock.close()
