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
import shutil
import zipfile
import xml.etree.ElementTree as ET
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
    """EPUB构建器 - 保留原始结构和内容"""
    
    def __init__(self):
        """初始化EPUB构建器"""
        config_manager = ConfigManager()
        self.image_processor = ImageProcessor(config_manager.config.upscale)
        self.file_manager = FileManager()
        self.max_workers = cpu_count()
    
    def _find_upscaled_image(self, project_dir: Path, image_name: str) -> Optional[Path]:
        """查找超分辨率处理后的图片"""
        try:
            base_name = Path(image_name).stem
            
            # 构建可能的文件名模式
            patterns = [
                f"*{base_name}.*",
                f"[0-9]x-{base_name}.*",
            ]
            
            # 在所有batch目录中查找
            all_matches = []
            for batch_dir in project_dir.glob('upscaled/batch_*/outputs'):
                if batch_dir.exists():
                    for pattern in patterns:
                        matches = list(batch_dir.glob(pattern))
                        if matches:
                            all_matches.extend(matches)
                        
            # 也在主输出目录中查找
            main_output = project_dir / 'upscaled' / 'outputs'
            if main_output.exists():
                for pattern in patterns:
                    matches = list(main_output.glob(pattern))
                    if matches:
                        all_matches.extend(matches)
            
            if all_matches:
                return all_matches[0]
            
            # 后备方案：按页码匹配
            all_files = []
            for batch_dir in project_dir.glob('upscaled/batch_*/outputs'):
                if batch_dir.exists():
                    all_files.extend(batch_dir.glob('*.png'))
                    all_files.extend(batch_dir.glob('*.jpg'))
            
            if all_files:
                page_match = re.search(r'(\d+)', base_name)
                if page_match:
                    page_num = page_match.group(1)
                    for f in all_files:
                        if page_num in f.stem:
                            return f
                return sorted(all_files)[0]
            
            return None
            
        except Exception as e:
            print(f"查找图片时出错: {str(e)}")
            return None
    
    def create_epub(
        self,
        images: List[ProcessedImage],
        output_path: Path,
        metadata: EPUBMetadata,
        target_long_edge: int = 1872,
        resize_to_original: bool = False,
        original_epub_path: Optional[Path] = None
    ) -> ProcessingResult:
        """创建EPUB文件 - 保留原始结构和内容"""
        try:
            print("\n开始创建EPUB文件...")
            
            if original_epub_path and original_epub_path.exists():
                # 使用新方法：复制并修改原始EPUB
                return self._create_epub_from_original(
                    images, output_path, original_epub_path, 
                    target_long_edge, resize_to_original
                )
            else:
                # 使用旧方法：重新创建EPUB（兼容性保留）
                return self._create_epub_from_scratch(
                    images, output_path, metadata, 
                    target_long_edge, resize_to_original
                )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"EPUB创建失败: {str(e)}",
                error=e
            )
    
    def _create_epub_from_original(
        self,
        images: List[ProcessedImage],
        output_path: Path,
        original_epub_path: Path,
        target_long_edge: int = 1872,
        resize_to_original: bool = False
    ) -> ProcessingResult:
        """从原始EPUB创建，只替换图片"""
        try:
            print(f"复制原始EPUB: {original_epub_path}")
            
            # 创建临时目录
            temp_dir = output_path.parent / f"temp_epub_{output_path.stem}"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True)
            
            # 解压原始EPUB
            with zipfile.ZipFile(original_epub_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # 构建图片映射表
            image_map = {}
            for img in images:
                project_dir = img.processed_path.parent.parent
                upscaled_path = self._find_upscaled_image(project_dir, img.processed_path.name)
                if upscaled_path:
                    # 使用原始文件名作为键
                    orig_filename = img.original_path.name
                    image_map[orig_filename] = upscaled_path
                    # 也添加 basename 作为键（用于不同扩展名的情况）
                    image_map[Path(orig_filename).stem] = upscaled_path
            
            print(f"找到 {len(image_map)} 张超分辨率图片")
            
            # 替换图片
            replaced_count = 0
            for img_file in temp_dir.rglob('*'):
                if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    # 尝试匹配
                    upscaled_path = None
                    if img_file.name in image_map:
                        upscaled_path = image_map[img_file.name]
                    elif img_file.stem in image_map:
                        upscaled_path = image_map[img_file.stem]
                    
                    if upscaled_path and upscaled_path.exists():
                        # 处理图片（调整尺寸）
                        img = self.image_processor.load_image(upscaled_path)
                        if img:
                            if resize_to_original:
                                # 保持原始尺寸
                                pass
                            else:
                                # 调整到目标尺寸
                                width, height = img.size
                                if max(width, height) > target_long_edge:
                                    ratio = target_long_edge / max(width, height)
                                    new_size = (int(width * ratio), int(height * ratio))
                                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                            
                            # 保存替换后的图片
                            img.save(img_file, 'JPEG', quality=95)
                            replaced_count += 1
            
            print(f"替换了 {replaced_count} 张图片")
            
            # 重新打包EPUB
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in temp_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(temp_dir)
                        zipf.write(file_path, arcname)
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
            
            print(f"EPUB创建完成: {output_path}")
            
            return ProcessingResult(
                success=True,
                message=f"EPUB创建成功，替换了 {replaced_count} 张图片"
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"EPUB创建失败: {str(e)}",
                error=e
            )
    
    def _create_epub_from_scratch(
        self,
        images: List[ProcessedImage],
        output_path: Path,
        metadata: EPUBMetadata,
        target_long_edge: int = 1872,
        resize_to_original: bool = False
    ) -> ProcessingResult:
        """从头创建EPUB（旧方法，作为后备）"""
        try:
            print("使用后备方法创建EPUB...")
            
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
                
                completed_chapters = [None] * len(images)
                
                for future in concurrent.futures.as_completed(future_to_page):
                    page_num = future_to_page[future]
                    try:
                        chapter = future.result()
                        completed_chapters[page_num - 1] = chapter
                    except Exception as e:
                        print(f"处理第 {page_num} 页时出错: {str(e)}")
                        raise
                
                if None in completed_chapters:
                    missing_pages = [i + 1 for i, c in enumerate(completed_chapters) if c is None]
                    raise EPUBBuilderError(f"部分页面处理失败: {missing_pages}")
                
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
            project_dir = cover_image.processed_path.parent.parent
            upscaled_path = self._find_upscaled_image(project_dir, cover_image.processed_path.name)
            if not upscaled_path:
                raise EPUBBuilderError(f"找不到超分辨率处理后的封面图片: {cover_image.processed_path.name}")
            
            print(f"处理封面图片: {upscaled_path}")
            
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
