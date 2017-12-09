#!/usr/bin/env python
# -*- coding: utf-8 -*-
#скрипт для сбора конфигурации с микротиков при помощи pexpect

import getpass
import pexpect
import sys
import re
import os
import sqlite3
import datetime


ip_addresses = []

# На вход функции должны прийти mac, ip, configuration, datetime
# в виде списка или кортежа
def save_data_in_database(data, database = 'mikrotik_database.db'):

    if os.path.isfile(database):
        connection = sqlite3.connect(database)
        cursor = connection.cursor()

        query = "INSERT INTO devices VALUES (?, ?, ?, ?)"    
        try:
            cursor.execute(query, data)
            print('Данные добавлены в базу')
        except sqlite3.IntegrityError as error:
            print(error, '\nДанные существуют')        

        connection.commit()
        connection.close()
    else:
        print('БД не существует. Перед добавлением данных ее сначала нужно создать ')


# функция подключается к микротику, выполняет команду и возвращает ее результат
def connect_to_device(connection_command, password):
    with pexpect.spawn(connection_command, encoding='utf-8') as ssh:
        answer = ssh.expect(['password', 'continue connecting'])
        if answer == 0:
            ssh.sendline(password)
        else:
            ssh.sendline('yes')
            ssh.expect(['password', 'Password'])
            ssh.sendline(password)

        ssh.expect('\[admin@.+\]\s+>')
        # Отправляем нужную команду с символами перевода строки
        ssh.sendline('export compact\r\n')
        # Ищем приглашение системы два раза. По всей видимости, первый раз
        # это какое-то служебное приглашение. на экран терминалов не выводится
        # Второе приглашение - то, что нужно
        ssh.expect('\[admin@.+\]\s+>')
        ssh.expect('\[admin@.+\]\s+>')
        result = ssh.before    
    return (result)

# выделяем mac адрес устройства
def configuration_parse(data):
    for line in data.split('\n'):   
        try:            
            match = re.search('(\S\S:){5}\S\S', line).group(0)
            break
        except AttributeError as e:
            pass
    return (match)


# Запрашиваем у пользователя данные для авторизации на устройстве. 
# На основе данных формируем строку команды для подключения по ssh
username = input('Username: ')
password = getpass.getpass()
user_input= input('IP address: ')
port = input('Port: ')

if os.path.isfile(user_input):
    with open(user_input, 'r') as f:
        ip_addresses = f.read().split('\n')
        print(ip_addresses)
else:   
    ip_addresses.append(user_input)


for address in ip_addresses:
    print('='*40)
    print('Подключаемся к устройству с IP адресом {} ...'.format(address))
    connection_command = 'ssh {}@{} -p {}'.format(username, address, port)
    
    # Формируем данные для сохранения в базе
    try:
        mikrotik_output = connect_to_device(connection_command, password)
        mac = configuration_parse(mikrotik_output)
        now = str(datetime.datetime.today().replace(microsecond=0)) 
        data = tuple([mac, address, mikrotik_output, now])
        print('Данные собраны успешно. Сохраняем их в базе')
    except pexpect.exceptions.TIMEOUT as error:
        print('Время истекло. Произошла ошибка подключения')
        continue
    except OSError as error:
        print (error)
        continue

    save_data_in_database(data)