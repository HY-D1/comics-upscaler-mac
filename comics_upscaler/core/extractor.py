"""图片提取模块"""

import fitz
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import io

from ..exceptions.custom_exceptions import ExtractorError
from ..utils.image import ImageProcessor
from ..utils.file import FileManager
from ..config.config import ConfigManager
from ..models.data_models import ProcessedImage, EPUBMetadata

class ImageExtractor:
    """图片提取器"""
    
    def __init__(self, temp_dir: Path):
        """初始化图片提取器"""
        self.temp_dir = temp_dir
        self.file_manager = FileManager()
        config_manager = ConfigManager()
        self.image_processor = ImageProcessor(config_manager.config.upscale)
    
    def cleanup(self) -> None:
        """清理临时文件"""
        self.file_manager.cleanup_temp_files(self.temp_dir)
    
    def extract_from_pdf(self, file_path: Path, output_dir: Path) -> List[ProcessedImage]:
        """从PDF提取图片"""
        print("开始从PDF提取图片...")
        images = []
        
        try:
            doc = fitz.open(str(file_path))
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap()
                
                # 创建PIL图片
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # 保存图片
                image_path = output_dir / f'page_{page_num + 1:04d}.jpg'
                self.image_processor.save_image(img, image_path)
                
                # 记录图片信息
                images.append(ProcessedImage(
                    original_path=file_path,
                    processed_path=image_path,
                    page_number=page_num + 1,
                    width=pix.width,
                    height=pix.height,
                    format=self.image_processor.config.output_format
                ))
            
            print(f"PDF处理完成，共提取 {len(images)} 张图片")
            return images
            
        except Exception as e:
            raise ExtractorError(f"PDF处理失败: {str(e)}")
        finally:
            if 'doc' in locals():
                doc.close()
    
    def extract_from_epub(
        self,
        file_path: Path,
        output_dir: Path,
        min_size: Tuple[int, int] = (100, 100)
    ) -> Tuple[List[ProcessedImage], EPUBMetadata]:
        """从EPUB提取图片"""
        print("开始从EPUB提取图片...")
        images = []
        
        try:
            book = epub.read_epub(str(file_path))
            
            # 获取元数据
            metadata = self._extract_metadata(book)
            print(f"书籍标题: {metadata.title}")
            print(f"作者: {metadata.creator}")
            
            # 创建图片ID到内容的映射
            image_map = self._create_image_map(book, min_size)
            
            # 按HTML文档顺序处理图片
            processed_images = set()
            page_num = 1
            
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    soup = BeautifulSoup(item.content, 'html.parser')
                    for img_tag in soup.find_all('img'):
                        src = img_tag.get('src')
                        if not src:
                            continue
                        
                        # 处理图片路径
                        img_name = src.split('/')[-1]
                        
                        # 查找匹配的图片
                        matching_image = None
                        for image_file in image_map:
                            if img_name in image_file or image_file in img_name:
                                matching_image = image_file
                                break
                        
                        if matching_image and matching_image not in processed_images:
                            img_info = image_map[matching_image]
                            
                            # 保存图片
                            image_path = output_dir / f'page_{page_num:04d}.jpg'
                            
                            # 处理图片
                            img = Image.open(io.BytesIO(img_info['data']))
                            img = self.image_processor.convert_to_rgb(img)
                            self.image_processor.save_image(img, image_path)
                            
                            # 记录图片信息
                            # original_path 应该是图片在 EPUB 中的原始路径，用于后续替换
                            images.append(ProcessedImage(
                                original_path=Path(matching_image),
                                processed_path=image_path,
                                page_number=page_num,
                                width=img_info['size'][0],
                                height=img_info['size'][1],
                                format=self.image_processor.config.output_format,
                                is_cover='cover' in matching_image.lower()
                            ))
                            
                            processed_images.add(matching_image)
                            print(f"已提取图片 {page_num}: {matching_image}")
                            page_num += 1
            
            print(f"EPUB处理完成，共提取 {len(images)} 张图片")
            return images, metadata
            
        except Exception as e:
            raise ExtractorError(f"EPUB处理失败: {str(e)}")
    
    def _extract_metadata(self, book: epub.EpubBook) -> EPUBMetadata:
        """提取EPUB元数据"""
        metadata = EPUBMetadata()
        
        try:
            # 提取基本元数据
            metadata.title = next(iter(book.get_metadata('DC', 'title')), [None])[0]
            metadata.creator = next(iter(book.get_metadata('DC', 'creator')), [None])[0]
            metadata.language = next(iter(book.get_metadata('DC', 'language')), ['zh'])[0]
            metadata.identifier = next(iter(book.get_metadata('DC', 'identifier')), [None])[0]
            
            # 提取其他元数据
            additional_metadata = {}
            for namespace, values in book.metadata.items():
                for v in values:
                    if len(v) >= 2:
                        name, value = v[0], v[1]
                        if value is not None:
                            additional_metadata[f"{namespace}:{name}"] = value
            
            metadata.additional_metadata = additional_metadata
            
        except Exception as e:
            print(f"提取元数据时出错: {str(e)}")
        
        return metadata
    
    def _create_image_map(
        self,
        book: epub.EpubBook,
        min_size: Tuple[int, int]
    ) -> dict:
        """创建图片映射"""
        image_map = {}
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                try:
                    img_data = item.content
                    img = Image.open(io.BytesIO(img_data))
                    
                    # 检查图片大小
                    width, height = img.size
                    if width >= min_size[0] and height >= min_size[1]:
                        image_map[item.file_name] = {
                            'data': img_data,
                            'mode': img.mode,
                            'size': (width, height),
                            'id': item.id
                        }
                except Exception as e:
                    print(f"处理图片时出错 {item.get_name()}: {str(e)}")
        
        return image_map 