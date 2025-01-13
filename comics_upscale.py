import os
import fitz  # PyMuPDF
import ebooklib
from ebooklib import epub
from PIL import Image
import io
import warnings
from datetime import datetime
import shutil
from tqdm import tqdm
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import time

# 检查必要的依赖
try:
    import yaml
except ImportError:
    print("缺少必要的依赖，请运行以下命令安装：")
    print("pip install PyYAML")
    exit(1)

# 抑制ebooklib警告
warnings.filterwarnings('ignore', category=UserWarning, module='ebooklib.epub')
warnings.filterwarnings('ignore', category=FutureWarning, module='ebooklib.epub')

def monitor_progress(output_dir, total_files, pbar):
    """
    监控超分处理进度的函数
    :param output_dir: 输出目录
    :param total_files: 总文件数
    :param pbar: tqdm进度条对象
    """
    processed_files = set()
    
    while len(processed_files) < total_files:
        # 扫描所有批次目录
        all_files = set()
        for batch_dir in os.listdir(output_dir):
            if batch_dir.startswith('batch_'):
                batch_outputs = os.path.join(output_dir, batch_dir, 'outputs')
                if os.path.exists(batch_outputs):
                    all_files.update(os.listdir(batch_outputs))
        
        # 检查主输出目录
        main_outputs = os.path.join(output_dir, 'outputs')
        if os.path.exists(main_outputs):
            all_files.update(os.listdir(main_outputs))
        
        # 更新进度
        new_files = all_files - processed_files
        if new_files:
            pbar.update(len(new_files))
            processed_files.update(new_files)
        
        time.sleep(0.5)  # 每0.5秒检查一次

def process_batch(args):
    """
    处理单个批次的图片的独立函数
    :param args: (config_path, batch_output_dir) 元组
    :return: 是否成功
    """
    config_path, batch_output_dir = args
    try:
        final2x_path = os.path.join(os.getcwd(), "Final2X", "Final2x-core.exe")
        if not os.path.exists(final2x_path):
            raise FileNotFoundError(f"未找到Final2X: {final2x_path}")
        
        cmd = [final2x_path, "--YAML", config_path, "--NOTOPENFOLDER"]
        
        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"超分处理出错:")
            print(result.stderr)
            return False
        
        return True
    except Exception as e:
        print(f"超分处理异常: {str(e)}")
        return False

