#!/usr/bin/env python3
"""
测试夸克 API - 直接使用 QuarkPanTool 的 API 格式
"""

import json
import re
import time
import requests
from pathlib import Path

# Cookie 文件路径
COOKIES_PATH = Path.home() / ".config" / "quark" / "cookies.txt"

def load_cookies() -> dict:
    """加载 Cookie"""
    if not COOKIES_PATH.exists():
        print(f"❌ Cookie 文件不存在：{COOKIES_PATH}")
        return {}
    
    with open(COOKIES_PATH, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if content.startswith('{'):
            return json.loads(content)
        else:
            cookies = {}
            for item in content.split(';'):
                if '=' in item:
                    key, value = item.strip().split('=', 1)
                    cookies[key] = value
            return cookies

def get_headers():
    """获取请求头"""
    return {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'origin': 'https://pan.quark.cn',
        'referer': 'https://pan.quark.cn/',
        'accept-language': 'zh-CN,zh;q=0.9',
    }

def get_stoken(pwd_id: str, password: str = '') -> str:
    """获取访问令牌"""
    cookies = load_cookies()
    if not cookies:
        raise Exception("未找到 Cookie")
    
    url = "https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token"
    params = {
        'pr': 'ucpro',
        'fr': 'pc',
        'uc_param_str': '',
        '__dt': int(time.time() * 1000) % 10000,
        '__t': int(time.time() * 1000),
    }
    data = {"pwd_id": pwd_id, "passcode": password or ""}
    
    response = requests.post(url, headers=get_headers(), cookies=cookies, params=params, json=data)
    result = response.json()
    
    print(f"📋 Token 响应：{json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if result.get('status') != 200:
        raise Exception(f"获取 stoken 失败：{result.get('message', '未知错误')}")
    
    return result['data']['stoken']

def get_file_list(pwd_id: str, stoken: str, pdir_fid: str = '0'):
    """获取文件列表"""
    cookies = load_cookies()
    if not cookies:
        raise Exception("未找到 Cookie")
    
    url = "https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail"
    params = {
        'pr': 'ucpro',
        'fr': 'pc',
        'pwd_id': pwd_id,
        'stoken': stoken,
        'pdir_fid': pdir_fid,
        '_page': '1',
        '_size': '50',
        '_sort': 'file_type:asc,updated_at:desc',
    }
    
    response = requests.get(url, headers=get_headers(), cookies=cookies, params=params)
    result = response.json()
    
    print(f"\n📋 详情响应：{json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if result.get('status') != 200:
        raise Exception(f"获取文件列表失败：{result.get('message', '未知错误')}")
    
    return result['data']['list']

def main():
    share_url = "https://pan.quark.cn/s/4a5fcaa2b07b"
    
    # 解析分享链接
    match = re.match(r'https?://pan\.quark\.cn/s/([a-zA-Z0-9_-]+)', share_url)
    if not match:
        print("❌ 无效的分享链接")
        return
    
    pwd_id = match.group(1)
    print(f"📁 分享 ID: {pwd_id}")
    
    # 提取密码（如果有）
    password = ''
    pwd_match = re.search(r'[?&]pwd=([^&]+)', share_url)
    if pwd_match:
        password = pwd_match.group(1)
        print(f"🔑 提取码：{password}")
    
    # 获取 stoken
    print("\n🔐 正在获取访问令牌...")
    try:
        stoken = get_stoken(pwd_id, password)
        print(f"✅ stoken: {stoken[:20]}...")
    except Exception as e:
        print(f"❌ 失败：{e}")
        return
    
    # 获取文件列表
    print("\n📂 正在获取文件列表...")
    try:
        files = get_file_list(pwd_id, stoken)
        
        print(f"\n✅ 获取到 {len(files)} 个文件/文件夹:")
        print("=" * 80)
        print(f"{'序号':<5} {'名称':<50} {'大小':>15} {'类型':<10}")
        print("=" * 80)
        
        for i, f in enumerate(files, 1):
            name = f.get('file_name', '未知')[:48]
            size = f.get('size', 0)
            size_str = f"{size / 1024 / 1024:.2f} MB" if size > 0 else '-'
            ftype = '📁 文件夹' if f.get('dir', False) else '📄 文件'
            print(f"{i:<5} {name:<50} {size_str:>15} {ftype:<10}")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 失败：{e}")

if __name__ == '__main__':
    main()
