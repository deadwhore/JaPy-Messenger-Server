# -*- coding: utf-8 -*-
import socket
import argparse
import json
from datetime import datetime
import time


def telprint(connection, telsend):
    # отсылаем строку
    telsend += '\r\n'
    try:
        connection.send(telsend.encode(encoding='utf-8', errors='strict'))
        return True
    except ConnectionResetError:
        print('Remote host disconnected!')
        return False
    except ConnectionAbortedError:
        print('Remote host disconnected!')
        return False


def telinput(connection, chat_file):
    # рисуем курсор
    try:
        connection.send('> '.encode(encoding='utf-8', errors='strict'))
    except ConnectionAbortedError:
        return ["Remote host disconnected!", False]
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

    # writing it to chat file and return
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
def lstnr_print2json(chat_filename, port, string):
    date = get_time()
    msg_id = 0
    cl_time = 'Unknown'
    srv = True
    user = 'Listener' + str(port)
    chat_write(chat_filename, json.dumps(
        {'cl_time': cl_time,
         'msg_id': msg_id,
         'srv': srv,
         'user_nick': user,
         'lstnr_time': date,
         'msg_text': string}
    ))

# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

# получаем данные из параметров вызова
parser = argparse.ArgumentParser()
parser.add_argument("port")
parser.add_argument("file")
args = parser.parse_args()
# назначаем переменным данные из параметров
sock_port = int(args.port)
chat_file_name = args.file

# # если надо работать с программой вручную
# sock_port = 25901
# chat_file_name = "chat-" + str(sock_port) + ".tmp"

# with open(chat_file_name, 'w', encoding='utf-8') as chat_file:
sock = socket.socket()
# chat_write(chat_file, 'Open socket ' + str(sock_port))

# с какого IP и порта будут ожидаться подключения, если айпи пуст - со всех возможных адресов
try:
    sock.bind(('', sock_port))
except OSError:
    print('Port ', sock_port, 'is busy!')

# ждём подключения, только один может встать в очередь, остальных кикнет
sock.listen(1)

# подключился кто-то
conn, address = sock.accept()
try:

    # ставим таймаут подключения в 10 минут
    conn.settimeout(600)
    with open(chat_file_name, 'w', encoding='utf-8') as chat_file:
        print("User connected from " + address[0])
        lstnr_print2json(chat_file, sock_port, "User connected from " + address[0])

        # ждём ввода каких-нибудь первых данных и пишем приветствие.
        # ждём данных потому что путти сразу посылает какие-то служебные данные
        conn_init = telinput(conn, chat_file)
        if conn_init[0]['msg_text'] == "INIT_SOCK":
            telprint(conn, 'INIT_ACCP')

        # стартуем цикл принятия первых данных
        enter = ['', True]
        # while enter[1]:
        while True:
            # ждём данных
            enter = telinput(conn, chat_file)
            # проверяем, нет ли ошибок при вводе
            if enter[1]:
                if enter[0]['msg_text'].strip() == "exit":
                    print('User exits')
                # данные получены
                elif telprint(conn, "You write to me: [" + enter[0]['msg_text'] + "], asshole!"):
                    continue
                break
            else:
                break

        print('-----------------------------------')
        print('Session closed')
        lstnr_print2json(chat_file, sock_port, "User disconnected")

finally:
    # завершаем подключение и сокет
    # chat_write(chat_file, "User disconnected ")
    conn.close()
    sock.close()
