# -*- coding: utf-8 -*-
"""
从微信导出文件名 mmexport<13位时间戳>.jpg 提取时间，
写入 EXIF 拍摄日期（DateTimeOriginal / DateTimeDigitized / DateTime）。
支持弹窗选文件夹、勾选部分图片处理，处理前自动备份。
"""

import os
import re
import shutil
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import piexif
from PIL import Image

# 支持的图片扩展名
EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp")

# 匹配 mmexport + 13位数字（毫秒时间戳）
PATTERN = re.compile(r"mmexport(\d{13})", re.IGNORECASE)


def ts_to_str(ts_ms: str) -> str:
    """13位毫秒时间戳 -> 'YYYY:MM:DD HH:MM:SS'（本地时区，即北京时间）"""
    sec = int(ts_ms) / 1000.0
    dt = datetime.datetime.fromtimestamp(sec)
    return dt.strftime("%Y:%m:%d %H:%M:%S")


def write_exif_datetime(path: str, dt_str: str):
    """把日期写入图片 EXIF。已有 EXIF 则保留其他字段。"""
    ext = os.path.splitext(path)[1].lower()

    if ext in (".jpg", ".jpeg", ".tif", ".tiff", ".webp"):
        # 用 piexif 处理
        try:
            exif_dict = piexif.load(path)
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        exif_dict.setdefault("0th", {})
        exif_dict.setdefault("Exif", {})

        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = dt_str
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = dt_str
        exif_dict["0th"][piexif.ImageIFD.DateTime] = dt_str

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, path)

    elif ext == ".png":
        # PNG 用 piexif 不方便，这里跳过或可改用 exiftool
        raise NotImplementedError("PNG 的 EXIF 支持较弱，建议用 exiftool 处理")

    elif ext == ".heic":
        raise NotImplementedError("HEIC 需要额外库，建议用 exiftool 处理")

    else:
        raise NotImplementedError(f"不支持的格式: {ext}")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("微信图片拍摄日期批量写入")
        self.root.geometry("640x520")

        self.folder = ""
        self.files = []          # [(fullpath, filename, datetime_str)]
        self.vars = []           # 每个文件的勾选变量

        # 顶部：选文件夹
        top = tk.Frame(root)
        top.pack(fill="x", padx=10, pady=8)

        self.folder_var = tk.StringVar(value="未选择文件夹")
        tk.Label(top, textvariable=self.folder_var, anchor="w").pack(
            side="left", fill="x", expand=True
        )
        tk.Button(top, text="选择文件夹", command=self.choose_folder).pack(side="right")

        # 中间：文件列表（带滚动条）
        mid = tk.Frame(root)
        mid.pack(fill="both", expand=True, padx=10)

        self.canvas = tk.Canvas(mid, borderwidth=0)
        scrollbar = ttk.Scrollbar(mid, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas)

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 底部：全选/全不选 + 执行
        bottom = tk.Frame(root)
        bottom.pack(fill="x", padx=10, pady=8)

        tk.Button(bottom, text="全选", command=lambda: self.set_all(True)).pack(side="left")
        tk.Button(bottom, text="全不选", command=lambda: self.set_all(False)).pack(side="left", padx=6)
        tk.Button(bottom, text="开始处理", command=self.process).pack(side="right")

        self.status = tk.Label(root, text="", anchor="w", fg="blue")
        self.status.pack(fill="x", padx=10, pady=(0, 8))

    def choose_folder(self):
        folder = filedialog.askdirectory(title="选择包含 mmexport 图片的文件夹")
        if not folder:
            return
        self.folder = folder
        self.folder_var.set(folder)
        self.load_files()

    def load_files(self):
        # 清空旧列表
        for w in self.inner.winfo_children():
            w.destroy()
        self.files = []
        self.vars = []

        for name in sorted(os.listdir(self.folder)):
            full = os.path.join(self.folder, name)
            if not os.path.isfile(full):
                continue
            if not name.lower().endswith(EXTS):
                continue
            m = PATTERN.search(name)
            if not m:
                continue
            dt_str = ts_to_str(m.group(1))
            self.files.append((full, name, dt_str))

        if not self.files:
            self.status.config(text="该文件夹下没有找到 mmexport<13位时间戳> 的图片")
            return

        for i, (full, name, dt_str) in enumerate(self.files):
            var = tk.BooleanVar(value=True)
            self.vars.append(var)
            text = f"{name}   →   {dt_str}"
            cb = tk.Checkbutton(self.inner, text=text, variable=var, anchor="w", justify="left")
            cb.pack(fill="x", anchor="w")

        self.status.config(text=f"找到 {len(self.files)} 张可处理图片（默认全选）")

    def set_all(self, value: bool):
        for v in self.vars:
            v.set(value)

    def process(self):
        if not self.files:
            messagebox.showwarning("提示", "没有可处理的图片")
            return

        selected = [f for f, v in zip(self.files, self.vars) if v.get()]
        if not selected:
            messagebox.showwarning("提示", "没有勾选任何图片")
            return

        # 备份目录
        backup_dir = os.path.join(self.folder, "backup_exif")
        os.makedirs(backup_dir, exist_ok=True)

        ok, fail = 0, 0
        errors = []

        for full, name, dt_str in selected:
            try:
                # 备份
                shutil.copy2(full, os.path.join(backup_dir, name))
                # 写入
                write_exif_datetime(full, dt_str)
                ok += 1
            except Exception as e:
                fail += 1
                errors.append(f"{name}: {e}")

        msg = f"处理完成\n成功: {ok}\n失败: {fail}\n原图已备份到: {backup_dir}"
        if errors:
            msg += "\n\n失败详情:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                msg += f"\n... 还有 {len(errors) - 10} 条"
        messagebox.showinfo("结果", msg)
        self.status.config(text=f"完成：成功 {ok}，失败 {fail}")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()