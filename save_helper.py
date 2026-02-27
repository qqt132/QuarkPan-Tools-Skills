#!/usr/bin/env python3
"""
夸克网盘保存助手 - 交互式保存脚本

提供交互式界面来选择文件并转存到夸克网盘

使用方式：
    python save_helper.py <share_url> [--password <pwd>]
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

from quark_client import QuarkClient, display_files, display_file_tree_view, format_size, parse_file_selection


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


def get_file_selection(files: list, index_map: list) -> list:
    """
    获取用户文件选择
    
    Args:
        files: 文件列表
        index_map: 序号映射表
        
    Returns:
        list: 选中的文件列表
    """
    print("\n" + "="*60)
    print("📝 请选择要转存的文件")
    print("="*60)
    print("\n支持的选择方式：")
    print("  all              - 选择所有文件")
    print("  1,2,3            - 选择序号 1, 2, 3 的文件")
    print("  1-10             - 选择序号 1 到 10 的文件")
    print("  *.mkv            - 选择所有 mkv 文件")
    print("  video            - 选择所有视频文件")
    print("  zip              - 选择所有压缩包")
    print("  mkv,pdf,mp4      - 选择指定扩展名的文件")
    print()
    
    while True:
        try:
            selection = input("请输入选择 (或按回车输入 'help' 查看说明): ").strip()
            
            if not selection:
                continue
            
            if selection.lower() == 'help':
                print("\n帮助信息：")
                print("  all              - 选择所有文件")
                print("  1,2,3            - 选择序号 1, 2, 3 的文件")
                print("  1-10             - 选择序号 1 到 10 的文件")
                print("  *.mkv            - 选择所有 mkv 文件")
                print("  video            - 选择所有视频文件")
                print("  zip              - 选择所有压缩包")
                print("  mkv,pdf,mp4      - 选择指定扩展名的文件")
                continue
            
            # 解析选择
            selected = parse_file_selection(selection, files)
            
            if not selected:
                print("⚠️  没有匹配的文件，请重新输入")
                continue
            
            # 显示选中的文件
            print(f"\n✅ 选中 {len(selected)} 个文件：")
            for i, f in enumerate(selected, 1):
                size_str = format_size(f['size']) if f['size'] > 0 else '-'
                ftype = '📁' if not f['is_file'] else '📄'
                print(f"  {i}. {ftype} {f['name']} ({size_str})")
            
            confirm = input("\n确认选择吗？(y/n): ").strip().lower()
            if confirm in ['y', 'yes', '是']:
                return selected
                
        except (KeyboardInterrupt, EOFError):
            print("\n❌ 操作已取消")
            sys.exit(0)


def get_target_dir(client: QuarkClient) -> tuple:
    """
    获取目标目录
    
    Args:
        client: QuarkClient 实例
        
    Returns:
        tuple: (目录路径, 目录ID)
    """
    print("\n" + "="*60)
    print("📂 选择目标目录")
    print("="*60)
    
    while True:
        try:
            dirs = client.get_user_dirs()
            
            # 显示目录树
            print("\n📁 我的目录：")
            if dirs:
                for d in dirs:
                    indent = d['path'].count('/')
                    print(f"{'  ' * indent}└─ {d['name']} (路径: {d['path']})")
            else:
                print("  (空)")
            
            print("\n支持的输入：")
            print("  /路径/目录       - 使用现有目录")
            print("  new:目录名      - 创建新目录")
            print("  home            - 使用根目录 (/)")
            print()
            
            path_input = input("请输入目标路径 (或按回车输入 'help'): ").strip()
            
            if not path_input:
                continue
            
            if path_input.lower() == 'help':
                continue
            
            # 处理新建目录
            if path_input.lower().startswith('new:'):
                dir_name = path_input[4:].strip()
                if not dir_name:
                    print("❌ 目录名称不能为空")
                    continue
                
                # 询问父目录
                print(f"\n要将 '{dir_name}' 创建在哪个目录下？")
                print("  /              - 根目录")
                print("  /路径/目录     - 指定目录")
                print("  (留空)         - 根目录")
                parent_path = input("父目录路径: ").strip()
                
                if not parent_path:
                    parent_fid = '0'
                else:
                    parent_fid = client.get_dir_by_path(parent_path)
                    if parent_fid is None:
                        print(f"❌ 父目录不存在: {parent_path}")
                        continue
                
                # 创建目录
                try:
                    new_dir_id = client.create_dir(dir_name, parent_fid)
                    print(f"✅ 目录创建成功: {new_dir_id}")
                    return (f"{parent_path}/{dir_name}" if parent_path != '/' else f"/{dir_name}", new_dir_id)
                except Exception as e:
                    print(f"❌ 创建目录失败: {e}")
                    continue
            
            # 处理 home
            if path_input.lower() == 'home':
                return ('/', '0')
            
            # 检查目录是否存在
            dir_id = client.get_dir_by_path(path_input)
            if dir_id is None:
                print(f"❌ 目录不存在: {path_input}")
                create = input("是否创建该目录？(y/n): ").strip().lower()
                if create in ['y', 'yes', '是']:
                    # 递归创建目录
                    parts = [p for p in path_input.split('/') if p]
                    current_fid = '0'
                    current_path = ''
                    
                    for part in parts:
                        current_path = f"{current_path}/{part}" if current_path else f"/{part}"
                        existing_id = client.get_dir_by_path(current_path)
                        if existing_id:
                            current_fid = existing_id
                        else:
                            print(f"  创建目录: {part}")
                            current_fid = client.create_dir(part, current_fid)
                    
                    print(f"✅ 目录创建成功: {path_input}")
                    return (path_input, current_fid)
                continue
            
            return (path_input, dir_id)
            
        except (KeyboardInterrupt, EOFError):
            print("\n❌ 操作已取消")
            sys.exit(0)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='夸克网盘保存助手 - 交互式转存工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例：
  python save_helper.py https://pan.quark.cn/s/xxxxx
  python save_helper.py https://pan.quark.cn/s/xxxxx --password 1234
        '''
    )
    
    parser.add_argument('share_url', help='夸克分享链接')
    parser.add_argument('--password', '-p', help='提取码')
    parser.add_argument('--auto', '-a', action='store_true', 
                       help='自动模式（不交互，使用默认设置）')
    
    args = parser.parse_args()
    
    # 创建客户端
    client = create_client()
    
    # 解析分享链接
    try:
        parsed = client.parse_share_url(args.share_url)
        pwd_id = parsed['pwd_id']
        password = parsed['password'] if not args.password else args.password
    except Exception as e:
        print(f"❌ 解析分享链接失败: {e}")
        sys.exit(1)
    
    print(f"\n📋 分享链接: {args.share_url}")
    
    # 获取 stoken
    try:
        stoken = client.get_stoken(pwd_id, password)
        print("✅ stoken 获取成功")
    except Exception as e:
        print(f"❌ 获取 stoken 失败: {e}")
        sys.exit(1)
    
    # 获取所有文件
    print("\n📂 正在获取文件列表...")
    try:
        files = client.get_all_files_recursive(pwd_id, stoken)
        print(f"✅ 获取到 {len(files)} 个文件/文件夹")
    except Exception as e:
        print(f"❌ 获取文件列表失败: {e}")
        sys.exit(1)
    
    # 显示文件树
    display_file_tree_view(files, [])
    
    # 自动模式
    if args.auto:
        print("\n💡 自动模式：选择所有文件，保存到根目录")
        selected = files
        target_path = '/'
        target_fid = '0'
    else:
        # 获取文件选择
        index_map = [str(i) for i in range(1, len(files) + 1)]
        selected = get_file_selection(files, index_map)
        
        # 获取目标目录
        target_path, target_fid = get_target_dir(client)
    
    # 转存文件
    print("\n" + "="*60)
    print("📤 开始转存")
    print("="*60)
    print(f"文件数: {len(selected)}")
    print(f"目标目录: {target_path} (ID: {target_fid})")
    print()
    
    # 构建文件ID列表
    fid_list = [f['fid'] for f in selected]
    share_fid_tokens = [''] * len(fid_list)
    
    try:
        # 执行转存
        task_id = client.save_files(
            pwd_id, stoken, fid_list, share_fid_tokens, target_fid
        )
        
        if not task_id:
            raise Exception("创建转存任务失败")
        
        print(f"✅ 转存任务已创建: {task_id}")
        
        # 等待任务完成
        def progress_callback(progress, status, message):
            print(f"  {status}: {progress}% - {message}")
        
        success = client.wait_task_complete(task_id, on_progress=progress_callback)
        
        result = {
            'action': 'save',
            'status': 'success' if success else 'error',
            'task_id': task_id,
            'file_count': len(selected),
            'target_dir': target_path,
            'target_fid': target_fid
        }
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        result = {
            'action': 'save',
            'status': 'error',
            'message': str(e)
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
