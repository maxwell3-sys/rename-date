# 按文件名批量写入图片拍摄日期

从图片文件名中解析时间，写入 EXIF 拍摄日期（`DateTimeOriginal` 等）。
支持微信导出图片和安卓截图两种常见命名格式，带图形界面，可勾选部分文件处理，处理前自动备份。

## 功能

- 图形界面选择文件夹，无需命令行
- 自动识别文件名中的时间，支持两种格式：
  - **微信导出**：`mmexport<13位毫秒时间戳>.jpg`
  - **安卓截图**：`Screenshot_YYYY-MM-DD-HH-MM-SS-毫秒_xxx.jpg`
- 列出所有可处理图片，默认全选，可手动取消勾选
- 将解析出的时间写入 EXIF 的拍摄日期字段：
  - `DateTimeOriginal`（拍摄日期）
  - `DateTimeDigitized`（数字化日期）
  - `DateTime`（修改日期）
- 处理前自动备份原图到 `backup_exif` 子文件夹
- 支持 JPG / JPEG / TIFF / WebP

## 环境要求

- Python 3.7 及以上
- 依赖库：
  - `pillow`
  - `piexif`

## 安装

```bash
pip install pillow piexif
