"""主程序入口"""

import sys
import time
import warnings
from pathlib import Path
import os

# 过滤 ebooklib 警告
warnings.filterwarnings('ignore', category=UserWarning, module='ebooklib.epub')
warnings.filterwarnings('ignore', category=FutureWarning, module='ebooklib.epub')

from comics_upscaler.config.config import ConfigManager
from comics_upscaler.core.extractor import ImageExtractor
from comics_upscaler.core.upscaler import Upscaler
from comics_upscaler.core.epub_builder import EPUBBuilder
from comics_upscaler.utils.file import FileManager
from comics_upscaler.models.data_models import BatchProcessingStats

def get_base_path() -> Path:
    """获取应用基础路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe
        return Path(sys._MEIPASS).parent
    else:
        # 如果是开发环境
        return Path(__file__).parent

def get_config_path() -> Path:
    """获取配置文件路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe，配置文件在exe同级目录
        return Path(sys._MEIPASS).parent / "config" / "settings.yaml"
    else:
        # 如果是开发环境
        return Path(__file__).parent / "config" / "settings.yaml"

def init_app(config_path: Path) -> None:
    """初始化应用"""
    config_manager = ConfigManager()
    config_manager.init_config(config_path)
    print("应用初始化完成")

def process_single_file(
    input_file: Path,
    output_dir: Path,
    config_manager: ConfigManager
) -> bool:
    """处理单个文件"""
    config = config_manager.config
    file_manager = FileManager()
    
    try:
        # 创建项目目录
        project_dir, original_file = file_manager.setup_project_folders(input_file)
        
        # 创建处理器实例
        extractor = ImageExtractor(config.temp_dir)
        # 获取 Final2x-core 路径（支持 macOS 和 Windows）
        base_path = get_base_path()
        if sys.platform == 'darwin':  # macOS
            final2x_path = base_path.parent / "Final2X" / "Final2x-core"
        else:  # Windows
            final2x_path = Path("Final2X/Final2x-core.exe")
        upscaler = Upscaler(final2x_path)
        epub_builder = EPUBBuilder()
        
        try:
            # 1. 提取图片
            print(f"\n{'='*20} 开始处理 {input_file.name} {'='*20}")
            print("\n第1步: 提取图片")
            
            if input_file.suffix.lower() == '.pdf':
                images = extractor.extract_from_pdf(original_file, project_dir / 'images')
                metadata = None
            else:
                images, metadata = extractor.extract_from_epub(original_file, project_dir / 'images')
            
            if not images:
                print("没有找到可处理的图片!")
                return False
            
            print(f"找到 {len(images)} 张图片")
            
            # 2. 超分辨率处理
            print("\n第2步: 超分辨率图片")
            upscaled_dir = project_dir / "upscaled"
            file_manager.ensure_dir(upscaled_dir)
            
            result = upscaler.upscale_images(
                images,
                upscaled_dir,
                config.upscale.model_name,
                config.upscale.scale,
                config.upscale.num_processes
            )
            
            if not result.success:
                print(f"超分辨率处理失败: {result.message}")
                return False
            
            # 3. 重新打包
            print("\n第3步: 重新打包EPUB")
            output_file = output_dir / input_file.name
            
            print("打包设置:")
            print(f"- 原始文件: {input_file}")
            print(f"- 超分辨率图片: {upscaled_dir}")
            print(f"- 输出文件: {output_file}")
            print(f"- 适配电子墨水屏: 是 ({config.upscale.target_long_edge}×{config.upscale.target_long_edge*3//4})")
            
            result = epub_builder.create_epub(
                images,
                output_file,
                metadata,
                config.upscale.target_long_edge,
                config.epub.resize_to_original,
                original_file  # 传递原始EPUB路径以保留结构
            )
            
            if result.success:
                print(f"\n{'='*20} 处理完成 {'='*20}")
                print(f"输出文件: {output_file}")
                
                # 显示文件大小对比
                original_size = file_manager.get_file_size(input_file)
                new_size = file_manager.get_file_size(output_file)
                print("\n文件大小对比:")
                print(f"- 原始文件: {original_size:.2f} MB")
                print(f"- 处理后文件: {new_size:.2f} MB")
                print(f"- 增大比例: {(new_size/original_size - 1)*100:.1f}%")
                
                return True
            else:
                print(f"打包失败: {result.message}")
                return False
                
        finally:
            # 清理临时文件
            extractor.cleanup()
            file_manager.cleanup_temp_files(project_dir)
            print("\n临时文件已清理")
            
    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        import traceback
        print("\n详细错误信息:")
        print(traceback.format_exc())
        return False

