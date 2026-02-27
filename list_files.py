#!/usr/bin/env python3
"""
夸克分享链接文件列表 - 支持递归显示
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
    params = {'pr': 'ucpro', 'fr': 'pc', '__dt': int(time.time()*1000)%10000, '__t': int(time.time()*1000)}
    data = {'pwd_id': pwd_id, 'passcode': password}
    resp = requests.post('https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token', 
                        headers=get_headers(), cookies=cookies, params=params, json=data)
    result = resp.json()
    if result.get('status') != 200:
        raise Exception(f"获取 stoken 失败：{result.get('message', '未知错误')}")
    return result['data']['stoken']

def get_files(cookies, pwd_id, stoken, pdir_fid='0'):
    params = {'pr': 'ucpro', 'fr': 'pc', 'pwd_id': pwd_id, 'stoken': stoken, 
              'pdir_fid': pdir_fid, '_page': '1', '_size': '50'}
    resp = requests.get('https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail',
                       headers=get_headers(), cookies=cookies, params=params)
    result = resp.json()
    if result.get('status') != 200:
        raise Exception(f"获取文件列表失败：{result.get('message', '未知错误')}")
    return result['data']['list']

def format_size(size_bytes):
    if size_bytes > 1024*1024*1024:
        return f"{size_bytes/1024/1024/1024:.2f} GB"
    elif size_bytes > 1024*1024:
        return f"{size_bytes/1024/1024:.2f} MB"
    else:
        return f"{size_bytes/1024:.2f} KB"

def display_recursive(cookies, pwd_id, stoken, pdir_fid='0', prefix='', depth=0, max_depth=10, index_counter=[1]):
    """递归显示文件列表"""
    files = get_files(cookies, pwd_id, stoken, pdir_fid)
    
    for i, f in enumerate(files):
        name = f.get('file_name', '未知')
        fid = f.get('fid', '')
        size = f.get('size', 0)
        is_dir = f.get('dir', False)
        size_str = format_size(size) if size > 0 else '-'
        
        # 树形符号
        is_last = (i == len(files) - 1)
        branch = '└─ ' if is_last else '├─ '
        indent = '│  ' if not is_last else '   '
        
        if is_dir:
            print(f"{prefix}{branch}📁 {name}/")
            # 递归显示子文件夹
            display_recursive(cookies, pwd_id, stoken, fid, 
                            prefix + indent, depth + 1, max_depth, index_counter)
        else:
            idx = index_counter[0]
            index_counter[0] += 1
            print(f"{prefix}{branch}📄 {name} ({size_str}) [{idx}]")

def main():
    if len(sys.argv) < 2:
        print("用法：python list_files.py <分享链接> [--depth N]")
        print("示例：python list_files.py https://pan.quark.cn/s/xxxxx")
        print("      python list_files.py https://pan.quark.cn/s/xxxxx --depth 1")
        sys.exit(1)
    
    share_url = sys.argv[1]
    
    # 解析深度参数
    max_depth = 10
    if '--depth' in sys.argv:
        depth_idx = sys.argv.index('--depth')
        if depth_idx + 1 < len(sys.argv):
            max_depth = int(sys.argv[depth_idx + 1])
    
    # 解析分享链接
    match = re.match(r'https?://pan\.quark\.cn/s/([a-zA-Z0-9_-]+)', share_url)
    if not match:
        print("❌ 无效的分享链接")
        sys.exit(1)
    
    pwd_id = match.group(1)
    print(f"📁 分享 ID: {pwd_id}")
    
    # 提取密码
    password = ''
    pwd_match = re.search(r'[?&]pwd=([^&]+)', share_url)
    if pwd_match:
        password = pwd_match.group(1)
        print(f"🔑 提取码：{password}")
    
    # 加载 Cookie
    cookies = load_cookies()
    if not cookies:
        print("❌ 未找到 Cookie，请先运行：python set_cookie.py \"Cookie 字符串\"")
        sys.exit(1)
    
    # 获取 stoken
    print("\n🔐 正在获取访问令牌...")
    try:
        stoken = get_stoken(cookies, pwd_id, password)
        print(f"✅ 成功")
    except Exception as e:
        print(f"❌ 失败：{e}")
        sys.exit(1)
    
    # 获取并显示文件列表
    print(f"\n📂 文件列表（最大深度：{max_depth}）:")
    print("=" * 80)
    
    try:
        display_recursive(cookies, pwd_id, stoken, '0', '', 0, max_depth)
        print("=" * 80)
    except Exception as e:
        print(f"❌ 获取文件列表失败：{e}")
        sys.exit(1)

if __name__ == '__main__':
    import sys
    main()
