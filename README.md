[![English](https://img.shields.io/badge/English-en-blue.svg)](#en) [![中文](https://img.shields.io/badge/中文-zh-red.svg)](#zh)

<a id="zh"></a>
# Comics Upscaler

Comics Upscaler 是一个专门用于优化电子书（EPUB）图片质量的工具。它能够自动提取电子书中的图片，使用AI超分辨率技术提升图片质量，并重新打包成适合电子墨水屏阅读的电子书。

## ✨ 特性

- 🚀 支持EPUB格式的电子书处理
- 🖼️ 使用先进的AI超分辨率技术提升图片质量
- 📱 自动优化图片尺寸，适配电子墨水屏
- 📚 保留原始电子书的元数据和目录结构
- 🛠️ 支持批量处理多个文件
- ⚡ 多进程并行处理，提升处理速度
- 🧹 自动清理临时文件

## 🔧 系统要求

- Windows 10/11 64位
- Python 3.8-3.12
- 内存：建议8GB以上
- 存储空间：建议预留处理文件大小10倍以上的空间
- GPU要求：
  - NVIDIA显卡（推荐）：支持CUDA加速
  - AMD显卡：仅支持在Linux系统下通过ROCm使用
  - Intel显卡：暂不支持GPU加速
- [Final2x-core](https://github.com/Tohrusky/Final2x-core/releases) v3.0.0+ (用于图片超分辨率处理)

## 📦 安装

### 方式一：直接下载（推荐）
1. 从 [Releases](https://github.com/[your-username]/comics-upscaler/releases) 页面下载最新版本的压缩包
2. 解压到任意目录
3. 下载 [Final2x-core](https://github.com/Tohrusky/Final2x-core/releases) 最新版本，解压并放置在程序目录下的 `Final2X` 文件夹中
4. 根据需要修改 `config/settings.yaml` 配置文件（参考下方配置说明）
5. 双击运行 `ComicsUpscaler.exe`

### 方式二：手动安装
1. 克隆仓库：
```bash
git clone https://github.com/[your-username]/comics-upscaler.git
cd comics-upscaler
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 下载并配置Final2x-core：
   - 从[Final2x-core Releases](https://github.com/Tohrusky/Final2x-core/releases)下载最新版本
   - 将项目解压放置在Final2X目录下

## ⚙️ 配置

在`config/settings.yaml`中配置以下参数：

```yaml
# 临时目录
temp_dir: "temp"

# 目录设置
directories:
  # 输入目录路径
  input: "D:/电子书/"
  # 输出目录后缀（将添加到输入目录后）
  output_suffix: "_upscale"

# 超分辨率设置
upscale:
  # 使用的模型名称
  model_name: "RealCUGAN_Conservative_4x.pth"
  # 放大倍数
  scale: 4
  # 目标长边尺寸（适配电子墨水屏）
  target_long_edge: 3744
  # 并行处理的进程数
  num_processes: 4
  # 输出图片格式
  output_format: "JPEG"
  # 输出图片质量 (1-100)
  output_quality: 95

# EPUB设置
epub:
  # 是否调整到原始大小
  resize_to_original: false
  # 是否创建新的EPUB
  create_new: false
  # 是否创建适配电子墨水屏的EPUB
  create_eink: true 
```

### 超分辨率模型说明

- **RealCUGAN-pro**: 适合漫画、插画等内容，对线条和细节的保持较好
- **RealESRGAN**: 适合真实照片，对噪点的处理较好
- **SwinIR**: 新一代通用超分辨率模型，效果优秀但处理速度较慢
- **EDSR**: 经典模型，速度和效果均衡
- **SCUNet**: 适合处理复杂纹理的图像

## 🚀 使用方法

1. 将需要处理的电子书文件放入input目录
2. 运行程序：
```bash
python comics_upscale.py
```
3. 处理后的文件将保存在"input_upscaled"目录中

### 性能调优

- `num_processes`: 建议设置为CPU核心数的一半
- 如果内存充足，可以适当增加并行处理数
- GPU处理时建议将`num_processes`设置为1

## 📝 注意事项

- 处理过程中会占用较多磁盘空间，请确保有足够的存储空间
- 图片处理时间取决于图片数量、尺寸和电脑性能
- 建议先处理单个文件测试效果

## ❓ 常见问题

1. **Q: 处理速度很慢怎么办？**
   - A: 确保使用NVIDIA显卡并启用GPU加速
   - A: 可以尝试使用较轻量级的模型（如EDSR）
   - A: 减小目标分辨率或降低放大倍数

2. **Q: 内存占用过高怎么办？**
   - A: 减少并行处理数量
   - A: 降低处理图片的数量
   - A: 使用GPU处理时设置`num_processes`为1

3. **Q: 支持哪些图片格式？**
   - A: 支持jpg、png、webp等常见格式

4. **Q: 为什么无法使用GPU加速？**
   - A: Windows系统目前仅支持NVIDIA显卡的GPU加速
   - A: AMD显卡仅支持在Linux系统下通过ROCm使用
   - A: Intel显卡暂不支持GPU加速

---

<a id="en"></a>
# Comics Upscaler

Comics Upscaler is a specialized tool for enhancing image quality in electronic books (EPUB). It automatically extracts images from e-books, uses AI super-resolution technology to improve image quality, and repackages them into e-books suitable for e-ink screen reading.

## ✨ Features

- 🚀 Support for EPUB format e-books processing
- 🖼️ Advanced AI super-resolution technology for image quality enhancement
- 📱 Automatic image size optimization for e-ink screens
- 📚 Preserves original e-book metadata and directory structure
- 🛠️ Support for batch processing multiple files
- ⚡ Multi-process parallel processing for improved speed
- 🧹 Automatic cleanup of temporary files

## 🔧 System Requirements

- Windows 10/11 64-bit
- Python 3.8-3.12
- Memory: 8GB or more recommended
- Storage Space: Recommend reserving 10x the size of files being processed
- GPU Requirements:
  - NVIDIA GPU (Recommended): Supports CUDA acceleration
  - AMD GPU: ROCm support on Linux systems only
  - Intel GPU: GPU acceleration not currently supported
- [Final2x-core](https://github.com/Tohrusky/Final2x-core/releases) v3.0.0+ (for image super-resolution processing)

## 📦 Installation

### Method 1: Direct Download (Recommended)
1. Download the latest version from the [Releases](https://github.com/[your-username]/comics-upscaler/releases) page
2. Extract to any directory
3. Download the latest version of [Final2x-core](https://github.com/Tohrusky/Final2x-core/releases), extract and place it in the `Final2X` folder under the program directory
4. Modify the `config/settings.yaml` configuration file as needed (refer to configuration instructions below)
5. Double-click `ComicsUpscaler.exe` to run

### Method 2: Manual Installation
1. Clone the repository:
```bash
git clone https://github.com/[your-username]/comics-upscaler.git
cd comics-upscaler
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Download and configure Final2x-core:
   - Download the latest version from [Final2x-core Releases](https://github.com/Tohrusky/Final2x-core/releases)
   - Extract and place the project in the Final2X directory

## ⚙️ Configuration

Configure the following parameters in `config/settings.yaml`:

```yaml
# Temporary directory
temp_dir: "temp"

# Directory settings
directories:
  # Input directory path
  input: "D:/ebooks/"
  # Output directory suffix (will be added to input directory)
  output_suffix: "_upscale"

# Upscale settings
upscale:
  # Model name to use
  model_name: "RealCUGAN_Conservative_4x.pth"
  # Scale factor
  scale: 4
  # Target long edge size (for e-ink screen compatibility)
  target_long_edge: 3744
  # Number of parallel processes
  num_processes: 4
  # Output image format
  output_format: "JPEG"
  # Output image quality (1-100)
  output_quality: 95

# EPUB settings
epub:
  # Whether to resize to original size
  resize_to_original: false
  # Whether to create new EPUB
  create_new: false
  # Whether to create e-ink optimized EPUB
  create_eink: true 
```

### Super-resolution Model Description

- **RealCUGAN-pro**: Suitable for comics and illustrations, better preservation of lines and details
- **RealESRGAN**: Suitable for real photos, better noise handling
- **SwinIR**: New generation universal super-resolution model, excellent results but slower processing
- **EDSR**: Classic model, balanced speed and effect
- **SCUNet**: Suitable for processing images with complex textures

## 🚀 Usage

1. Place the e-books to be processed in the input directory
2. Run the program:
```bash
python comics_upscale.py
```
3. Processed files will be saved in the "input_upscaled" directory

### Performance Tuning

- `num_processes`: Recommended to set to half of CPU cores
- Increase parallel processing if memory is sufficient
- Set `num_processes` to 1 when using GPU processing

## 📝 Notes

- Processing will occupy significant disk space, ensure sufficient storage
- Image processing time depends on image quantity, size, and computer performance
- Recommended to test with a single file first

## ❓ FAQ

1. **Q: What to do if processing is too slow?**
   - A: Ensure NVIDIA GPU is used with GPU acceleration enabled
   - A: Try using lighter models (like EDSR)
   - A: Reduce target resolution or scale factor

2. **Q: What to do about high memory usage?**
   - A: Reduce number of parallel processes
   - A: Reduce number of images being processed
   - A: Set `num_processes` to 1 when using GPU

3. **Q: What image formats are supported?**
   - A: Supports jpg, png, webp, and other common formats

4. **Q: Why can't I use GPU acceleration?**
   - A: Windows systems currently only support NVIDIA GPU acceleration
   - A: AMD GPUs only supported through ROCm on Linux systems
   - A: Intel GPUs currently do not support GPU acceleration