class ImageExtractor:
    def __init__(self):
        """初始化图片提取器"""
        self.temp_dir = os.path.join(os.getcwd(), 'temp')
        os.makedirs(self.temp_dir, exist_ok=True)

    def cleanup(self):
        """清理临时文件夹"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def setup_project_folders(self, file_path):
        """创建项目文件夹结构"""
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = f"{base_name}_extracted_{timestamp}"
        
        project_dir = os.path.join("projects", project_name)
        subdirs = ['original', 'images']
        
        for subdir in subdirs:
            full_path = os.path.join(project_dir, subdir)
            os.makedirs(full_path, exist_ok=True)
            
        original_file = os.path.join(project_dir, 'original', os.path.basename(file_path))
        shutil.copy2(file_path, original_file)
        
        return project_dir

    def extract_from_pdf(self, file_path, project_dir):
        """从PDF提取图片"""
        print("\n开始从PDF提取图片...")
        images = []
        doc = fitz.open(file_path)
        
        for page_num in tqdm(range(len(doc)), desc="提取PDF页面"):
            page = doc[page_num]
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            image_path = os.path.join(project_dir, 'images', f'page_{page_num + 1:04d}.jpg')
            img.save(image_path, 'JPEG', quality=95)
            images.append(image_path)
        
        return images

    def extract_from_epub(self, file_path, project_dir):
        """从EPUB提取图片"""
        print("\n开始从EPUB提取图片...")
        images = []
        book = epub.read_epub(file_path)
        page_num = 1

        # 获取文档信息
        print(f"书籍标题: {book.get_metadata('DC', 'title')}")
        print(f"作者: {book.get_metadata('DC', 'creator')}")

        # 创建图片ID到内容的映射
        image_map = {}
        
        # 收集所有图片
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                try:
                    img_data = item.get_content()
                    img = Image.open(io.BytesIO(img_data))
                    
                    # 检查图片大小
                    width, height = img.size
                    if width >= 100 and height >= 100:
                        image_map[item.file_name] = {
                            'data': img_data,
                            'mode': img.mode,
                            'size': (width, height),
                            'id': item.id
                        }
                except Exception as e:
                    print(f"处理图片时出错 {item.get_name()}: {str(e)}")

        # 按HTML文档顺序处理图片
        processed_images = set()
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                from bs4 import BeautifulSoup
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
                        image_path = os.path.join(project_dir, 'images', f'page_{page_num:04d}.jpg')
                        
                        # 处理图片
                        img = Image.open(io.BytesIO(img_info['data']))
                        if img.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', img_info['size'], 'white')
                            if img.mode == 'RGBA':
                                background.paste(img, mask=img.split()[3])
                            else:
                                background.paste(img, mask=img.split()[1])
                            img = background
                        
                        img = img.convert('RGB')
                        img.save(image_path, 'JPEG', quality=95)
                        
                        images.append(image_path)
                        processed_images.add(matching_image)
                        print(f"已提取图片 {page_num}: {matching_image} -> {os.path.basename(image_path)}")
                        page_num += 1

        print(f"\nEPUB处理完成，共提取 {len(images)} 张图片")
        return images

    def extract_images(self, file_path):
        """提取图片的主函数"""
        try:
            project_dir = self.setup_project_folders(file_path)
            print(f"\n项目文件夹已创建: {project_dir}")

            file_ext = os.path.splitext(file_path)[1].lower()
            original_file = os.path.join(project_dir, 'original', os.path.basename(file_path))

            print(f"\n开始处理文件: {file_path}")
            print(f"文件格式: {file_ext}")
            
            if file_ext == '.pdf':
                images = self.extract_from_pdf(original_file, project_dir)
            elif file_ext == '.epub':
                images = self.extract_from_epub(original_file, project_dir)
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")

            print(f"\n处理完成!")
            print(f"提取图片总数: {len(images)}")
            print(f"输出目录: {os.path.join(project_dir, 'images')}")

            return images, project_dir

        except Exception as e:
            print(f"\n处理文件时出错: {str(e)}")
            import traceback
            print("\n详细错误信息:")
            print(traceback.format_exc())
            return [], None
        finally:
            self.cleanup()

    def repack_epub(self, original_file, new_images_dir, output_path, resize_to_original=False):
        """
        将超分辨率后的图片重新打包回EPUB文件
        """
        from datetime import datetime
        from PIL import Image
        import io
        
        print("\n开始重新打包EPUB文件...")
        try:
            # 读取原始EPUB
            book = epub.read_epub(original_file)
            
            # 创建新的EPUB
            new_book = epub.EpubBook()
            
            # 复制元数据
            for namespace, values in book.metadata.items():
                for v in values:
                    try:
                        if not v or len(v) < 2:  # 跳过无效的元数据
                            continue
                            
                        # 获取基本元数据
                        name, value = v[0], v[1]
                        
                        # 处理属性
                        attrs = {}
                        if len(v) > 2 and isinstance(v[2], dict):
                            attrs = v[2]
                        
                        # 特殊处理 dcterms:modified
                        if attrs.get('property') == 'dcterms:modified':
                            value = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                        
                        # 添加元数据
                        if value is not None:  # 确保值不是None
                            new_book.add_metadata(namespace, name, value, attrs)
                        
                    except Exception as e:
                        print(f"警告: 跳过元数据 {v[0] if v and len(v) > 0 else 'unknown'}: {str(e)}")
                        continue
            
            # 添加必要的元数据
            if not any(v[1].get('property') == 'dcterms:modified' for values in new_book.metadata.values() for v in values if len(v) > 1 and isinstance(v[1], dict)):
                new_book.add_metadata('DC', 'date', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), {'property': 'dcterms:modified'})
            
            # 复制spine和toc
            new_book.spine = book.spine
            new_book.toc = book.toc
            
            # Final2X输出目录
            final2x_output_dir = os.path.join(new_images_dir, 'outputs')
            
            # 获取输出目录中的所有文件并建立映射关系
            output_files = {}
            if os.path.exists(final2x_output_dir):
                for file in os.listdir(final2x_output_dir):
                    # 从文件名中提取页码
                    if 'page_' in file:
                        try:
                            page_num = int(file.split('page_')[1].split('.')[0])
                            output_files[page_num] = file
                        except:
                            continue
            else:
                print(f"警告: 输出目录不存在: {final2x_output_dir}")

            # 用于记录已处理的图片
            processed_images = {}
            image_mapping = {}  # 用于记录原始图片到页码的映射
            
            # 第一遍扫描：建立原始图片到页码的映射
            image_count = 1
            
            # 首先处理封面
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_COVER or \
                   (item.get_type() == ebooklib.ITEM_IMAGE and ('cover' in item.id.lower() or 'cover' in item.file_name.lower())):
                    try:
                        img = Image.open(io.BytesIO(item.content))
                        if img.size[0] >= 100 and img.size[1] >= 100:
                            image_mapping[item.id] = image_count
                            print(f"找到封面图片 ID: {item.id}, 页码: {image_count}")
                            image_count += 1
                            break
                    except:
                        continue

            # 然后处理其他图片
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_IMAGE:
                    # 跳过已处理的封面
                    if item.id in image_mapping:
                        continue
                        
                    try:
                        img = Image.open(io.BytesIO(item.content))
                        if img.size[0] >= 100 and img.size[1] >= 100:
                            image_mapping[item.id] = image_count
                            image_count += 1
                    except:
                        continue

            print(f"图片映射关系: 共 {len(image_mapping)} 张图片")
            for img_id, page_num in sorted(image_mapping.items(), key=lambda x: x[1]):
                print(f"ID: {img_id} -> 页码: {page_num}")

            # 处理所有项目
            for item in tqdm(book.get_items(), desc="打包EPUB"):
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    # 复制文档，保留原始样式
                    new_book.add_item(item)
                elif item.get_type() == ebooklib.ITEM_STYLE:
                    # 复制CSS样式
                    new_book.add_item(item)
                elif item.get_type() == ebooklib.ITEM_IMAGE:
                    try:
                        # 获取当前图片对应的页码
                        page_num = image_mapping.get(item.id)
                        if not page_num:
                            new_book.add_item(item)
                            continue

                        # 查找对应的超分辨率图片
                        if page_num in output_files:
                            new_image_path = os.path.join(final2x_output_dir, output_files[page_num])
                            print(f"处理第 {page_num} 页图片: {output_files[page_num]}")
                            if 'cover' in item.id.lower() or 'cover' in item.file_name.lower():
                                print(f"处理封面图片: {output_files[page_num]}")
                            
                            if resize_to_original:
                                # 获取原始图片尺寸
                                original_img = Image.open(io.BytesIO(item.content))
                                original_size = original_img.size
                                
                                # 读取超分辨率后的图片并调整大小
                                upscaled_img = Image.open(new_image_path)
                                resized_img = upscaled_img.resize(original_size, Image.Resampling.LANCZOS)
                                
                                # 转换为字节
                                img_byte_arr = io.BytesIO()
                                resized_img.save(img_byte_arr, format='PNG', quality=95, optimize=True)
                                new_image_data = img_byte_arr.getvalue()
                                
                                print(f"已将图片缩放至原始大小: {original_size}")
                            else:
                                # 直接读取超分辨率后的图片
                                with open(new_image_path, 'rb') as f:
                                    new_image_data = f.read()
                            
                            # 创建新的EpubImage，保持原始属性
                            new_image = epub.EpubImage()
                            new_image.id = item.id
                            new_image.file_name = item.file_name
                            new_image.media_type = item.media_type  # 保持原始媒体类型
                            new_image.content = new_image_data
                            
                            # 复制其他属性
                            if hasattr(item, 'properties'):
                                new_image.properties = item.properties
                            
                            new_book.add_item(new_image)
                            processed_images[item.id] = True
                        else:
                            print(f"未找到对应的超分辨率图片，使用原图: page_{page_num:04d}")
                            new_book.add_item(item)
                    except Exception as e:
                        print(f"处理图片时出错 {item.id}: {str(e)}")
                        new_book.add_item(item)
                else:
                    # 复制其他类型的项目
                    new_book.add_item(item)
            
            # 保存新的EPUB
            epub.write_epub(output_path, new_book, {})
            print(f"\nEPUB打包完成: {output_path}")
            print(f"成功替换图片数量: {len(processed_images)}")
            
            return True
            
        except Exception as e:
            print(f"\n打包EPUB时出错: {str(e)}")
            import traceback
            print("\n详细错误信息:")
            print(traceback.format_exc())
            return False

    def process_book(self, input_file, output_file, new_images_dir, resize_to_original=False, create_new=False, create_eink=False):
        """
        处理电子书：提取图片，替换超分辨率后的图片并重新打包
        :param create_eink: 是否创建适配电子墨水屏的EPUB
        """
        try:
            file_ext = os.path.splitext(input_file)[1].lower()
            
            if file_ext == '.epub':
                if create_eink:
                    return self.create_eink_epub(input_file, new_images_dir, output_file, resize_to_original=resize_to_original)
                elif create_new:
                    return self.create_new_epub(input_file, new_images_dir, output_file, resize_to_original=resize_to_original)
                else:
                    return self.repack_epub(input_file, new_images_dir, output_file, resize_to_original=resize_to_original)
            else:
                raise ValueError(f"暂不支持的文件格式: {file_ext}")
            
        except Exception as e:
            print(f"\n处理文件时出错: {str(e)}")
            return False

    def generate_final2x_config(self, input_images, output_dir, model_name, scale=4, batch_id=None):
        """
        生成Final2X配置文件
        :param input_images: 输入图片路径列表
        :param output_dir: 输出目录
        :param model_name: 使用的模型名称
        :param scale: 放大倍数，默认4倍
        :param batch_id: 批次ID，用于生成唯一的配置文件
        :return: 配置文件路径
        """
        config = {
            'device': 'auto',
            'input_path': input_images,
            'output_path': output_dir,
            'pretrained_model_name': model_name,
            'target_scale': scale
        }
        
        # 为每个批次创建独立的配置文件
        config_filename = f'final2x_config_{batch_id}.yaml' if batch_id is not None else 'final2x_config.yaml'
        config_path = os.path.join(self.temp_dir, config_filename)
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        import yaml
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
        
        return config_path

    def upscale_images(self, images, output_dir, model_name='RealESRGAN_RealESRGAN_x4plus_anime_6B_4x.pth', scale=4, num_processes=4):
        """
        使用Final2X对图片进行超分辨率处理，支持多进程并行处理
        :param images: 图片路径列表
        :param output_dir: 输出目录
        :param model_name: 使用的模型名称，默认使用RealESRGAN x4plus anime模型
        :param scale: 放大倍数，默认4倍
        :param num_processes: 并行处理的进程数，默认4个
        :return: 是否成功
        """
        try:
            print("\n开始超分辨率处理...")
            print(f"使用模型: {model_name}")
            print(f"放大倍数: {scale}x")
            print(f"并行进程数: {num_processes}")
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 将图片列表分成N组
            batch_size = len(images) // num_processes
            if batch_size == 0:
                batch_size = 1
            image_batches = []
            for i in range(0, len(images), batch_size):
                batch = images[i:i + batch_size]
                if batch:  # 确保批次不为空
                    image_batches.append(batch)
            
            print(f"图片总数: {len(images)}")
            print(f"分成 {len(image_batches)} 批处理")
            
            # 为每个批次创建单独的配置文件和输出目录
            configs = []
            for i, batch in enumerate(image_batches):
                batch_output_dir = os.path.join(output_dir, f'batch_{i}')
                os.makedirs(batch_output_dir, exist_ok=True)
                
                config_path = self.generate_final2x_config(
                    batch,
                    batch_output_dir,
                    model_name,
                    scale,
                    batch_id=i  # 添加批次ID
                )
                configs.append((config_path, batch_output_dir))
            
            # 创建进度条
            pbar = tqdm(total=len(images), desc="超分进度", unit="张")
            
            # 启动进度监控线程
            import threading
            import time
            monitor_thread = threading.Thread(
                target=monitor_progress,
                args=(output_dir, len(images), pbar),
                daemon=True
            )
            monitor_thread.start()
            
            # 使用进程池并行处理
            print("\n开始并行处理...")
            with multiprocessing.Pool(processes=num_processes) as pool:
                results = []
                for config_path, batch_output_dir in configs:
                    result = pool.apply_async(process_batch, ((config_path, batch_output_dir),))
                    results.append(result)
                
                # 等待所有进程完成
                success = True
                for i, result in enumerate(results):
                    if not result.get():
                        print(f"批次 {i} 处理失败")
                        success = False
                    else:
                        print(f"批次 {i} 处理完成")
            
            # 等待进度监控线程完成最后的更新
            time.sleep(2)
            pbar.close()
            
            # 合并所有批次的输出
            print("\n合并输出...")
            for i, (config_path, batch_output_dir) in enumerate(configs):
                batch_outputs = os.path.join(batch_output_dir, 'outputs')
                if os.path.exists(batch_outputs):
                    # 移动所有输出文件到主输出目录
                    main_output = os.path.join(output_dir, 'outputs')
                    os.makedirs(main_output, exist_ok=True)
                    for file in os.listdir(batch_outputs):
                        src = os.path.join(batch_outputs, file)
                        dst = os.path.join(main_output, file)
                        if os.path.exists(dst):
                            os.remove(dst)
                        shutil.move(src, dst)
                    # 删除批次目录
                    shutil.rmtree(batch_output_dir)
                # 删除配置文件
                if os.path.exists(config_path):
                    os.remove(config_path)
            
            if success:
                print("\n所有批次处理完成!")
            return success
            
        except Exception as e:
            print(f"超分处理出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def create_new_epub(self, original_file, new_images_dir, output_path, resize_to_original=False):
        """
        创建全新的EPUB文件，使用超分辨率后的图片
        """
        from datetime import datetime
        from PIL import Image
        import io
        
        print("\n开始创建新的EPUB文件...")
        try:
            # 读取原始EPUB获取元数据
            original_book = epub.read_epub(original_file)
            
            # 创建新的EPUB
            book = epub.EpubBook()
            
            # 复制基本元数据
            for namespace, values in original_book.metadata.items():
                for v in values:
                    try:
                        if not v or len(v) < 2:
                            continue
                        name, value = v[0], v[1]
                        if value is not None:
                            book.add_metadata(namespace, name, value)
                    except Exception as e:
                        print(f"警告: 跳过元数据 {v[0] if v and len(v) > 0 else 'unknown'}: {str(e)}")

            # 添加更新时间
            book.add_metadata('DC', 'date', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), 
                             {'property': 'dcterms:modified'})

            # 创建样式
            style = '''
            @namespace epub "http://www.idpf.org/2007/ops";
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
            }
            div.image-container {
                text-align: center;
                page-break-after: always;
                margin: 0;
                padding: 0;
            }
            img {
                max-width: 100%;
                max-height: 100vh;
                margin: 0;
                padding: 0;
            }
            '''
            
            nav_css = epub.EpubItem(
                uid="style_nav",
                file_name="style/nav.css",
                media_type="text/css",
                content=style
            )
            book.add_item(nav_css)

            # 获取超分辨率后的图片
            final2x_output_dir = os.path.join(new_images_dir, 'outputs')
            if not os.path.exists(final2x_output_dir):
                raise FileNotFoundError(f"未找到超分辨率图片目录: {final2x_output_dir}")

            # 获取所有超分辨率后的图片并排序
            image_files = []
            for file in os.listdir(final2x_output_dir):
                if 'page_' in file:
                    try:
                        page_num = int(file.split('page_')[1].split('.')[0])
                        image_files.append((page_num, file))
                    except:
                        continue
            image_files.sort()  # 按页码排序

            # 创建章节和图片
            chapters = []
            spine = ['nav']
            
            # 添加封面页（使用第一页作为封面）
            if len(image_files) > 0:
                image_file = image_files[0]  # 获取第一个图片作为封面
                image_path = os.path.join(final2x_output_dir, image_file[1])
                
                if resize_to_original:
                    # 获取原始图片尺寸
                    original_items = [item for item in original_book.get_items() if item.get_type() == ebooklib.ITEM_IMAGE]
                    if len(original_items) > 0:
                        original_img = Image.open(io.BytesIO(original_items[0].content))
                        original_size = original_img.size
                        
                        # 调整大小
                        img = Image.open(image_path)
                        img = img.resize(original_size, Image.Resampling.LANCZOS)
                        
                        # 保存到内存
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='PNG', quality=95, optimize=True)
                        img_data = img_byte_arr.getvalue()
                    else:
                        with open(image_path, 'rb') as f:
                            img_data = f.read()
                else:
                    with open(image_path, 'rb') as f:
                        img_data = f.read()

                # 添加封面图片
                cover_image = epub.EpubImage()
                cover_image.uid = 'cover-image'
                cover_image.file_name = 'images/cover.png'
                cover_image.media_type = 'image/png'
                cover_image.content = img_data
                book.add_item(cover_image)

                # 创建封面章节
                chapter_content = f'''<?xml version="1.0" encoding="utf-8"?>
                <!DOCTYPE html>
                <html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh" xml:lang="zh">
                    <head>
                        <title>封面</title>
                        <link rel="stylesheet" type="text/css" href="style/nav.css" />
                    </head>
                    <body>
                        <div class="image-container">
                            <img src="images/cover.png" alt="封面" />
                        </div>
                    </body>
                </html>
                '''
                
                cover_chapter = epub.EpubHtml(
                    title='封面',
                    file_name='cover.xhtml',
                    content=chapter_content,
                    lang='zh'
                )
                book.add_item(cover_chapter)
                chapters.append(cover_chapter)
                spine.append(cover_chapter)

                # 设置为电子书封面
                book.set_cover('images/cover.png', img_data)

            # 处理剩余的图片（从第二张开始）
            for page_num, image_file in enumerate(image_files[1:], 1):
                # 读取图片
                image_path = os.path.join(final2x_output_dir, image_file[1])
                
                if resize_to_original:
                    # 获取原始图片尺寸
                    original_items = [item for item in original_book.get_items() if item.get_type() == ebooklib.ITEM_IMAGE]
                    if page_num <= len(original_items):
                        original_img = Image.open(io.BytesIO(original_items[page_num-1].content))
                        original_size = original_img.size
                        
                        # 调整大小
                        img = Image.open(image_path)
                        img = img.resize(original_size, Image.Resampling.LANCZOS)
                        
                        # 保存到内存
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='PNG', quality=95, optimize=True)
                        img_data = img_byte_arr.getvalue()
                    else:
                        with open(image_path, 'rb') as f:
                            img_data = f.read()
                else:
                    with open(image_path, 'rb') as f:
                        img_data = f.read()

                # 添加图片
                image_item = epub.EpubItem(
                    uid=f'image_{page_num}',
                    file_name=f'images/image_{page_num}.png',
                    media_type='image/png',
                    content=img_data
                )
                book.add_item(image_item)

                # 创建包含图片的章节
                chapter_content = f'''
                <html>
                    <head>
                        <link rel="stylesheet" type="text/css" href="style/nav.css" />
                    </head>
                    <body>
                        <div class="image-container">
                            <img src="images/image_{page_num}.png" alt="第{page_num}页" 
                                 width="{original_size[0]}" height="{original_size[1]}" />
                        </div>
                    </body>
                </html>
                '''
                
                chapter = epub.EpubHtml(
                    title=f'第{page_num}页',
                    file_name=f'page_{page_num}.xhtml',
                    content=chapter_content,
                    lang='zh'
                )
                book.add_item(chapter)
                chapters.append(chapter)
                spine.append(chapter)

            # 添加导航
            book.toc = chapters
            book.spine = spine
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            # 生成EPUB
            epub.write_epub(output_path, book, {})
            print(f"\nEPUB创建完成: {output_path}")
            print(f"总页数: {len(chapters)}")
            
            return True
            
        except Exception as e:
            print(f"\n创建EPUB时出错: {str(e)}")
            import traceback
            print("\n详细错误信息:")
            print(traceback.format_exc())
            return False

    def process_image_for_eink(self, args):
        """
        处理单个图片的函数，用于并行处理
        """
        image_path, actual_page_num, target_long_edge = args
        try:
            img = Image.open(image_path)
            
            # 计算最佳显示尺寸
            width, height = img.size
            new_width, new_height = self.calculate_optimal_size(width, height, target_long_edge)
            
            # 调整图片大小
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 转换为字节
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG', quality=95, optimize=True)
            img_data = img_byte_arr.getvalue()
            
            return {
                'page_num': actual_page_num,
                'width': new_width,
                'height': new_height,
                'data': img_data,
                'success': True
            }
        except Exception as e:
            print(f"处理图片出错 {image_path}: {str(e)}")
            return {
                'page_num': actual_page_num,
                'success': False,
                'error': str(e)
            }

    def create_eink_epub(self, original_file, new_images_dir, output_path, target_long_edge=1872, resize_to_original=False):
        """
        创建适配电子墨水屏的EPUB文件
        :param target_long_edge: 目标长边尺寸，默认1872
        """
        from datetime import datetime
        from PIL import Image
        import io
        
        print(f"\n开始创建电子墨水屏EPUB文件 (长边 {target_long_edge})...")
        try:
            # 读取原始EPUB获取元数据
            original_book = epub.read_epub(original_file)
            
            # 创建新的EPUB
            book = epub.EpubBook()
            
            # 复制所有元数据，包括标题、作者、出版日期等
            for namespace, values in original_book.metadata.items():
                for v in values:
                    try:
                        if not v or len(v) < 2:
                            continue
                        name, value = v[0], v[1]
                        attrs = {}
                        if len(v) > 2 and isinstance(v[2], dict):
                            attrs = v[2]
                        if value is not None:
                            book.add_metadata(namespace, name, value, attrs)
                            if name == 'title':
                                print(f"保留书籍标题: {value}")
                            elif name == 'creator':
                                print(f"保留作者信息: {value}")
                    except Exception as e:
                        print(f"警告: 跳过元数据 {v[0] if v and len(v) > 0 else 'unknown'}: {str(e)}")

            # 添加更新时间
            book.add_metadata('DC', 'date', datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"), 
                             {'property': 'dcterms:modified'})

            # 创建优化的电子墨水屏样式
            style = f'''
            @namespace epub "http://www.idpf.org/2007/ops";
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: white;
            }}
            div.image-container {{
                width: 100%;
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
                padding: 0;
                page-break-after: always;
            }}
            img {{
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
                margin: 0;
                padding: 0;
            }}
            '''
            
            nav_css = epub.EpubItem(
                uid="style_nav",
                file_name="style/nav.css",
                media_type="text/css",
                content=style
            )
            book.add_item(nav_css)

            # 获取超分辨率后的图片
            final2x_output_dir = os.path.join(new_images_dir, 'outputs')
            if not os.path.exists(final2x_output_dir):
                raise FileNotFoundError(f"未找到超分辨率图片目录: {final2x_output_dir}")

            # 获取所有超分辨率后的图片并排序
            image_files = []
            for file in os.listdir(final2x_output_dir):
                if 'page_' in file:
                    try:
                        # 提取页码，移除前缀（如4x-）
                        page_str = file.split('page_')[1].split('.')[0]
                        # 确保只获取数字部分
                        page_num = int(''.join(filter(str.isdigit, page_str)))
                        image_files.append((page_num, file))
                    except Exception as e:
                        print(f"警告: 无法解析文件名 {file}: {str(e)}")
                        continue

            # 按页码排序
            image_files.sort(key=lambda x: x[0])
            
            print("\n图片处理顺序:")
            for page_num, file in image_files:
                print(f"页码 {page_num:04d}: {file}")

            # 创建章节和图片
            chapters = []
            spine = ['nav']

            # 处理封面
            cover_found = False
            for item in original_book.get_items():
                if item.get_type() == ebooklib.ITEM_COVER or \
                   (item.get_type() == ebooklib.ITEM_IMAGE and ('cover' in item.id.lower() or 'cover' in item.file_name.lower())):
                    try:
                        # 查找对应的超分辨率封面图片
                        cover_image_path = None
                        for page_num, file in image_files:
                            if page_num == 1:  # 假设第一张图片是封面
                                cover_image_path = os.path.join(final2x_output_dir, file)
                                break

                        if cover_image_path and os.path.exists(cover_image_path):
                            print("处理封面图片...")
                            img = Image.open(cover_image_path)
                            width, height = img.size
                            new_width, new_height = self.calculate_optimal_size(width, height, target_long_edge)
                            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            
                            # 保存封面图片
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format='PNG', quality=95, optimize=True)
                            img_data = img_byte_arr.getvalue()
                            
                            # 创建封面项
                            cover_image = epub.EpubImage()
                            cover_image.id = 'cover-image'
                            cover_image.file_name = 'images/cover.png'
                            cover_image.media_type = 'image/png'
                            cover_image.content = img_data
                            book.add_item(cover_image)
                            
                            # 设置封面
                            book.set_cover('images/cover.png', img_data)
                            
                            # 创建封面页章节
                            cover_chapter_content = f'''
                            <html>
                                <head>
                                    <title>封面</title>
                                    <link rel="stylesheet" type="text/css" href="style/nav.css" />
                                </head>
                                <body>
                                    <div class="image-container">
                                        <img src="images/cover.png" alt="封面" 
                                             width="{new_width}" height="{new_height}" />
                                    </div>
                                </body>
                            </html>
                            '''
                            
                            cover_chapter = epub.EpubHtml(
                                title='封面',
                                file_name='cover.xhtml',
                                content=cover_chapter_content,
                                lang='zh'
                            )
                            book.add_item(cover_chapter)
                            chapters.append(cover_chapter)
                            spine.append(cover_chapter)
                            
                            cover_found = True
                            print("封面图片和封面页已添加")
                            break
                    except Exception as e:
                        print(f"处理封面时出错: {str(e)}")
                        continue

            if not cover_found:
                print("警告: 未找到封面图片")
            
            # 准备并行处理的参数
            process_args = []
            actual_page_num = 1
            for page_num, image_file in image_files:
                # 如果是封面图片且已经处理过，则跳过
                if page_num == 1 and cover_found:
                    continue
                    
                image_path = os.path.join(final2x_output_dir, f"4x-page_{page_num:04d}.png")
                if not os.path.exists(image_path):
                    print(f"警告: 找不到文件 {image_path}")
                    continue
                    
                process_args.append((image_path, actual_page_num, target_long_edge))
                actual_page_num += 1

            # 并行处理图片
            print(f"\n开始并行处理图片 (32线程)...")
            processed_images = {}
            with ThreadPoolExecutor(max_workers=32) as executor:
                future_to_page = {executor.submit(self.process_image_for_eink, args): args[1] 
                                for args in process_args}
                
                for future in tqdm(as_completed(future_to_page), total=len(process_args), desc="处理图片"):
                    result = future.result()
                    if result['success']:
                        processed_images[result['page_num']] = result

            # 按页码顺序添加处理后的图片到EPUB
            for page_num in sorted(processed_images.keys()):
                result = processed_images[page_num]
                
                # 添加图片
                image_item = epub.EpubItem(
                    uid=f'image_{page_num}',
                    file_name=f'images/image_{page_num}.png',
                    media_type='image/png',
                    content=result['data']
                )
                book.add_item(image_item)

                # 创建包含图片的章节
                chapter_content = f'''
                <html>
                    <head>
                        <link rel="stylesheet" type="text/css" href="style/nav.css" />
                    </head>
                    <body>
                        <div class="image-container">
                            <img src="images/image_{page_num}.png" alt="第{page_num}页" 
                                 width="{result['width']}" height="{result['height']}" />
                        </div>
                    </body>
                </html>
                '''
                
                chapter = epub.EpubHtml(
                    title=f'第{page_num}页',
                    file_name=f'page_{page_num}.xhtml',
                    content=chapter_content,
                    lang='zh'
                )
                book.add_item(chapter)
                chapters.append(chapter)
                spine.append(chapter)

            # 添加导航
            book.toc = [(epub.Section('目录'), chapters)]
            book.spine = spine
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            # 生成EPUB
            epub.write_epub(output_path, book, {})
            print(f"\nEPUB创建完成: {output_path}")
            print(f"总页数: {len(chapters)}")
            
            return True
            
        except Exception as e:
            print(f"\n创建EPUB时出错: {str(e)}")
            import traceback
            print("\n详细错误信息:")
            print(traceback.format_exc())
            return False

    def calculate_optimal_size(self, img_width, img_height, target_long_edge=1872):
        """
        计算最佳显示尺寸，长边统一适配1872
        :param img_width: 原始宽度
        :param img_height: 原始高度
        :param target_long_edge: 目标长边尺寸，默认1872
        """
        # 确定长边
        long_edge = max(img_width, img_height)
        # 计算缩放比例
        scale = target_long_edge / long_edge
        
        # 按比例计算新尺寸
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        return new_width, new_height

    def check_processed_files(self, input_dir, output_dir):
        """
        检查目标文件夹中是否存在已处理的文件
        :param input_dir: 输入文件夹路径
        :param output_dir: 输出文件夹路径
        :return: 已处理文件列表, 未处理文件列表
        """
        processed_files = []
        unprocessed_files = []
        
        # 获取所有输入epub文件
        input_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.epub')]
        
        # 获取所有输出文件
        output_files = set(f for f in os.listdir(output_dir) if f.lower().endswith('.epub')) if os.path.exists(output_dir) else set()
        
        # 检查每个输入文件
        for input_file in input_files:
            if input_file in output_files:
                # 检查输出文件是否完整（大小大于0）
                output_path = os.path.join(output_dir, input_file)
                if os.path.getsize(output_path) > 0:
                    processed_files.append(input_file)
                    continue
            unprocessed_files.append(input_file)
        
        return processed_files, unprocessed_files

def main():
    """
    批量处理文件夹中的所有epub文件
    1. 提取所有图片
    2. 使用Final2X超分辨率图片（4倍放大，使用RealESRGAN x4plus anime模型）
    3. 重新打包成新的EPUB
    """
    # 获取输入文件夹路径
    input_dir = r"D:\电子书\[Kmoe][epub][迷宮飯]打包"
    
    if not os.path.exists(input_dir):
        print(f"错误: 文件夹不存在: {input_dir}")
        return
        
    # 创建输出文件夹
    output_dir = input_dir + "_upscale"
    os.makedirs(output_dir, exist_ok=True)

    # 设置超分辨率参数
    model_name = 'RealESRGAN_RealESRGAN_x4plus_anime_6B_4x.pth'
    scale = 4

    # 检查已处理和未处理的文件
    extractor = ImageExtractor()
    processed_files, unprocessed_files = extractor.check_processed_files(input_dir, output_dir)
    
    if processed_files:
        print(f"\n已处理的文件 ({len(processed_files)}):")
        for file in processed_files:
            print(f"- {file}")
    
    if not unprocessed_files:
        print("\n所有文件都已处理完成!")
        return
        
    print(f"\n待处理的文件 ({len(unprocessed_files)}):")
    for file in unprocessed_files:
        print(f"- {file}")
    
    print(f"\n超分辨率设置:")
    print(f"- 使用模型: {model_name}")
    print(f"- 放大倍数: {scale}x")
    
    # 处理每个未处理的epub文件
    for epub_file in unprocessed_files:
        input_file = os.path.join(input_dir, epub_file)
        print(f"\n{'='*20} 开始处理 {epub_file} {'='*20}")
        
        try:
            # 1. 提取图片
            print("\n第1步: 提取图片")
            images, project_dir = extractor.extract_images(input_file)
            
            if not images:
                print("没有找到可处理的图片!")
                continue
                
            print(f"找到 {len(images)} 张图片")
            
            # 2. 使用Final2X超分辨率图片
            print("\n第2步: 超分辨率图片")
            upscaled_dir = os.path.join(project_dir, "upscaled")
            os.makedirs(upscaled_dir, exist_ok=True)
            
            success = extractor.upscale_images(
                images, 
                upscaled_dir, 
                model_name=model_name,
                scale=scale
            )
            if not success:
                print("超分辨率过程失败!")
                continue
                
            # 3. 重新打包
            print("\n第3步: 重新打包EPUB")
            output_file = os.path.join(output_dir, epub_file)
            
            print(f"打包设置:")
            print(f"- 原始文件: {input_file}")
            print(f"- 超分辨率图片: {upscaled_dir}")
            print(f"- 输出文件: {output_file}")
            print(f"- 适配电子墨水屏: 是 (1872×1404)")
            
            success = extractor.process_book(
                input_file, 
                output_file, 
                upscaled_dir,
                resize_to_original=False,
                create_new=False,
                create_eink=True
            )
            
            if success:
                print(f"\n{'='*20} 处理完成 {'='*20}")
                print(f"输出文件: {output_file}")
                print("\n文件大小对比:")
                original_size = os.path.getsize(input_file) / (1024*1024)
                new_size = os.path.getsize(output_file) / (1024*1024)
                print(f"- 原始文件: {original_size:.2f} MB")
                print(f"- 处理后文件: {new_size:.2f} MB")
                print(f"- 增大比例: {(new_size/original_size - 1)*100:.1f}%")
            else:
                print("\n处理失败!")
                
        except Exception as e:
            print(f"\n处理过程出错: {str(e)}")
            import traceback
            print("\n详细错误信息:")
            print(traceback.format_exc())
        finally:
            extractor.cleanup()
            print("\n临时文件已清理")
            
    print(f"\n所有文件处理完成!")
    print(f"输出文件夹: {output_dir}")

if __name__ == "__main__":
    main()