def process_directory(
    input_dir: Path,
    output_dir: Path,
    config_manager: ConfigManager
) -> BatchProcessingStats:
    """批量处理目录"""
    file_manager = FileManager()
    
    # 检查已处理和未处理的文件
    processed_files, unprocessed_files = file_manager.check_processed_files(input_dir, output_dir)
    
    if processed_files:
        print(f"\n已处理的文件 ({len(processed_files)}):")
        for file in processed_files:
            print(f"- {file}")
    
    if not unprocessed_files:
        print("\n所有文件都已处理完成!")
        return BatchProcessingStats(
            total_files=len(processed_files),
            processed_files=len(processed_files),
            failed_files=0,
            total_images=0,
            processed_images=0,
            failed_images=0,
            start_time=time.time(),
            end_time=time.time()
        )
    
    print(f"\n待处理的文件 ({len(unprocessed_files)}):")
    for file in unprocessed_files:
        print(f"- {file}")
    
    # 显示处理设置
    config = config_manager.config
    print(f"\n超分辨率设置:")
    print(f"- 使用模型: {config.upscale.model_name}")
    print(f"- 放大倍数: {config.upscale.scale}x")
    print(f"- 并行进程数: {config.upscale.num_processes}")
    
    # 开始处理
    stats = BatchProcessingStats(
        total_files=len(unprocessed_files),
        processed_files=0,
        failed_files=0,
        total_images=0,
        processed_images=0,
        failed_images=0,
        start_time=time.time()
    )
    
    for input_file in unprocessed_files:
        success = process_single_file(input_file, output_dir, config_manager)
        if success:
            stats.processed_files += 1
        else:
            stats.failed_files += 1
    
    stats.end_time = time.time()
    
    # 显示处理结果
    print(f"\n批处理完成!")
    print(f"- 总文件数: {stats.total_files}")
    print(f"- 成功处理: {stats.processed_files}")
    print(f"- 处理失败: {stats.failed_files}")
    print(f"- 处理时间: {(stats.end_time - stats.start_time):.1f} 秒")
    print(f"输出目录: {output_dir}")
    
    return stats

def main():
    """主函数"""
    try:
        # 初始化应用
        config_path = get_config_path()
        print(f"配置文件路径: {config_path}")
        init_app(config_path)
        
        # 获取配置管理器
        config_manager = ConfigManager()
        
        # 从配置文件获取输入目录
        input_dir = Path(config_manager.config.directories.input)
        if not input_dir.exists():
            print(f"错误: 目录不存在: {input_dir}")
            return 1
        
        # 创建输出目录
        output_dir = Path(str(input_dir) + config_manager.config.directories.output_suffix)
        file_manager = FileManager()
        file_manager.ensure_dir(output_dir)
        
        # 处理目录
        stats = process_directory(input_dir, output_dir, config_manager)
        
        # 等待用户按键退出
        if getattr(sys, 'frozen', False):
            input("\n按回车键退出...")
        
        return 0 if stats.failed_files == 0 else 1
        
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        import traceback
        print("\n详细错误信息:")
        print(traceback.format_exc())
        if getattr(sys, 'frozen', False):
            input("\n按回车键退出...")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 