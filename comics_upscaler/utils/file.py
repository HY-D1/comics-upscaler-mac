"""文件处理工具模块"""

import os
import shutil
from pathlib import Path
from typing import Tuple, List, Optional
from datetime import datetime

from ..exceptions.custom_exceptions import FileOperationError

class FileManager:
    """文件管理工具类"""
    
    @staticmethod
    def setup_project_folders(
        file_path: Path,
        base_dir: Path = Path("projects")
    ) -> Tuple[Path, Path]:
        """创建项目文件夹结构"""
        try:
            # 创建项目名称
            base_name = file_path.stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = f"{base_name}_extracted_{timestamp}"
            
            # 创建项目目录
            project_dir = base_dir / project_name
            subdirs = ['original', 'images']
            
            for subdir in subdirs:
                (project_dir / subdir).mkdir(parents=True, exist_ok=True)
            
            # 复制原始文件
            original_file = project_dir / 'original' / file_path.name
            shutil.copy2(file_path, original_file)
            
            return project_dir, original_file
            
        except Exception as e:
            raise FileOperationError(f"创建项目目录失败: {str(e)}")
    
    @staticmethod
    def cleanup_temp_files(temp_dir: Path) -> None:
        """清理临时文件"""
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                print(f"已清理临时目录: {temp_dir}")
        except Exception as e:
            print(f"清理临时文件失败: {str(e)}")
    
    @staticmethod
    def check_processed_files(
        input_dir: Path,
        output_dir: Path
    ) -> Tuple[List[Path], List[Path]]:
        """检查已处理和未处理的文件"""
        try:
            processed_files = []
            unprocessed_files = []
            
            # 获取所有输入epub文件
            input_files = [f for f in input_dir.glob("*.epub")]
            
            # 获取所有输出文件
            output_files = set(f.name for f in output_dir.glob("*.epub")) if output_dir.exists() else set()
            
            # 检查每个输入文件
            for input_file in input_files:
                if input_file.name in output_files:
                    # 检查输出文件是否完整
                    output_path = output_dir / input_file.name
                    if output_path.stat().st_size > 0:
                        processed_files.append(input_file)
                        continue
                unprocessed_files.append(input_file)
            
            return processed_files, unprocessed_files
            
        except Exception as e:
            raise FileOperationError(f"检查文件状态失败: {str(e)}")
    
    @staticmethod
    def get_file_size(file_path: Path) -> float:
        """获取文件大小（MB）"""
        try:
            return file_path.stat().st_size / (1024 * 1024)
        except Exception as e:
            raise FileOperationError(f"获取文件大小失败: {str(e)}")
    
    @staticmethod
    def ensure_dir(dir_path: Path) -> None:
        """确保目录存在"""
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise FileOperationError(f"创建目录失败: {str(e)}")
    
    @staticmethod
    def move_file(src: Path, dst: Path) -> None:
        """移动文件"""
        try:
            if dst.exists():
                dst.unlink()
            shutil.move(src, dst)
        except Exception as e:
            raise FileOperationError(f"移动文件失败: {str(e)}")
    
    @staticmethod
    def copy_file(src: Path, dst: Path) -> None:
        """复制文件"""
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            raise FileOperationError(f"复制文件失败: {str(e)}")
            
    @staticmethod
    def list_files(
        directory: Path,
        pattern: str = "*",
        recursive: bool = False
    ) -> List[Path]:
        """列出目录中的文件"""
        try:
            if recursive:
                return list(directory.rglob(pattern))
            return list(directory.glob(pattern))
        except Exception as e:
            raise FileOperationError(f"列出文件失败: {str(e)}") 