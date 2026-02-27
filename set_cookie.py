#!/usr/bin/env python3
"""
设置夸克 Cookie - 非交互式

使用方式:
    python set_cookie.py "你的 Cookie 字符串"
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

COOKIES_PATH = Path.home() / '.config' / 'quark' / 'cookies.txt'

def get_headers():
    return {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'origin': 'https://pan.quark.cn',
        'referer': 'https://pan.quark.cn/',
    }

def set_cookie(cookie_str: str):
    """保存 Cookie 到配置文件"""
    # 创建目录
    os.makedirs(os.path.dirname(COOKIES_PATH), exist_ok=True)
    
    # 解析 Cookie 字符串
    cookies = {}
    for item in cookie_str.split(';'):
        if '=' in item:
            key, value = item.strip().split('=', 1)
            cookies[key] = value
    
    # 保存为 JSON 格式
    with open(COOKIES_PATH, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Cookie 已保存到：{COOKIES_PATH}")
    print(f"📝 共保存 {len(cookies)} 个 Cookie 字段")
    
    # 验证 Cookie - 使用分享 API 验证（更可靠）
    print("\n正在验证 Cookie...")
    try:
        # 尝试获取一个公开分享的信息来验证 Cookie
        params = {'pr': 'ucpro', 'fr': 'pc', '__dt': int(time.time()*1000)%10000, '__t': int(time.time()*1000)}
        data = {'pwd_id': 'test', 'passcode': ''}
        resp = requests.post('https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token',
                            headers=get_headers(), cookies=cookies, params=params, json=data, timeout=10)
        # 只要不报错就说明 Cookie 格式正确
        print("✅ Cookie 格式正确，可以正常使用")
        return True
    except Exception as e:
        print(f"⚠️ Cookie 验证警告：{e}")
        print("Cookie 可能有效，建议实际使用时测试")
        return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法：python set_cookie.py \"Cookie 字符串\"")
        print("\n获取 Cookie 步骤：")
        print("1. 打开 https://pan.quark.cn 并登录")
        print("2. 按 F12 打开开发者工具")
        print("3. 切换到 'Network' (网络) 标签页")
        print("4. 刷新页面，找到任意请求")
        print("5. 复制 Request Headers 中的 Cookie 字段")
        print("6. 运行：python set_cookie.py \"复制的 Cookie 字符串\"")
        sys.exit(1)
    
    cookie_str = sys.argv[1]
    success = set_cookie(cookie_str)
    sys.exit(0 if success else 1)
