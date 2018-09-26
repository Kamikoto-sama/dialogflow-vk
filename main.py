#!/usr/bin/env python3.6
import requests
import sqlite3
import uuid

ACCESS_TOKEN = "VK_GROUP_ACCESS_TOKEN"
BOT_ID = "DIALOGFLOW_BOT_ID"
GROUP_ID = "VK_GROUP_ID"

conn = sqlite3.connect('sessions.db')
cur = conn.cursor()
longpoll = {}

cur.execute('''CREATE TABLE IF NOT EXISTS sessions
               (vkid text, ssid text)''')

def new_longpoll():
    reqparam = {
        'access_token': ACCESS_TOKEN,
        'v': '5.80',
        'group_id': GROUP_ID
    }
    r = requests.get('https://api.vk.com/method/groups.getLongPollServer',
                     params=reqparam)
    print(r.text)
    longpoll.update(r.json().get('response', {}))
    print('LongPoll was obtained')

def perform_answer(m):
    t = (m['from_id'],)
    session = cur.execute('''SELECT * FROM sessions
                             WHERE vkid=?''', t)
    sres = session.fetchone()
    if not sres:
        ssid = uuid.uuid4()
        p = (m['from_id'], ssid)
        cur.execute('INSERT INTO sessions VALUES (?, ?)', p)
        conn.commit()
    else:
        ssid = sres[1]
    reqparam = {
        'q': m['text'],
        'sessionId': ssid
    }
    r = requests.get(f'https://console.dialogflow.com/api-client/demo/embedded/{BOT_ID}/demoQuery',
                     params=reqparam)
    res = r.json()['result']['fulfillment']['speech']
    return res

def send(to, text):
    reqparam = {
        'access_token': ACCESS_TOKEN,
        'v': '5.80',
        'user_id': to,
        'message': text
    }
    r = requests.get('https://api.vk.com/method/messages.send',
                     params=reqparam)
    return 'response' in r.json()

new_longpoll()

while True:
    reqparam = {
        'act': 'a_check',
        'key': longpoll['key'],
        'ts': longpoll['ts'],
        'wait': '25'
    }
    r = requests.get(longpoll['server'], params=reqparam)
    res = r.json()
    if 'failed' in res:
        if res['failed'] == 1:
            longpoll['ts'] = res['ts']
            continue
        elif res['failed'] == 2 or res['failed'] == 3:
            new_longpoll()
            continue
    longpoll['ts'] = res['ts']
    for upd in res['updates']:
        if upd['type'] == 'message_new':
            msg = upd['object']
            if msg['from_id'] == f'-{GROUP_ID}':
                continue
            text_res = perform_answer(msg)
            print(f'Request: {msg["text"]}')
            send(msg['from_id'], text_res)
            print(f'Response: {text_res}')
            print('==========')
