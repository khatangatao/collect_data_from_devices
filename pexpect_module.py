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
from sys import argv
import argparse



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
            print(error, '\nДанные существуют\n')        

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

        ssh.expect('\[\S+@.+\]\s+>')
        # Отправляем нужную команду с символами перевода строки
        ssh.sendline('export compact\r\n')
        # Ищем приглашение системы два раза. Почему оно выводится два раза - не понимаю
        ssh.expect('\[\S+@.+\]\s+>')
        ssh.expect('\[\S+@.+\]\s+>')

        result = ssh.before
        ssh.sendline('quit\r\n')  
        # ssh.close(force=True) 
        print('Отключаемся от устройства') 
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


# Главная функция. 
def collect_data_from_devices(username, password, ip_addresses, port):
    for address in ip_addresses:
        print('='*72)
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
            print('Время истекло. Произошла ошибка подключения\n')
            continue
        except pexpect.exceptions.EOF:
            print('Ошибка EOF\n')
            continue

        save_data_in_database(data)  


# Сбор данных устройст, которые находятся за vpn
def collect_data_from_devices_vpn(username_vpn, password_vpn, vpn_gateway, username, password, ip_addresses, port):
    print('Подключаемся к шлюзу VPN с IP адресом {} ...'.format(vpn_gateway))
    connection_command = 'ssh {}@{}'.format(username_vpn, vpn_gateway)
    
    with pexpect.spawn(connection_command, encoding='utf-8') as ssh:
        answer = ssh.expect(['password', 'continue connecting'])
        if answer == 0:
            ssh.sendline(password_vpn)
        else:
            ssh.sendline('yes')
            ssh.expect(['password'])
            ssh.sendline(password_vpn)

        for address in ip_addresses:
            ssh.expect('\[\S+@.+\]\$')
            print('='*72)
            print('Подключаемся к устройству с IP адресом {} ...'.format(address))
            ssh.sendline('ssh {}@{} -p {}'.format(username, address, port))
            ssh.expect(['password'])
            ssh.sendline(password)

            ssh.expect('\[\S+@.+\]\s+>')
            # Отправляем нужную команду с символами перевода строки
            ssh.sendline('export compact\r\n')
            # Ищем приглашение системы два раза. Почему оно выводится два раза - не понимаю
            ssh.expect('\[\S+@.+\]\s+>')
            ssh.expect('\[\S+@.+\]\s+>')
            command_output  = ssh.before           

            ssh.sendline('quit\r\n')  
            # ssh.close(force=True) 
            print('Отключаемся от устройства')
            mac = configuration_parse(command_output)
            now = str(datetime.datetime.today().replace(microsecond=0)) 
            data = tuple([mac, address, command_output, now]) 
            save_data_in_database(data)  



# Обработка переданных пользователем аргументов
parser = argparse.ArgumentParser(description='collect_data_from_devices')
parser.add_argument('-v', action='store', dest='vpn_gateway')
parser.add_argument('-vu', action='store', dest='vpn_gateway_username')
parser.add_argument('-a', action='store', dest='destination', required=True)
args = parser.parse_args()

try:
    if args.vpn_gateway:
        print('Целевые устройства находятся в VPN')

        print('Введите учетные данные для авторизации на шлюзе VPN:')
        username_vpn = input('Username: ')
        password_vpn = getpass.getpass()


        print('Введите учетные данные для авторизации на целевых устройствах:')  
        username = input('Username: ')
        password = getpass.getpass()
        port = input('Port: ')


        if os.path.isfile(args.destination):
            with open(args.destination, 'r') as f:
                ip_addresses = f.read().split('\n')
                print(ip_addresses)
        else:   
            ip_addresses.append(args.destination)

        collect_data_from_devices_vpn(username_vpn, password_vpn, args.vpn_gateway, username, password, ip_addresses, port)
        sys.exit()
except IndexError:
    print('Целевые устройства доступны напрямую')


# Запрашиваем у пользователя данные для авторизации на устройстве. 
print('Введите учетные данные для авторизации на целевых устройствах:')
username = input('Username: ')
password = getpass.getpass()
port = input('Port: ')

if os.path.isfile(args.destination):
    with open(args.destination, 'r') as f:
        ip_addresses = f.read().split('\n')
        print(ip_addresses)
else:   
    ip_addresses.append(args.destination)

collect_data_from_devices(username, password, ip_addresses, port)