"""EPUB构建模块"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import ebooklib
from ebooklib import epub
from PIL import Image
import io
import glob
import re
import os
import concurrent.futures
from multiprocessing import cpu_count

from ..exceptions.custom_exceptions import EPUBBuilderError
from ..utils.image import ImageProcessor
from ..utils.file import FileManager
from ..config.config import ConfigManager
from ..models.data_models import (
    ProcessedImage,
    EPUBMetadata,
    EPUBChapter,
    ProcessingResult
)

class EPUBBuilder:
    """EPUB构建器"""
    
    def __init__(self):
        """初始化EPUB构建器"""
        config_manager = ConfigManager()
        self.image_processor = ImageProcessor(config_manager.config.upscale)
        self.file_manager = FileManager()
        self.max_workers = cpu_count()  # 获取CPU核心数
    
    def _find_upscaled_image(self, project_dir: Path, image_name: str) -> Optional[Path]:
        """查找超分辨率处理后的图片
        
        Args:
            project_dir: 项目目录
            image_name: 图片文件名
            
        Returns:
            图片路径，如果找不到则返回None
        """
        try:
            # 从原始文件名中提取页码
            match = re.search(r'page_(\d+)', image_name)
            if not match:
                return None
            page_num = match.group(1)
            
            # 构建可能的文件名模式
            patterns = [
                f"4x-page_{page_num}.*",  # 4x-page_0001.png
                f"page_{page_num}.*",      # page_0001.png
            ]
            
            # 在所有batch目录中查找
            for pattern in patterns:
                for batch_dir in project_dir.glob('upscaled/batch_*/outputs'):
                    matches = list(batch_dir.glob(pattern))
                    if matches:
                        return matches[0]
                        
                # 也在主输出目录中查找
                main_output = project_dir / 'upscaled' / 'outputs'
                if main_output.exists():
                    matches = list(main_output.glob(pattern))
                    if matches:
                        return matches[0]
            
            return None
            
        except Exception as e:
            print(f"查找图片时出错: {str(e)}")
            return None
    
    def _process_image_parallel(
        self,
        book: epub.EpubBook,
        image: ProcessedImage,
        page_num: int,
        target_long_edge: int,
        resize_to_original: bool
    ) -> epub.EpubHtml:
        """并行处理单个图片章节"""
        try:
            return self._create_image_chapter(
                book,
                image,
                page_num,
                target_long_edge,
                resize_to_original
            )
        except Exception as e:
            print(f"处理第 {page_num} 页时出错: {str(e)}")
            raise

    def create_epub(
        self,
        images: List[ProcessedImage],
        output_path: Path,
        metadata: EPUBMetadata,
        target_long_edge: int = 1872,
        resize_to_original: bool = False
    ) -> ProcessingResult:
        """创建EPUB文件"""
        try:
            print("\n开始创建EPUB文件...")
            
            # 创建新的EPUB
            book = epub.EpubBook()
            
            # 添加元数据
            self._add_metadata(book, metadata)
            
            # 创建样式
            style = self._create_style()
            nav_css = epub.EpubItem(
                uid="style_nav",
                file_name="style/nav.css",
                media_type="text/css",
                content=style
            )
            book.add_item(nav_css)
            
            # 处理图片和创建章节
            chapters = []
            spine = ['nav']
            
            # 处理封面
            cover_image = next((img for img in images if img.is_cover), None)
            if cover_image:
                print("处理封面图片...")
                self._add_cover(book, cover_image, target_long_edge, resize_to_original)
                images = [img for img in images if not img.is_cover]
            
            # 并行处理其他图片
            print(f"使用 {self.max_workers} 个线程并行处理图片...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务并保存页码映射
                future_to_page = {
                    executor.submit(
                        self._process_image_parallel,
                        book,
                        image,
                        page_num,
                        target_long_edge,
                        resize_to_original
                    ): page_num
                    for page_num, image in enumerate(images, 1)
                }
                
                # 初始化结果列表，保持与输入图片相同的顺序
                completed_chapters = [None] * len(images)
                print(f"初始化结果列表，长度: {len(completed_chapters)}")
                
                # 收集并行处理的结果
                for future in concurrent.futures.as_completed(future_to_page):
                    page_num = future_to_page[future]
                    try:
                        chapter = future.result()
                        # 确保章节被放到正确的位置（索引 = 页码 - 1）
                        completed_chapters[page_num - 1] = chapter
                        print(f"完成第 {page_num} 页处理，保存到索引 {page_num - 1}")
                    except Exception as e:
                        print(f"处理第 {page_num} 页时出错: {str(e)}")
                        raise
                
                # 验证所有章节都已处理完成
                if None in completed_chapters:
                    missing_pages = [i + 1 for i, c in enumerate(completed_chapters) if c is None]
                    raise EPUBBuilderError(f"部分页面处理失败: {missing_pages}")
                
                print("所有章节处理完成，按顺序添加到EPUB中...")
                # 按顺序添加章节到EPUB
                for chapter in completed_chapters:
                    if chapter:
                        chapters.append(chapter)
                        spine.append(chapter)
            
            # 添加导航
            book.toc = chapters
            book.spine = spine
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            
            # 生成EPUB
            epub.write_epub(str(output_path), book, {})
            
            print(f"EPUB创建完成: {output_path}")
            print(f"总页数: {len(chapters)}")
            
            return ProcessingResult(
                success=True,
                message="EPUB创建成功"
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"EPUB创建失败: {str(e)}",
                error=e
            )
    
    def _add_metadata(self, book: epub.EpubBook, metadata: EPUBMetadata) -> None:
        """添加元数据"""
        if metadata.title:
            book.set_title(metadata.title)
        
        if metadata.creator:
            book.add_author(metadata.creator)
        
        book.set_language(metadata.language)
        
        if metadata.identifier:
            book.set_identifier(metadata.identifier)
        
        # 添加更新时间
        book.add_metadata(
            'DC',
            'date',
            datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            {'property': 'dcterms:modified'}
        )
        
        # 添加其他元数据
        if metadata.additional_metadata:
            for key, value in metadata.additional_metadata.items():
                try:
                    # 跳过单字符的键名
                    if ':' in key and len(key.split(':')[1]) > 1:
                        namespace, name = key.split(':', 1)
                        book.add_metadata(namespace, name, value)
                except Exception as e:
                    print(f"跳过无效的元数据: {key} = {value}")
                    continue
    
    def _create_style(self) -> str:
        """创建样式表"""
        return '''
            @namespace epub "http://www.idpf.org/2007/ops";
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: white;
            }
            div.image-container {
                width: 100%;
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
                padding: 0;
                page-break-after: always;
            }
            img {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
                margin: 0;
                padding: 0;
            }
        '''
    
    def _add_cover(
        self,
        book: epub.EpubBook,
        cover_image: ProcessedImage,
        target_long_edge: int,
        resize_to_original: bool
    ) -> None:
        """添加封面"""
        try:
            # 获取超分辨率后的图片路径
            project_dir = cover_image.processed_path.parent.parent
            upscaled_path = self._find_upscaled_image(project_dir, cover_image.processed_path.name)
            if not upscaled_path:
                raise EPUBBuilderError(f"找不到超分辨率处理后的封面图片: {cover_image.processed_path.name}")
            
            print(f"处理封面图片: {upscaled_path}")
            
            # 加载图片
            img = self.image_processor.load_image(upscaled_path)
            if not img:
                raise EPUBBuilderError("加载封面图片失败")
            
            # 调整大小
            if resize_to_original:
                original_img = self.image_processor.load_image(cover_image.original_path)
                if original_img:
                    width, height = original_img.size
                else:
                    width, height = img.size
            else:
                width, height = img.size
                if max(width, height) > target_long_edge:
                    width, height = self.image_processor.calculate_optimal_size(
                        width, height, target_long_edge
                    )
            
            # 调整图片大小并转换为字节
            img_data = self.image_processor.resize_image(
                img,
                (width, height),
                format=self.image_processor.config.output_format,
                quality=self.image_processor.config.output_quality
            )
            
            # 获取实际的图片格式
            output_format = self.image_processor.config.output_format.lower()
            
            # 创建封面图片项
            cover_image = epub.EpubImage()
            cover_image.uid = 'cover-image'
            cover_image.file_name = f'images/cover.{output_format}'
            cover_image.media_type = f'image/{output_format}'
            cover_image.content = img_data
            book.add_item(cover_image)
            
            # 设置为封面
            book.set_cover(cover_image.file_name, img_data)
            
            # 创建封面章节
            cover_chapter = epub.EpubHtml(
                title='封面',
                file_name='cover.xhtml',
                content=f'''
                    <html>
                        <head>
                            <title>封面</title>
                            <link rel="stylesheet" type="text/css" href="style/nav.css" />
                        </head>
                        <body>
                            <div class="image-container">
                                <img src="{cover_image.file_name}" alt="封面" 
                                     width="{width}" height="{height}" />
                            </div>
                        </body>
                    </html>
                '''
            )
            book.add_item(cover_chapter)
            book.spine = ['nav', cover_chapter]
            
        except Exception as e:
            raise EPUBBuilderError(f"添加封面失败: {str(e)}")
    
    def _create_image_chapter(
        self,
        book: epub.EpubBook,
        image: ProcessedImage,
        page_num: int,
        target_long_edge: int,
        resize_to_original: bool
    ) -> epub.EpubHtml:
        """创建图片章节"""
        try:
            # 获取超分辨率后的图片路径
            project_dir = image.processed_path.parent.parent
            upscaled_path = self._find_upscaled_image(project_dir, image.processed_path.name)
            if not upscaled_path:
                raise EPUBBuilderError(f"找不到超分辨率处理后的图片: {image.processed_path.name}")
            
            print(f"处理第 {page_num} 页图片: {upscaled_path}")
            
            # 加载图片
            img = self.image_processor.load_image(upscaled_path)
            if not img:
                raise EPUBBuilderError(f"加载图片失败: {upscaled_path}")
            
            # 调整大小
            if resize_to_original:
                original_img = self.image_processor.load_image(image.original_path)
                if original_img:
                    width, height = original_img.size
                else:
                    width, height = img.size
            else:
                width, height = img.size
                if max(width, height) > target_long_edge:
                    width, height = self.image_processor.calculate_optimal_size(
                        width, height, target_long_edge
                    )
            
            # 调整图片大小并转换为字节
            img_data = self.image_processor.resize_image(
                img,
                (width, height),
                format=self.image_processor.config.output_format,
                quality=self.image_processor.config.output_quality
            )
            
            # 获取实际的图片格式
            output_format = self.image_processor.config.output_format.lower()
            
            # 添加图片
            image_item = epub.EpubItem(
                uid=f'image_{page_num}',
                file_name=f'images/image_{page_num}.{output_format}',
                media_type=f'image/{output_format}',
                content=img_data
            )
            book.add_item(image_item)
            
            # 创建章节
            chapter = epub.EpubHtml(
                title=f'第{page_num}页',
                file_name=f'page_{page_num}.xhtml',
                content=f'''
                    <html>
                        <head>
                            <link rel="stylesheet" type="text/css" href="style/nav.css" />
                        </head>
                        <body>
                            <div class="image-container">
                                <img src="{image_item.file_name}" alt="第{page_num}页" 
                                     width="{width}" height="{height}" />
                            </div>
                        </body>
                    </html>
                '''
            )
            book.add_item(chapter)
            
            return chapter
            
        except Exception as e:
            raise EPUBBuilderError(f"创建图片章节失败: {str(e)}") 