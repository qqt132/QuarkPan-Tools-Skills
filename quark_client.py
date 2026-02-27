#!/usr/bin/env python3
"""
夸克网盘客户端 - 封装夸克网盘 API 调用
支持分享链接解析、文件列表获取、转存、目录管理等功能

修复说明：修正 API 调用方式，确保 GET 请求使用 params，POST 请求使用 json + params
参考 test_save.py 的正确实现方式
"""

import os
import re
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass
class QuarkFileInfo:
    """夸克文件信息"""
    fid: str  # 文件ID
    name: str  # 文件名
    size: int  # 文件大小（字节）
    type: str  # 文件类型（file/folder）
    is_file: bool  # 是否为文件
    pdir_fid: str  # 父目录ID


class QuarkClient:
    """
    夸克网盘客户端
    
    主要功能：
    - Cookie 管理（保存/检查/更新）
    - 分享链接解析
    - 文件列表获取
    - 文件转存
    - 目录管理
    """
    
    # 夸克网盘 API 基础 URL（PC 端）
    API_BASE_URL = "https://drive-pc.quark.cn/1/clouddrive"
    
    # API 端点
    ENDPOINTS = {
        'sharepage_token': "/share/sharepage/token",  # 获取访问令牌
        'sharepage_detail': "/share/sharepage/detail",  # 获取分享链接文件详情
        'sharepage_save': "/share/sharepage/save",  # 转存文件
        'task': "/task",  # 查询任务状态
        'list': "/file/sort",  # 获取目录列表
        'create_dir': "/file",  # 创建目录
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Origin": "https://pan.quark.cn",
        "Referer": "https://pan.quark.cn/",
    }
    
    def __init__(self, cookies_path: str = "~/.config/quark/cookies.txt"):
        """
        初始化夸克客户端
        
        Args:
            cookies_path: Cookie 文件路径
        """
        self.cookies_path = os.path.expanduser(cookies_path)
        self.cookies = {}
        self.user_info = None
        self._load_cookies()
    
    def _load_cookies(self) -> None:
        """从文件加载 Cookie"""
        try:
            if os.path.exists(self.cookies_path):
                with open(self.cookies_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # 支持两种格式：JSON 或单行 Cookie
                    if content.startswith('{'):
                        self.cookies = json.loads(content)
                    else:
                        # 解析单行 Cookie
                        for item in content.split(';'):
                            if '=' in item:
                                key, value = item.strip().split('=', 1)
                                self.cookies[key] = value
        except Exception as e:
            print(f"⚠️ 读取 Cookie 文件失败: {e}")
            self.cookies = {}
    
    def _save_cookies(self) -> None:
        """保存 Cookie 到文件"""
        try:
            os.makedirs(os.path.dirname(self.cookies_path), exist_ok=True)
            with open(self.cookies_path, 'w', encoding='utf-8') as f:
                json.dump(self.cookies, f, indent=2, ensure_ascii=False)
            print(f"✅ Cookie 已保存到: {self.cookies_path}")
        except Exception as e:
            print(f"❌ 保存 Cookie 失败: {e}")
    
    def _request(self, endpoint: str, method: str = "POST", 
                 data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        """
        发起 API 请求
        
        Args:
            endpoint: API 端点名称
            method: HTTP 方法
            data: 请求体数据（POST JSON）
            params: URL 参数（GET 参数）
            
        Returns:
            API 响应数据（JSON）
        """
        url = f"{self.API_BASE_URL}{self.ENDPOINTS[endpoint]}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(
                    url=url,
                    headers=self.headers,
                    cookies=self.cookies,
                    params=params,
                    timeout=30
                )
            else:
                response = requests.post(
                    url=url,
                    headers=self.headers,
                    cookies=self.cookies,
                    params=params,
                    json=data,
                    timeout=30
                )
            result = response.json()
            
            # 检查 API 返回码（兼容 status 和 code）
            status_code = result.get('status') or result.get('code')
            if status_code == 401:
                raise Exception("Cookie 已失效，请重新登录")
            elif status_code == 403:
                raise Exception("没有权限，请检查 Cookie")
            elif status_code != 200:
                raise Exception(f"API 错误: {result.get('message', result.get('msg', '未知错误'))}")
            
            # 兼容不同格式的响应数据
            if 'data' in result:
                return result['data']
            elif 'result' in result and 'data' in result['result']:
                return result['result']['data']
            return {}
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"解析响应失败: {e}")
    
    def login(self) -> bool:
        """
        验证 Cookie 是否有效
        
        Returns:
            True: Cookie 有效
            False: Cookie 失效
        """
        if not self.cookies:
            print("⚠️ 未找到 Cookie，请先登录")
            return False
        
        try:
            # 使用 GET 方法验证用户目录列表 API（参考 test_save.py）
            url = f"{self.API_BASE_URL}/file/sort"
            params = {
                'pr': 'ucpro',
                'fr': 'pc',
                'pdir_fid': '0',
                '_page': 1,
                '_size': 10,
            }
            
            response = requests.get(
                url=url,
                headers=self.headers,
                cookies=self.cookies,
                params=params,
                timeout=30
            )
            result = response.json()
            
            # 兼容 status 和 code
            status_code = result.get('status') or result.get('code')
            if status_code == 200:
                self.user_info = result.get('data', {})
                print("✅ Cookie 验证成功")
                return True
            elif status_code == 401:
                print("❌ Cookie 已失效")
                return False
            else:
                print(f"❌ Cookie 验证失败: {result.get('message', result.get('msg', '未知错误'))}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Cookie 验证失败: 网络错误 - {e}")
            self.cookies = {}
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Cookie 验证失败: 响应解析失败 - {e}")
            return False
    
    def manual_login(self) -> bool:
        """
        手动登录（从浏览器复制 Cookie）
        
        Returns:
            True: 登录成功
            False: 登录失败
        """
        print("\n" + "="*60)
        print("📖 手动登录步骤：")
        print("  1. 打开 https://pan.quark.cn 并登录")
        print("  2. 按 F12 打开开发者工具")
        print("  3. 切换到 'Network' (网络) 标签页")
        print("  4. 刷新页面，找到任意请求的 Cookie")
        print("  5. 复制 Cookie 字符串")
        print("  6. 粘贴到下方（不会显示在屏幕上）")
        print("="*60 + "\n")
        
        try:
            cookie_str = input("请输入 Cookie 字符串: ").strip()
            if not cookie_str:
                print("❌ Cookie 不能为空")
                return False
            
            # 解析 Cookie 字符串
            for item in cookie_str.split(';'):
                if '=' in item:
                    key, value = item.strip().split('=', 1)
                    self.cookies[key] = value
            
            self._save_cookies()
            return self.login()
            
        except KeyboardInterrupt:
            print("\n❌ 登录已取消")
            return False
        except Exception as e:
            print(f"❌ 登录失败: {e}")
            return False
    
    def parse_share_url(self, url: str) -> Dict:
        """
        解析夸克分享链接
        
        Args:
            url: 分享链接，例如: https://pan.quark.cn/s/xxxxx 或 https://pan.quark.cn/s/xxxxx?pwd=1234
            
        Returns:
            dict: 包含 pwd_id 和 password 的字典
        """
        url = url.strip()
        
        # 匹配分享链接格式
        match = re.match(r'https?://pan\.quark\.cn/s/([a-zA-Z0-9_-]+)', url)
        if not match:
            raise ValueError("无效的夸克分享链接格式")
        
        pwd_id = match.group(1)
        
        # 提取提取码
        password = ''
        pwd_match = re.search(r'[?&]pwd=([^&]+)', url)
        if pwd_match:
            password = pwd_match.group(1)
        
        return {
            'pwd_id': pwd_id,
            'password': password
        }

    def get_stoken(self, pwd_id: str, password: str = '') -> str:
        """
        获取访问令牌 (stoken)
        
        Args:
            pwd_id: 分享链接 ID
            password: 提取码（可选）
            
        Returns:
            stoken: 访问令牌
            
        Raises:
            Exception: 获取失败时抛出异常
        """
        url = f"{self.API_BASE_URL}/share/sharepage/token"
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            '__dt': int(time.time() * 1000) % 10000,
            '__t': int(time.time() * 1000),
        }
        
        data = {
            "pwd_id": pwd_id,
            "passcode": password or ""
        }
        
        response = requests.post(
            url=url,
            headers=self.headers,
            cookies=self.cookies,
            params=params,
            json=data,
            timeout=30
        )
        result = response.json()
        
        # 兼容 status 和 code
        status_code = result.get('status') or result.get('code')
        if status_code != 200:
            error_msg = result.get('message', result.get('msg', '未知错误'))
            if '密码' in error_msg or 'passcode' in error_msg:
                raise Exception("提取码错误")
            raise Exception(f"获取 stoken 失败: {error_msg}")
        
        # 兼容不同格式的响应
        if 'data' in result:
            return result['data']['stoken']
        elif 'result' in result and 'data' in result['result']:
            return result['result']['data']['stoken']
        return result['data']['stoken']

    def get_file_list(self, pwd_id: str, stoken: str, 
                      pdir_fid: str = '0', page: int = 1, size: int = 50) -> List[Dict]:
        """
        获取分享链接中的文件列表
        
        Args:
            pwd_id: 分享链接 ID
            stoken: 访问令牌
            pdir_fid: 父目录 ID（默认为根目录 '0'）
            page: 页码
            size: 每页数量
            
        Returns:
            List[Dict]: 文件列表
            
        Raises:
            Exception: 获取失败时抛出异常
        """
        url = f"{self.API_BASE_URL}/share/sharepage/detail"
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'pwd_id': pwd_id,
            'stoken': stoken,
            'pdir_fid': pdir_fid,
            '_page': page,
            '_size': size,
        }
        
        response = requests.get(
            url=url,
            headers=self.headers,
            cookies=self.cookies,
            params=params,
            timeout=30
        )
        result = response.json()
        
        # 兼容 status 和 code
        status_code = result.get('status') or result.get('code')
        if status_code != 200:
            raise Exception(f"获取文件列表失败: {result.get('message', result.get('msg', '未知错误'))}")
        
        # 返回原始 list
        return result.get('data', {}).get('list', [])

    def get_all_files_recursive(self, pwd_id: str, stoken: str, 
                                pdir_fid: str = '0', depth: int = 0, 
                                max_depth: int = -1) -> List[Dict]:
        """
        递归获取所有文件（包括子文件夹）
        
        Args:
            pwd_id: 分享链接 ID
            stoken: 访问令牌
            pdir_fid: 当前目录 ID
            depth: 当前深度（从 0 开始）
            max_depth: 最大深度（-1 表示无限，0 表示只显示当前层，1 表示显示当前层和下一层）
            
        Returns:
            List[Dict]: 所有文件的列表
        """
        all_files = []
        
        # 检查深度限制（max_depth <= 0 时只获取当前层）
        if max_depth != -1 and depth >= max_depth:
            # 仍然获取当前层的文件，只是不递归
            pass
        
        try:
            files = self.get_file_list(pwd_id, stoken, pdir_fid)
            
            for file in files:
                # 使用原始 file_name 和 fid 字段（API 返回的字段名）
                file_name = file.get('file_name') or file.get('name')
                fid = file.get('file_id') or file.get('fid')
                
                converted_file = {
                    # 使用 API 期望的字段名
                    'file_name': file_name,
                    'fid': fid,
                    'file_id': fid,  # 兼容两种字段名
                    'size': file.get('size', 0),
                    'type': file.get('type', 'file' if not file.get('dir', False) else 'folder'),
                    'is_file': file.get('type') == 'file' or not file.get('dir', False),
                    'pdir_fid': pdir_fid,
                    'obj_category': file.get('obj_category'),
                    'phone_play_url': file.get('play_lua', {}).get('phone_play_url'),
                    'dir': file.get('dir', False),
                    'share_fid_token': file.get('share_fid_token', ''),
                    'updated_at': file.get('updated_at'),
                    'created_at': file.get('created_at'),
                }
                
                if converted_file['is_file']:
                    all_files.append(converted_file)
                elif max_depth == -1 or depth < max_depth:
                    # 如果是文件夹且未达到最大深度，递归获取
                    all_files.extend(
                        self.get_all_files_recursive(pwd_id, stoken, converted_file['fid'], depth + 1, max_depth)
                    )
            
            return all_files
            
        except Exception as e:
            raise Exception(f"递归获取文件失败: {e}")

    def get_folder_tree(self, pwd_id: str, stoken: str, 
                        pdir_fid: str = '0', depth: int = 0, 
                        max_depth: int = -1) -> Dict:
        """
        获取完整的文件夹树结构（带路径）
        
        Args:
            pwd_id: 分享链接 ID
            stoken: 访问令牌
            pdir_fid: 当前目录 ID
            depth: 当前深度
            max_depth: 最大深度（-1 表示无限）
            
        Returns:
            Dict: 文件夹树结构
        """
        # 检查深度限制
        if max_depth != -1 and depth > max_depth:
            return None
        
        try:
            files = self.get_file_list(pwd_id, stoken, pdir_fid)
            
            tree = {
                'type': 'folder',
                'fid': pdir_fid if pdir_fid != '0' else None,
                'name': '根目录' if pdir_fid == '0' else '',
                'children': []
            }
            
            for item in files:
                converted = {
                    'fid': item.get('file_id') or item.get('fid'),
                    'name': item.get('file_name') or item.get('name'),
                    'size': item.get('size', 0),
                    'type': 'file' if item.get('type') == 'file' else 'folder',
                    'is_file': item.get('type') == 'file' or not item.get('dir', False),
                    'dir': item.get('dir', False),
                }
                
                if converted['is_file']:
                    tree['children'].append({
                        'type': 'file',
                        'fid': converted['fid'],
                        'name': converted['name'],
                        'size': converted['size'],
                        'size_str': format_size(converted['size']),
                    })
                else:
                    # 递归获取子文件夹
                    child_tree = self.get_folder_tree(pwd_id, stoken, converted['fid'], depth + 1, max_depth)
                    if child_tree:
                        tree['children'].append(child_tree)
            
            return tree
            
        except Exception as e:
            raise Exception(f"获取文件夹树失败: {e}")
    
    def save_files(self, pwd_id: str, stoken: str, fid_list: List[str],
                   share_fid_tokens: List[str], 
                   to_pdir_fid: str = '0') -> str:
        """
        转存文件到用户网盘
        
        Args:
            pwd_id: 分享链接 ID
            stoken: 访问令牌
            fid_list: 要转存的文件 ID 列表
            share_fid_tokens: 文件的访问令牌列表（与 fid_list 一一对应）
            to_pdir_fid: 目标目录 ID（默认为根目录 '0'）
            
        Returns:
            task_id: 转存任务 ID
            
        Raises:
            Exception: 转存失败时抛出异常
        """
        url = f"{self.API_BASE_URL}/share/sharepage/save"
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
        }
        
        data = {
            "pwd_id": pwd_id,
            "stoken": stoken,
            "fid_list": fid_list,
            "share_fid_token_list": share_fid_tokens,
            "to_pdir_fid": to_pdir_fid,
            "pdir_fid": "0",
            "scene": "link"
        }
        
        response = requests.post(
            url=url,
            headers=self.headers,
            cookies=self.cookies,
            params=params,
            json=data,
            timeout=30
        )
        result = response.json()
        
        # 兼容 status 和 code
        status_code = result.get('status') or result.get('code')
        if status_code != 200:
            error_msg = result.get('message', result.get('msg', '未知错误'))
            if '容量' in error_msg or '空间' in error_msg or 'space' in str(error_msg).lower():
                raise Exception("网盘容量不足")
            raise Exception(f"转存失败: {error_msg}")
        
        # 兼容不同格式的响应
        if 'data' in result:
            return result['data'].get('task_id', '')
        elif 'result' in result and 'data' in result['result']:
            return result['result']['data'].get('task_id', '')
        return result.get('data', {}).get('task_id', '')

    def check_task_status(self, task_id: str) -> Dict:
        """
        查询转存任务状态
        
        Args:
            task_id: 任务 ID
            
        Returns:
            Dict: 任务状态信息
        """
        url = f"{self.API_BASE_URL}/task"
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'task_id': task_id,
            'retry_index': '0',
        }
        
        response = requests.get(
            url=url,
            headers=self.headers,
            cookies=self.cookies,
            params=params,
            timeout=30
        )
        result = response.json()
        
        # 兼容不同格式的响应
        if 'data' in result:
            data = result['data']
        elif 'result' in result and 'data' in result['result']:
            data = result['result']['data']
        else:
            data = result
            
        status = data.get('status', data.get('task_status', 'unknown'))
        
        # 转换状态码
        status_map = {
            0: 'pending',
            1: 'processing',
            2: 'completed',
            3: 'failed',
            4: 'cancelled'
        }
        
        return {
            'status': status_map.get(status, 'unknown'),
            'progress': data.get('progress', data.get('percent', 0)),
            'message': data.get('message', data.get('msg', '')),
            'raw_status': status
        }
        
    def wait_task_complete(self, task_id: str, timeout: int = 300, 
                          on_progress=None) -> bool:
        """
        等待任务完成
        
        Args:
            task_id: 任务 ID
            timeout: 超时时间（秒）
            on_progress: 进度回调函数，接收 (progress, status, message) 参数
            
        Returns:
            bool: 任务是否成功完成
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.check_task_status(task_id)
            
            # 调用进度回调
            if on_progress:
                on_progress(status['progress'], status['status'], status['message'])
            
            if status['status'] == 'completed':
                print("✅ 转存完成！")
                return True
            elif status['status'] == 'failed':
                print(f"❌ 转存失败: {status['message']}")
                return False
            elif status['status'] == 'cancelled':
                print("❌ 转存已取消")
                return False
            
            # 显示进度
            print(f"⏳ 转存进度: {status['progress']}% - {status['message']}")
            time.sleep(2)
        
        print("❌ 转存超时")
        return False

    def get_user_dirs(self, pdir_fid: str = '0', prefix: str = '') -> List[Dict]:
        """
        获取用户网盘目录列表
        
        Args:
            pdir_fid: 父目录 ID
            prefix: 前缀路径
            
        Returns:
            List[Dict]: 目录列表
        """
        url = f"{self.API_BASE_URL}/file/sort"
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'pdir_fid': pdir_fid,
            '_page': 1,
            '_size': 100,
        }
        
        response = requests.get(
            url=url,
            headers=self.headers,
            cookies=self.cookies,
            params=params,
            timeout=30
        )
        result = response.json()
        
        dirs = []
        for item in result.get('data', {}).get('list', []):
            if item.get('type') == 'folder' or item.get('dir', False):
                current_path = f"{prefix}/{item.get('file_name')}" if prefix else f"/{item.get('file_name')}"
                dirs.append({
                    'fid': item.get('file_id') or item.get('fid'),
                    'name': item.get('file_name'),
                    'path': current_path,
                    'pdir_fid': pdir_fid
                })
                # 递归获取子目录
                dirs.extend(self.get_user_dirs(item.get('file_id') or item.get('fid'), current_path))
        
        return dirs

    def create_dir(self, dir_name: str, parent_fid: str = '0') -> str:
        """
        创建新目录
        
        Args:
            dir_name: 目录名称
            parent_fid: 父目录 ID
            
        Returns:
            str: 新目录的 ID
            
        Raises:
            Exception: 创建失败时抛出异常
        """
        url = f"{self.API_BASE_URL}/file"
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
        }
        
        data = {
            "pdir_fid": parent_fid,
            "file_name": dir_name,
            "_version": 2
        }
        
        response = requests.post(
            url=url,
            headers=self.headers,
            cookies=self.cookies,
            params=params,
            json=data,
            timeout=30
        )
        result = response.json()
        
        # 兼容 status 和 code
        status_code = result.get('status') or result.get('code')
        if status_code != 200:
            error_msg = result.get('message', result.get('msg', '未知错误'))
            if '存在' in error_msg:
                raise Exception("目录已存在")
            raise Exception(f"创建目录失败: {error_msg}")
        
        # 兼容不同格式的响应
        # 尝试多种可能的路径
        if 'data' in result:
            data_obj = result['data']
            # 尝试 file_id, fid, object_id 等字段
            return data_obj.get('file_id', data_obj.get('fid', data_obj.get('object_id', ''))) or data_obj.get('id', '')
        elif 'result' in result and 'data' in result['result']:
            data_obj = result['result']['data']
            return data_obj.get('file_id', data_obj.get('fid', data_obj.get('object_id', ''))) or data_obj.get('id', '')
        
        # 如果 data 是字符串，可能直接是 ID
        if isinstance(result.get('data'), str):
            return result['data']
        
        return result.get('data', {}).get('file_id', '')

    def get_dir_by_path(self, path: str) -> Optional[str]:
        """
        根据路径获取目录 ID
        
        Args:
            path: 目录路径，例如 "/我的视频/电影"
            
        Returns:
            str: 目录 ID，不存在返回 None
        """
        if not path or path == '/':
            return '0'
        
        parts = [p for p in path.split('/') if p]
        current_fid = '0'
        
        for part in parts:
            dirs = self.get_user_dirs(current_fid)
            found = False
            for d in dirs:
                if d['name'] == part:
                    current_fid = d['fid']
                    found = True
                    break
            if not found:
                return None
        
        return current_fid


# 全局函数：格式化文件大小
def format_size(size_bytes: int) -> str:
    """格式化文件大小为可读格式"""
    if size_bytes == 0:
        return '-'
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


# 全局函数：树形显示文件列表
def display_file_tree(tree: Dict, indent: str = '', is_last: bool = True) -> None:
    """
    以树形结构显示文件夹树
    
    Args:
        tree: 文件夹树
        indent: 缩进
        is_last: 是否是最后一个节点
    """
    if tree is None:
        return
    
    # 构建当前节点的前缀
    prefix = '└─ ' if is_last else '├─ '
    
    # 显示文件夹
    if tree.get('type') == 'folder':
        if tree.get('name'):
            print(f"{indent}{prefix}📁 {tree['name']}/")
        children = tree.get('children', [])
        for i, child in enumerate(children):
            is_child_last = (i == len(children) - 1)
            new_indent = indent + ('   ' if is_last else '│  ')
            display_file_tree(child, new_indent, is_child_last)
    
    # 显示文件
    elif tree.get('type') == 'file':
        size_str = format_size(tree.get('size', 0))
        print(f"{indent}{prefix}📄 {tree['name']} ({size_str})")
    
    # 显示树节点（带序号）
    elif 'children' in tree:
        children = tree.get('children', [])
        for i, child in enumerate(children):
            is_child_last = (i == len(children) - 1)
            display_file_tree(child, indent, is_child_last)


# 全局函数：显示文件列表（带序号）
def display_files(files: List[Dict], show_size: bool = True, 
                  show_index: bool = True) -> List[str]:
    """
    格式化显示文件列表
    
    Args:
        files: 文件列表
        show_size: 是否显示文件大小
        show_index: 是否显示序号
        
    Returns:
        List[str]: 序号映射表
    """
    if not files:
        print("📂 空目录")
        return []
    
    # 显示表头
    if show_index:
        print("\n" + "="*80)
        print(f"{'序号':<5} {'名称':<40} {'大小':>15} {'类型':<10}")
        print("="*80)
    else:
        print("\n" + "="*80)
        print(f"{'名称':<50} {'大小':>15} {'类型':<10}")
        print("="*80)
    
    # 序号映射表
    index_map = []
    
    for i, file in enumerate(files, 1):
        # 序号
        if show_index:
            index_str = f"[{i}]"
        else:
            index_str = ""
        
        # 兼容 'name' 和 'file_name' 字段
        name = (file.get('name') or file.get('file_name') or '未知')[:38]
        name = name + '..' if len(name) > 38 else name
        size = format_size(file.get('size', 0)) if file.get('size', 0) > 0 else '-'
        ftype = '📁 文件夹' if not file.get('is_file', True) else '📄 文件'
        
        if show_index:
            print(f"{index_str:<5} {name:<40} {size:>15} {ftype:<10}")
        else:
            print(f"  {name:<48} {size:>15} {ftype:<10}")
        
        index_map.append(str(i))
    
    if show_index:
        print("="*80)
        print(f"共 {len(files)} 个项目\n")
    else:
        print("="*80)
        print(f"共 {len(files)} 个项目\n")
    
    return index_map


# 全局函数：解析文件选择
def parse_file_selection(selection: str, files: List[Dict]) -> List[Dict]:
    """
    解析文件选择字符串
    
    Args:
        selection: 选择字符串，例如 "1,2,3" 或 "1-10" 或 "all" 或 "*.mkv"
        files: 文件列表
        
    Returns:
        List[Dict]: 选中的文件列表
    """
    selected = []
    
    # 全部选择
    if selection.lower() == 'all':
        return files.copy()
    
    # 按序号范围选择 (如 "1-10")
    range_match = re.match(r'^(\d+)-(\d+)$', selection)
    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2))
        start = max(1, min(start, len(files)))
        end = max(1, min(end, len(files)))
        for i in range(start, end + 1):
            if i <= len(files):
                selected.append(files[i - 1])
        return selected
    
    # 按序号选择 (如 "1,2,3")
    if ',' in selection or selection.isdigit():
        indices = []
        for part in selection.split(','):
            part = part.strip()
            if part.isdigit():
                indices.append(int(part))
            elif '-' in part:
                # 处理 "1-10" 格式
                range_match = re.match(r'^(\d+)-(\d+)$', part)
                if range_match:
                    start = int(range_match.group(1))
                    end = int(range_match.group(2))
                    indices.extend(range(start, end + 1))
        
        # 去重
        indices = list(dict.fromkeys(indices))
        
        for idx in indices:
            if 1 <= idx <= len(files):
                selected.append(files[idx - 1])
        return selected
    
    # 通配符匹配 (如 "*.mkv")
    if '*' in selection:
        pattern = selection.replace('.', '\\.').replace('*', '.*')
        for file in files:
            if re.match(pattern, file['name'], re.IGNORECASE):
                selected.append(file)
        return selected
    
    # 按类型选择
    if selection.lower() in ['video', 'videos', '电影', '影视']:
        video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', 
                          '.m4v', '.mpg', '.mpeg', '.webm', '.ts', '.vob'}
        for file in files:
            ext = os.path.splitext(file['name'])[1].lower()
            if ext in video_extensions:
                selected.append(file)
        return selected
    
    if selection.lower() in ['zip', 'rar', '7z', '压缩包', '压缩文件']:
        archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', 
                            '.tgz', '.xz', '.lzma'}
        for file in files:
            ext = os.path.splitext(file['name'])[1].lower()
            if ext in archive_extensions:
                selected.append(file)
        return selected
    
    # 文件扩展名匹配 (如 "mkv", "pdf")
    if not selection.startswith('.') and '.' not in selection:
        ext_lower = selection.lower()
        for file in files:
            ext = os.path.splitext(file['name'])[1].lower()
            if ext == '.' + ext_lower or ext == ext_lower:
                selected.append(file)
        return selected
    
    return selected


# 全局函数：显示文件树视图（带序号）
def display_file_tree_view(files: List[Dict], index_map: List[str]) -> None:
    """
    以树形结构显示文件列表（带序号）
    
    Args:
        files: 文件列表
        index_map: 序号映射表
    """
    if not files:
        print("📂 空目录")
        return
    
    print("\n📁 文件树：")
    print("-" * 60)
    
    for i, file in enumerate(files, 1):
        name = file['name']
        size = format_size(file['size']) if file['size'] > 0 else '-'
        ftype = '📁' if not file['is_file'] else '📄'
        index = f"[{i}]"
        
        print(f"  {index} {ftype} {name} ({size})")
    
    print("-" * 60)
    print(f"共 {len(files)} 个项目\n")
