#!/usr/bin/env python3
"""
夸克网盘转存工具 - 主入口脚本

用于引用 skill 的 Worker 执行脚本

功能：
1. 读取配置（Cookie 路径等）
2. 创建 QuarkClient 实例
3. 根据参数执行不同操作
4. 返回结果（JSON 格式）

使用方式：
    python main.py <command> [arguments]
    
命令：
    list    <share_url> [--password <pwd>] [--depth <n>]  查看分享文件列表
    save    <share_url> <fid_list> <to_dir>               转存文件
    dirs                                                  查看我的目录
    create_dir <dir_name> [--parent_fid <fid>]           创建目录
    login                                                 登录（手动输入 Cookie）
    
示例：
    python main.py list https://pan.quark.cn/s/xxxxx
    python main.py list https://pan.quark.cn/s/xxxxx --password 1234
    python main.py list https://pan.quark.cn/s/xxxxx --depth 1
    python main.py save https://pan.quark.cn/s/xxxxx "1,2,3" "/我的视频"
    python main.py dirs
    python main.py create_dir "测试目录" --parent_fid "a373fb0d522f455ea2af639e9d061747"
    python main.py login
"""

import os
import sys
import json
import argparse
import readline
from pathlib import Path

# 添加当前目录到路径（支持作为 skill 被引用）
current_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(current_dir))

from quark_client import QuarkClient, display_files, display_file_tree_view, format_size, parse_file_selection, display_file_tree


def get_cookies_path() -> str:
    """获取 Cookie 文件路径"""
    # 优先使用环境变量
    if os.environ.get('QUARK_COOKIES_PATH'):
        return os.path.expanduser(os.environ['QUARK_COOKIES_PATH'])
    
    # 默认路径
    return "~/.config/quark/cookies.txt"


def create_client() -> QuarkClient:
    """创建 QuarkClient 实例并验证 Cookie"""
    cookies_path = get_cookies_path()
    client = QuarkClient(cookies_path)
    
    if not client.login():
        print("❌ Cookie 失效或未登录")
        print("请先运行: python main.py login")
        sys.exit(1)
    
    return client


