"""图片超分模块"""

import subprocess
import yaml
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import threading

from ..exceptions.custom_exceptions import UpscalerError
from ..utils.file import FileManager
from ..models.data_models import ProcessedImage, ProcessingResult

class Upscaler:
    """图片超分处理器"""
    
    def __init__(self, final2x_path: Path):
        """初始化超分处理器"""
        self.final2x_path = final2x_path
        if not self.final2x_path.exists():
            raise UpscalerError(f"未找到Final2X: {self.final2x_path}")
        
        self.file_manager = FileManager()
    
    def generate_config(
        self,
        input_images: List[Path],
        output_dir: Path,
        model_name: str,
        scale: int,
        batch_id: str = None
    ) -> Path:
        """生成Final2X配置文件"""
        try:
            config = {
                'device': 'auto',
                'input_path': [str(p) for p in input_images],
                'output_path': str(output_dir),
                'pretrained_model_name': model_name,
                'target_scale': scale
            }
            
            # 为每个批次创建独立的配置文件
            config_filename = f'final2x_config_{batch_id}.yaml' if batch_id else 'final2x_config.yaml'
            config_path = output_dir / config_filename
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True)
            
            return config_path
            
        except Exception as e:
            raise UpscalerError(f"生成配置文件失败: {str(e)}")
    
    def process_batch(
        self,
        config_path: Path,
        batch_output_dir: Path
    ) -> ProcessingResult:
        """处理单个批次的图片"""
        try:
            cmd = [
                str(self.final2x_path),
                "--YAML",
                str(config_path),
                "--NOTOPENFOLDER"
            ]
            
            print(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return ProcessingResult(
                    success=False,
                    message=f"超分处理失败: {result.stderr}",
                    error=Exception(result.stderr)
                )
            
            return ProcessingResult(
                success=True,
                message="批次处理成功"
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"批次处理异常: {str(e)}",
                error=e
            )
    
    def monitor_progress(
        self,
        output_dir: Path,
        total_files: int,
        pbar: tqdm
    ) -> None:
        """监控超分处理进度"""
        processed_files = set()
        
        while len(processed_files) < total_files:
            # 扫描所有批次目录
            all_files = set()
            for batch_dir in output_dir.glob('batch_*'):
                batch_outputs = batch_dir / 'outputs'
                if batch_outputs.exists():
                    all_files.update(f.name for f in batch_outputs.glob('*'))
            
            # 检查主输出目录
            main_outputs = output_dir / 'outputs'
            if main_outputs.exists():
                all_files.update(f.name for f in main_outputs.glob('*'))
            
            # 更新进度
            new_files = all_files - processed_files
            if new_files:
                pbar.update(len(new_files))
                processed_files.update(new_files)
            
            time.sleep(0.5)
    
    def upscale_images(
        self,
        images: List[ProcessedImage],
        output_dir: Path,
        model_name: str,
        scale: int = 4,
        num_processes: int = 4
    ) -> ProcessingResult:
        """使用Final2X对图片进行超分辨率处理"""
        try:
            print("\n开始超分辨率处理...")
            print(f"使用模型: {model_name}")
            print(f"放大倍数: {scale}x")
            print(f"并行进程数: {num_processes}")
            
            # 确保输出目录存在
            self.file_manager.ensure_dir(output_dir)
            
            # 将图片列表分成N组
            batch_size = max(1, len(images) // num_processes)
            image_batches = []
            for i in range(0, len(images), batch_size):
                batch = images[i:i + batch_size]
                if batch:
                    image_batches.append(batch)
            
            print(f"图片总数: {len(images)}")
            print(f"分成 {len(image_batches)} 批处理")
            
            # 为每个批次创建配置文件和输出目录
            configs = []
            for i, batch in enumerate(image_batches):
                batch_output_dir = output_dir / f'batch_{i}'
                self.file_manager.ensure_dir(batch_output_dir)
                
                config_path = self.generate_config(
                    [img.processed_path for img in batch],
                    batch_output_dir,
                    model_name,
                    scale,
                    batch_id=str(i)
                )
                configs.append((config_path, batch_output_dir))
            
            # 创建进度条
            pbar = tqdm(total=len(images), desc="超分进度", unit="张")
            
            # 启动进度监控线程
            monitor_thread = threading.Thread(
                target=self.monitor_progress,
                args=(output_dir, len(images), pbar),
                daemon=True
            )
            monitor_thread.start()
            
            # 使用线程池并行处理
            print("\n开始并行处理...")
            success = True
            failed_batches = []
            
            with ThreadPoolExecutor(max_workers=num_processes) as executor:
                future_to_batch = {
                    executor.submit(self.process_batch, config_path, batch_dir): i
                    for i, (config_path, batch_dir) in enumerate(configs)
                }
                
                for future in as_completed(future_to_batch):
                    batch_id = future_to_batch[future]
                    result = future.result()
                    
                    if not result.success:
                        print(f"批次 {batch_id} 处理失败: {result.message}")
                        success = False
                        failed_batches.append(batch_id)
                    else:
                        print(f"批次 {batch_id} 处理完成")
            
            # 等待进度监控线程完成最后的更新
            time.sleep(2)
            pbar.close()
            
            # 合并所有批次的输出
            print("\n合并输出...")
            main_output = output_dir / 'outputs'
            self.file_manager.ensure_dir(main_output)
            
            for i, (config_path, batch_dir) in enumerate(configs):
                if i in failed_batches:
                    continue
                    
                batch_outputs = batch_dir / 'outputs'
                if batch_outputs.exists():
                    # 移动所有输出文件到主输出目录
                    for file in batch_outputs.glob('*'):
                        dst = main_output / file.name
                        if dst.exists():
                            dst.unlink()
                        self.file_manager.move_file(file, dst)
                    
                    # 删除批次目录
                    self.file_manager.cleanup_temp_files(batch_dir)
                
                # 删除配置文件
                if config_path.exists():
                    config_path.unlink()
            
            if success:
                return ProcessingResult(
                    success=True,
                    message="所有批次处理完成"
                )
            else:
                return ProcessingResult(
                    success=False,
                    message=f"部分批次处理失败: {failed_batches}"
                )
                
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"超分处理出错: {str(e)}",
                error=e
            ) 