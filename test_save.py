#!/usr/bin/env python3
"""
测试夸克转存功能
"""

import re
import json
import time
import requests
from pathlib import Path

COOKIES_PATH = Path.home() / '.config' / 'quark' / 'cookies.txt'

def load_cookies():
    if not COOKIES_PATH.exists():
        print(f"❌ Cookie 文件不存在：{COOKIES_PATH}")
        return {}
    with open(COOKIES_PATH, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if content.startswith('{'):
            return json.loads(content)
        cookies = {}
        for item in content.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key] = value
        return cookies

def get_headers():
    return {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'origin': 'https://pan.quark.cn',
        'referer': 'https://pan.quark.cn/',
    }

def get_stoken(cookies, pwd_id, password=''):
    """获取访问令牌"""
    params = {'pr': 'ucpro', 'fr': 'pc', '__dt': int(time.time()*1000)%10000, '__t': int(time.time()*1000)}
    data = {'pwd_id': pwd_id, 'passcode': password}
    resp = requests.post('https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token', 
                        headers=get_headers(), cookies=cookies, params=params, json=data)
    result = resp.json()
    if result.get('status') != 200:
        raise Exception(f"获取 stoken 失败：{result.get('message', '未知错误')}")
    return result['data']['stoken']

def get_files(cookies, pwd_id, stoken, pdir_fid='0'):
    """获取文件列表"""
    params = {'pr': 'ucpro', 'fr': 'pc', 'pwd_id': pwd_id, 'stoken': stoken, 
              'pdir_fid': pdir_fid, '_page': '1', '_size': '50'}
    resp = requests.get('https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail',
                       headers=get_headers(), cookies=cookies, params=params)
    result = resp.json()
    if result.get('status') != 200:
        raise Exception(f"获取文件列表失败：{result.get('message', '未知错误')}")
    return result['data']['list']

def save_files(cookies, pwd_id, stoken, fid_list, share_fid_tokens, to_pdir_fid='0'):
    """转存文件"""
    params = {'pr': 'ucpro', 'fr': 'pc'}
    data = {
        "pwd_id": pwd_id,
        "stoken": stoken,
        "fid_list": fid_list,
        "share_fid_token_list": share_fid_tokens,
        "to_pdir_fid": to_pdir_fid,
        "pdir_fid": "0",
        "scene": "link"
    }
    resp = requests.post('https://drive-pc.quark.cn/1/clouddrive/share/sharepage/save',
                        headers=get_headers(), cookies=cookies, params=params, json=data)
    result = resp.json()
    print(f"转存响应：{json.dumps(result, indent=2, ensure_ascii=False)}")
    if result.get('status') != 200:
        raise Exception(f"转存失败：{result.get('message', '未知错误')}")
    return result['data'].get('task_id', '')

def check_task(cookies, task_id):
    """查询任务状态"""
    params = {'pr': 'ucpro', 'fr': 'pc', 'task_id': task_id, 'retry_index': '0'}
    resp = requests.get('https://drive-pc.quark.cn/1/clouddrive/task',
                       headers=get_headers(), cookies=cookies, params=params)
    result = resp.json()
    print(f"任务状态：{json.dumps(result, indent=2, ensure_ascii=False)}")
    return result

def main():
    share_url = 'https://pan.quark.cn/s/0cb39ea5a2d9'
    target_dir_id = 'a373fb0d522f455ea2af639e9d061747'  # 来自：分享
    
    print(f"📁 分享链接：{share_url}")
    print(f"🎯 目标目录 ID: {target_dir_id}")
    
    # 解析分享链接
    match = re.match(r'https?://pan\.quark\.cn/s/([a-zA-Z0-9_-]+)', share_url)
    pwd_id = match.group(1) if match else None
    print(f"🔑 pwd_id: {pwd_id}")
    
    # 加载 Cookie
    cookies = load_cookies()
    if not cookies:
        print("❌ 未找到 Cookie")
        return
    
    # 获取 stoken
    print("\n🔐 获取访问令牌...")
    stoken = get_stoken(cookies, pwd_id)
    print(f"✅ stoken: {stoken[:30]}...")
    
    # 获取文件列表
    print("\n📂 获取文件列表...")
    files = get_files(cookies, pwd_id, stoken, '0')
    print(f"根目录有 {len(files)} 个项目")
    
    # 获取文件夹内容
    folder_fid = None
    for f in files:
        if f.get('dir', False):
            folder_fid = f['fid']
            print(f"找到文件夹：{f['file_name']} (FID: {folder_fid})")
            break
    
    if not folder_fid:
        print("❌ 未找到文件夹")
        return
    
    # 获取文件夹内的文件
    folder_files = get_files(cookies, pwd_id, stoken, folder_fid)
    print(f"\n文件夹内有 {len(folder_files)} 个文件")
    
    # 只显示前 3 个文件用于测试
    test_files = folder_files[:3]
    fid_list = [f['fid'] for f in test_files]
    share_fid_tokens = [f.get('share_fid_token', '') for f in test_files]
    
    print(f"\n📋 准备转存 {len(test_files)} 个文件:")
    for f in test_files:
        size = f.get('size', 0)
        size_str = f"{size/1024/1024/1024:.2f} GB" if size > 1024*1024*1024 else f"{size/1024/1024:.2f} MB"
        print(f"  - {f['file_name']} ({size_str})")
    
    # 执行转存
    print(f"\n🚀 开始转存到目录 {target_dir_id}...")
    task_id = save_files(cookies, pwd_id, stoken, fid_list, share_fid_tokens, target_dir_id)
    print(f"✅ 任务 ID: {task_id}")
    
    # 等待任务完成
    print("\n⏳ 等待任务完成...")
    for i in range(30):
        result = check_task(cookies, task_id)
        status = result.get('data', {}).get('status', 0)
        if status == 2:
            print("\n✅ 转存完成！")
            break
        elif status == 3:
            print("\n❌ 转存失败")
            break
        time.sleep(2)

if __name__ == '__main__':
    main()
