#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在容器内调试API"""

import paramiko
import sys
import io
import time

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

NAS_HOST = "192.168.31.153"
NAS_PORT = 10000
NAS_USER = "15233616788"
NAS_PASS = "&*ETubd4"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(NAS_HOST, port=NAS_PORT, username=NAS_USER, password=NAS_PASS)

# 在容器内执行调试
cmd = '''sudo -S docker exec bilibili-dashboard python -c "
import requests
import json

cookie = ''
try:
    with open('/app/data/bilibili_cookie.txt', 'r') as f:
        cookie = f.read().strip()
except Exception as e:
    print('Cookie read error:', e)

print('Cookie loaded:', len(cookie), 'bytes')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://space.bilibili.com/662899682',
    'Origin': 'https://space.bilibili.com',
}
if cookie:
    headers['Cookie'] = 'SESSDATA=' + cookie

# 测试用户信息API
resp = requests.get('https://api.bilibili.com/x/space/acc/info?mid=662899682', headers=headers, timeout=15)
info_data = resp.json()
print('API_INFO response code:', info_data.get('code'))
print('API_INFO message:', info_data.get('message', 'OK'))

if info_data.get('code') == 0:
    data = info_data.get('data', {})
    print('Name:', data.get('name'))
    print('Face:', data.get('face'))
else:
    print('Full response:', json.dumps(info_data, ensure_ascii=False)[:500])
"'''
stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
stdin.write(NAS_PASS + '\n')
stdin.flush()
print(stdout.read().decode('utf-8'))

client.close()