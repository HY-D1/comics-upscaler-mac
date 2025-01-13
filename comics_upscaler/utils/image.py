"""图片处理工具"""

from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
import io
from ..exceptions.custom_exceptions import FileOperationError
from ..config.config import UpscaleConfig

class ImageProcessor:
    """图片处理器"""
    
    def __init__(self, config: UpscaleConfig):
        """初始化图片处理器
        
        Args:
            config: 超分配置
        """
        self.config = config
    
    @staticmethod
    def calculate_optimal_size(
        img_width: int,
        img_height: int,
        target_long_edge: int = 1872
    ) -> Tuple[int, int]:
        """计算最佳显示尺寸
        
        Args:
            img_width: 原始宽度
            img_height: 原始高度
            target_long_edge: 目标长边尺寸
            
        Returns:
            新的宽度和高度
        """
        # 确定长边
        long_edge = max(img_width, img_height)
        # 计算缩放比例
        scale = target_long_edge / long_edge
        
        # 按比例计算新尺寸
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        return new_width, new_height
    
    @staticmethod
    def resize_image(
        image: Image.Image,
        target_size: Tuple[int, int],
        format: str = 'PNG',
        quality: int = 95
    ) -> bytes:
        """调整图片大小并转换为字节
        
        Args:
            image: PIL图片对象
            target_size: 目标尺寸 (宽, 高)
            format: 输出格式
            quality: 输出质量
            
        Returns:
            图片字节数据
        """
        try:
            # 调整大小
            resized_img = image.resize(target_size, Image.Resampling.LANCZOS)
            
            # 转换为字节
            img_byte_arr = io.BytesIO()
            resized_img.save(img_byte_arr, format=format, quality=quality, optimize=True)
            return img_byte_arr.getvalue()
        except Exception as e:
            raise FileOperationError(f"图片处理失败: {str(e)}")
    
    @staticmethod
    def convert_to_rgb(image: Image.Image, background_color: str = 'white') -> Image.Image:
        """将图片转换为RGB模式
        
        Args:
            image: PIL图片对象
            background_color: 背景颜色
            
        Returns:
            RGB模式的图片对象
        """
        try:
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, background_color)
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[3])
                else:
                    background.paste(image, mask=image.split()[1])
                return background
            return image.convert('RGB')
        except Exception as e:
            raise FileOperationError(f"图片转换失败: {str(e)}")
    
    def save_image(
        self,
        image: Image.Image,
        output_path: Path,
        format: str = None,
        quality: int = None
    ) -> None:
        """保存图片
        
        Args:
            image: PIL图片对象
            output_path: 输出路径
            format: 输出格式，如果为None则使用配置中的格式
            quality: 输出质量，如果为None则使用配置中的质量
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # 使用配置中的格式和质量，如果没有指定的话
            format = format or self.config.output_format
            quality = quality if quality is not None else self.config.output_quality
            image.save(output_path, format=format, quality=quality)
        except Exception as e:
            raise FileOperationError(f"保存图片失败: {str(e)}")
    
    @staticmethod
    def load_image(image_path: Path) -> Optional[Image.Image]:
        """加载图片
        
        Args:
            image_path: 图片路径
            
        Returns:
            PIL图片对象，如果加载失败返回None
        """
        try:
            return Image.open(image_path)
        except Exception as e:
            raise FileOperationError(f"加载图片失败: {str(e)}") 