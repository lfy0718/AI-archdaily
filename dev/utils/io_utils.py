import os
import shutil
import sys
import tkinter as tk
from ctypes import POINTER, byref, cast, windll, c_void_p, c_wchar_p
from ctypes.wintypes import SIZE, UINT, HANDLE, HBITMAP
from io import StringIO
from tkinter import filedialog
if sys.platform == "win32":
    import win32ui
from PIL import Image
from comtypes import GUID, IUnknown, COMMETHOD, HRESULT

from dev.global_app_state import g


class OutputCapture:
    def __init__(self, target_list):
        self.output_list = target_list
        self.output_text = StringIO()

    def write(self, text):
        self.output_text.write(text)
        if text.endswith('\n'):  # 以换行符判断一次输出结束
            output = self.output_text.getvalue().strip()
            if output != '':
                self.output_list.append(output)
            self.output_text.truncate(0)
            self.output_text.seek(0)

    def flush(self):
        pass

    def __enter__(self):
        self.old_stdout = sys.stdout
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self.old_stdout


def open_file_dialog(initial_dir=None) -> str:
    if initial_dir is None:
        initial_dir = g.mLastFileDir
    root = tk.Tk()
    root.withdraw()  # 隐藏根窗口
    filepath = filedialog.askopenfilename(initialdir=initial_dir)
    if filepath != '':
        g.mLastFileDir = os.path.dirname(filepath)
    return filepath


def save_file_dialog(initial_dir=None) -> str:
    if initial_dir is None:
        initial_dir = g.mLastFileDir
    root = tk.Tk()
    root.withdraw()  # 隐藏根窗口
    filepath = filedialog.asksaveasfilename(initialdir=initial_dir)
    if filepath != '':
        g.mLastFileDir = os.path.dirname(filepath)
    return filepath


def open_folder_dialog():
    # 创建 Tkinter 根窗口
    root = tk.Tk()
    root.withdraw()  # 隐藏根窗口
    # 弹出文件夹选择框
    selected_folder = filedialog.askdirectory()
    return selected_folder


shell32 = windll.shell32
shell32.SHCreateItemFromParsingName.argtypes = [c_wchar_p, c_void_p, POINTER(GUID), POINTER(HANDLE)]
shell32.SHCreateItemFromParsingName.restype = HRESULT

SIIGBF_RESIZETOFIT = 0


class IShellItemImageFactory(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{bcc18b79-ba16-442f-80c4-8a59c30c463b}')
    _idlflags_ = []


IShellItemImageFactory._methods_ = [
    COMMETHOD([], HRESULT, 'GetImage',
              (['in'], SIZE, 'size'),
              (['in'], UINT, 'flags'),
              (['out'], POINTER(HBITMAP), 'phbm')),
]

LP_IShellItemImageFactory = POINTER(IShellItemImageFactory)


def get_file_thumbnail(filename, icon_size) -> Image:
    # 判断当前操作系统是否为Ubuntu
    if platform.system() != 'win32':
        # 返回一个空的PIL Image对象
        return Image.new('RGB', (icon_size, icon_size), color=(255, 255, 255))
    
    h_siif = HANDLE()
    hr = shell32.SHCreateItemFromParsingName(filename, 0,
                                             byref(IShellItemImageFactory._iid_), byref(h_siif))
    if hr < 0:
        raise Exception(f'SHCreateItemFromParsingName failed: {hr}')
    h_siif = cast(h_siif, LP_IShellItemImageFactory)
    # Raises exception on failure.
    h_bitmap = h_siif.GetImage(SIZE(icon_size, icon_size), SIIGBF_RESIZETOFIT)
    pyCBitmap = win32ui.CreateBitmapFromHandle(h_bitmap)  # Returns a PyCBitmap
    info = pyCBitmap.GetInfo()  # Get a dictionary with info about the image (including width and height)
    data = pyCBitmap.GetBitmapBits(True)
    pil_image = Image.frombuffer('RGB', (info['bmWidth'], info['bmHeight']), data, 'raw', 'BGRX', 0, 1)
    return pil_image


import platform
import subprocess


def find_colmap_executable() -> str:
    if platform.system() == 'Windows':
        try:
            result = subprocess.run(["where", "colmap"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "Cannot found COLMAP"
        except FileNotFoundError:
            return "Error: 'where' command not found"
    elif platform.system() == 'Linux':
        try:
            result = subprocess.run(["which", "colmap"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return result.stderr.strip()
        except FileNotFoundError:
            return "Error: 'which' command not found"
    else:
        return "Error: Unsupported platform"


def clear_folder(folder_path):
    if not os.path.exists(folder_path):
        return
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')


def open_folder_in_explorer(folder_path):
    if folder_path is None:
        return
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        os.startfile(folder_path)


if __name__ == '__main__':
    print(find_colmap_executable())