def cmd_list(args):
    """list 命令：查看分享文件列表"""
    try:
        client = create_client()
        
        # 解析分享链接
        parsed = client.parse_share_url(args.share_url)
        pwd_id = parsed['pwd_id']
        password = parsed['password'] if not args.password else args.password
        
        # 获取 stoken
        stoken = client.get_stoken(pwd_id, password)
        
        # 获取文件列表
        depth = args.depth if args.depth and args.depth > 0 else -1
        
        # 获取文件夹树结构
        tree = client.get_folder_tree(pwd_id, stoken, max_depth=depth)
        
        # 获取完整文件列表
        if depth == -1 or depth > 0:
            all_files = client.get_all_files_recursive(pwd_id, stoken, max_depth=depth if depth > 0 else -1)
        else:
            all_files = client.get_file_list(pwd_id, stoken, '0')
        
        # 显示树形结构（默认，除非 --json-only）
        if not args.json_only:
            print(f"📁 分享 ID: {pwd_id}")
            if password:
                print(f"🔑 提取码: {password}")
            
            # 获取 stoken
            print("\n🔐 获取访问令牌...")
            print("✅ 成功")
            
            # 显示文件树（树形格式）
            print("\n📂 文件列表:")
            print("=" * 80)
            
            if tree and tree.get('children'):
                display_file_tree(tree)
            else:
                # 获取根目录文件
                files = client.get_file_list(pwd_id, stoken, '0')
                
                # 递归显示
                def display_recursive(files, prefix='', depth=0, max_depth=10, index_counter=[1]):
                    for i, f in enumerate(files):
                        name = f.get('file_name', '未知')
                        fid = f.get('fid', '')
                        size = f.get('size', 0)
                        is_dir = f.get('dir', False) or not f.get('is_file', True)
                        size_str = format_size(size) if size > 0 else '-'
                        
                        # 树形符号
                        is_last = (i == len(files) - 1)
                        branch = '└─ ' if is_last else '├─ '
                        indent = '│  ' if not is_last else '   '
                        
                        if is_dir:
                            print(f"{prefix}{branch}📁 {name}/")
                            if max_depth == -1 or depth < max_depth:
                                # 获取子文件夹内容
                                sub_files = client.get_file_list(pwd_id, stoken, fid)
                                display_recursive(sub_files, prefix + indent, depth + 1, max_depth, index_counter)
                        else:
                            idx = index_counter[0]
                            index_counter[0] += 1
                            print(f"{prefix}{branch}📄 {name} ({size_str}) [{idx}]")
                
                display_recursive(files, '', 0, depth if depth > 0 else 10)
            
            print("=" * 80)
            
            # 显示索引
            index_map = display_files(all_files)
        
        # 输出完整信息供程序使用
        result = {
            'success': True,
            'pwd_id': pwd_id,
            'stoken': stoken,
            'files': all_files,
            'count': len(all_files),
            'depth': depth if depth > 0 else 'all',
            'index_map': index_map
        }
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        error_result = {
            'action': 'list',
            'status': 'error',
            'message': str(e)
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        sys.exit(1)
    
    # 显示 JSON（如果指定）
    if args.json or args.json_only:
        if not args.json_only:
            print("\n")
        print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_save(args):
    """save 命令：转存文件"""
    try:
        client = create_client()
        
        # 解析分享链接
        parsed = client.parse_share_url(args.share_url)
        pwd_id = parsed['pwd_id']
        password = parsed['password'] if not args.password else args.password
        
        # 获取 stoken
        print("\n🔐 获取访问令牌...")
        stoken = client.get_stoken(pwd_id, password)
        print("✅ 成功")
        
        # 获取文件列表以获取序号映射
        all_files = client.get_all_files_recursive(pwd_id, stoken)
        
        # 解析要转存的文件 ID（序号或 fid）
        selection = args.fid_list.strip()
        
        # 如果是数字或数字列表，说明是序号
        if selection.replace(',', '').replace('-', '').isdigit():
            # 解析序号选择
            from quark_client import parse_file_selection
            selected_files = parse_file_selection(selection, all_files)
            fid_list = [f.get('fid') or f.get('file_id') for f in selected_files]
        else:
            # 直接是 fid 列表
            fid_list = [f.strip() for f in selection.split(',') if f.strip()]
            selected_files = [f for f in all_files if (f.get('fid') or f.get('file_id')) in fid_list]
        
        if not fid_list:
            print("❌ 没有选择任何文件")
            sys.exit(1)
        
        # 获取文件的 share_fid_token
        fid_to_token = {f.get('fid') or f.get('file_id'): f.get('share_fid_token', '') for f in all_files}
        share_fid_tokens = [fid_to_token.get(fid, '') for fid in fid_list]
        
        # 获取目标目录 ID
        if args.to_dir.startswith('/'):
            to_pdir_fid = client.get_dir_by_path(args.to_dir)
            if to_pdir_fid is None:
                print(f"❌ 目标目录不存在: {args.to_dir}")
                print(f"提示: 请先运行 'python main.py dirs' 查看可用目录")
                sys.exit(1)
        else:
            to_pdir_fid = args.to_dir
        
        # 执行转存
        print(f"\n🚀 开始转存 {len(fid_list)} 个文件到目录 {to_pdir_fid}...")
        task_id = client.save_files(
            pwd_id, stoken, fid_list, share_fid_tokens, to_pdir_fid
        )
        
        if not task_id:
            raise Exception("创建转存任务失败")
        
        print(f"✅ 转存任务已创建: {task_id}")
        
        # 等待任务完成
        success = client.wait_task_complete(task_id)
        
        result = {
            'action': 'save',
            'status': 'success' if success else 'error',
            'task_id': task_id,
            'file_count': len(fid_list),
            'target_dir': args.to_dir
        }
        
        # 默认只显示人类可读格式
        if not args.json_only:
            print(f"\n✅ 转存完成: {len(fid_list)} 个文件转存到 {args.to_dir}")
        
        # 显示 JSON（如果指定）
        if args.json or args.json_only:
            if not args.json_only:
                print("\n")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        error_result = {
            'action': 'save',
            'status': 'error',
            'message': str(e)
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        sys.exit(1)


def cmd_dirs(args):
    """dirs 命令：查看我的目录"""
    try:
        client = create_client()
        
        dirs = client.get_user_dirs()
        
        if not dirs:
            print("📂 您的网盘是空的")
            # 输出 JSON（如果指定）
            if args.json or args.json_only:
                result = {
                    'action': 'dirs',
                    'status': 'success',
                    'directories': [],
                    'count': 0
                }
                print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        
        # 显示目录树（默认）
        if not args.json_only:
            print("\n📁 我的目录结构：")
            print("-" * 60)
            
            # 按路径排序
            dirs.sort(key=lambda x: x['path'])
            
            for d in dirs:
                indent = d['path'].count('/')
                print(f"{'  ' * indent}└─ {d['name']} (ID: {d['fid']})")
            
            print("-" * 60)
            print(f"共 {len(dirs)} 个目录\n")
        
        result = {
            'action': 'dirs',
            'status': 'success',
            'directories': dirs,
            'count': len(dirs)
        }
        
        # 显示 JSON（如果指定）
        if args.json or args.json_only:
            if not args.json_only:
                print("\n")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        error_result = {
            'action': 'dirs',
            'status': 'error',
            'message': str(e)
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        sys.exit(1)


def cmd_login(args):
    """login 命令：手动登录"""
    try:
        cookies_path = get_cookies_path()
        client = QuarkClient(cookies_path)
        
        print("\n" + "="*60)
        print("🔒 夸克网盘登录")
        print("="*60)
        
        if client.manual_login():
            print("\n✅ 登录成功！")
            print(f" Cookie 保存位置: {cookies_path}")
        else:
            print("\n❌ 登录失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ 登录异常: {e}")
        sys.exit(1)


def cmd_create_dir(args):
    """create_dir 命令：创建新目录"""
    try:
        client = create_client()
        
        # 显示创建信息（默认）
        if not args.json_only:
            print(f"\n📁 创建目录: {args.dir_name}")
            if args.parent_fid:
                print(f"   父目录 ID: {args.parent_fid}")
        
        dir_id = client.create_dir(args.dir_name, args.parent_fid)
        
        # 显示成功信息（默认）
        if not args.json_only:
            print(f"\n✅ 目录创建成功!")
            print(f"   目录名称: {args.dir_name}")
            print(f"   目录 ID: {dir_id}")
        
        result = {
            'action': 'create_dir',
            'status': 'success',
            'dir_id': dir_id,
            'dir_name': args.dir_name
        }
        
        # 显示 JSON（如果指定）
        if args.json or args.json_only:
            if not args.json_only:
                print("\n")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        error_result = {
            'action': 'create_dir',
            'status': 'error',
            'message': str(e)
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='夸克网盘转存工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例：
  查看分享文件列表:
    python main.py list https://pan.quark.cn/s/xxxxx
    
  使用提取码查看:
    python main.py list https://pan.quark.cn/s/xxxxx --password 1234
    
  指定递归深度（1 表示只显示第一层）:
    python main.py list https://pan.quark.cn/s/xxxxx --depth 1
    
  转存指定文件:
    python main.py save https://pan.quark.cn/s/xxxxx "1,2,3" "/我的视频"
    
  查看我的目录:
    python main.py dirs
    
  创建目录:
    python main.py create_dir "测试目录" --parent_fid "a373fb0d522f455ea2af639e9d061747"
    
  登录:
    python main.py login
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='查看分享文件列表')
    list_parser.add_argument('share_url', help='夸克分享链接')
    list_parser.add_argument('--password', '-p', help='提取码')
    list_parser.add_argument('--depth', '-d', type=int, default=-1,
                            help='递归深度（-1 表示无限，1 表示只显示第一层）')
    list_parser.add_argument('--json', action='store_true', help='输出 JSON 格式（默认只显示人类可读格式）')
    list_parser.add_argument('--json-only', action='store_true', help='只输出 JSON（不显示树形结构）')
    
    # save 命令
    save_parser = subparsers.add_parser('save', help='转存文件')
    save_parser.add_argument('share_url', help='夸克分享链接')
    save_parser.add_argument('fid_list', help='文件 ID 列表（逗号分隔）')
    save_parser.add_argument('to_dir', help='目标目录路径')
    save_parser.add_argument('--password', '-p', help='提取码')
    save_parser.add_argument('--json', action='store_true', help='输出 JSON 格式（默认只显示人类可读格式）')
    save_parser.add_argument('--json-only', action='store_true', help='只输出 JSON（不显示树形结构）')
    
    # dirs 命令
    dirs_parser = subparsers.add_parser('dirs', help='查看我的目录')
    dirs_parser.add_argument('--json', action='store_true', help='输出 JSON 格式（默认只显示人类可读格式）')
    dirs_parser.add_argument('--json-only', action='store_true', help='只输出 JSON（不显示树形结构）')
    
    # login 命令
    login_parser = subparsers.add_parser('login', help='登录（手动输入 Cookie）')
    
    # create_dir 命令
    create_dir_parser = subparsers.add_parser('create_dir', help='创建新目录')
    create_dir_parser.add_argument('dir_name', help='目录名称')
    create_dir_parser.add_argument('--parent_fid', default='0', help='父目录 ID')
    create_dir_parser.add_argument('--json', action='store_true', help='输出 JSON 格式（默认只显示人类可读格式）')
    create_dir_parser.add_argument('--json-only', action='store_true', help='只输出 JSON（不显示树形结构）')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 执行相应命令
    commands = {
        'list': cmd_list,
        'save': cmd_save,
        'dirs': cmd_dirs,
        'login': cmd_login,
        'create_dir': cmd_create_dir
    }
    
    commands[args.command](args)


if __name__ == '__main__':
    main()
