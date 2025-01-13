import PyInstaller.__main__
import os
import shutil
from pathlib import Path

def build_exe():
    """打包应用为exe"""
    # 清理之前的构建文件
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    
    # 设置打包参数
    params = [
        'comics_upscaler/main.py',  # 主程序入口
        '--name=ComicsUpscaler',    # exe名称
        '--onedir',                 # 打包为目录
        '--console',               # 显示控制台，方便查看错误信息
        '--icon=icon.ico',         # 设置程序图标
        # 隐藏导入
        '--hidden-import=PIL',
        '--hidden-import=ebooklib',
        '--hidden-import=PyPDF2',
        '--hidden-import=yaml',
    ]
    
    # 执行打包
    PyInstaller.__main__.run(params)
    
    # 复制配置文件和其他资源
    dist_dir = Path('dist/ComicsUpscaler')
    
    # 复制配置文件
    config_dir = dist_dir / 'config'
    config_dir.mkdir(exist_ok=True)
    shutil.copy2('comics_upscaler/config/settings.yaml', config_dir / 'settings.yaml')
    
    # 复制Final2X
    if os.path.exists('Final2X'):
        shutil.copytree('Final2X', dist_dir / 'Final2X', dirs_exist_ok=True)
    
    print("\n打包完成！")
    print("输出目录: dist/ComicsUpscaler")

if __name__ == '__main__':
    build_exe() 