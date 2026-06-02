import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

def main():
    # 1. 実行している main.py の場所を正確にインポートパス（探索ルート）に登録する
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    try:
        # パスを通した後に、満を持してメイン画面をインポートする
        from views.main_window import EquipmentManagerMainWindow
        
        root = tk.Tk()
        
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        app = EquipmentManagerMainWindow(root)
        root.mainloop()

    except ModuleNotFoundError as e:
        # ファイルの配置やインポート文の間違いをポップアップで教えてくれるようにする
        error_msg = f"ファイルの読み込みに失敗しました。\n配置またはインポート名が間違っている可能性があります。\n\n詳細エラー:\n{e}"
        print(error_msg)
        # 画面が立ち上がらなくても警告メッセージだけは表示させる
        root_err = tk.Tk()
        root_err.withdraw()
        messagebox.showerror("起動エラー (ModuleNotFound)", error_msg)
    except Exception as e:
        error_msg = f"予期せぬエラーが発生しました:\n{e}"
        print(error_msg)
        root_err = tk.Tk()
        root_err.withdraw()
        messagebox.showerror("起動エラー", error_msg)

if __name__ == "__main__":
    main()