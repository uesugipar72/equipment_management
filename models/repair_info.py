import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any

# 🎯 作成した Model 層と DBManager から必要なものをインポート
from models.db_manager import DBManager
from models.repair_model import RepairModel
from edit_repair_window import EditRepairWindow

# もし MasterDataFetcher を利用し続ける場合は、既存のパスからインポートしてください
# from cls_master_data_fetcher import MasterDataFetcher


class RepairInfoWindow(tk.Toplevel):
    """
    器材情報と修理履歴を管理するウィンドウクラス。
    メインアプリから Toplevel として呼び出して利用します。
    """

    # 🎯 データベースの絶対パスは DBManager から直接取得する
    DB_NAME = DBManager.DB_PATH

    FORM_CONFIG = [
        ("カテゴリ名", "categorie_name"), ("器材番号", "equipment_code"),
        ("器材名", "name"), ("状態", "status_name"), ("部門", "department_name"),
        ("部屋", "room_name"), ("製造元", "manufacturer_name"), ("販売元", "celler_name"),
        ("備考", "remarks"), ("購入日", "purchase_date"), ("モデル(シリアル)", "model")
    ]

    REPAIR_HISTORY_COLUMNS = {
        "status": {"text": "状態", "width": 80},
        "request_date": {"text": "依頼日", "width": 90},
        "completion_date": {"text": "完了日", "width": 90},
        "repair_type": {"text": "修理種別", "width": 90},
        "vendor": {"text": "業者", "width": 130},
        "technician": {"text": "技術者", "width": 100},
        "details": {"text": "詳細", "width": 300},
        "remarks": {"text": "備考", "width": 200},
    }

    def __init__(self, parent: tk.Widget, equipment_code: str):
        """
        Args:
            parent: 呼び出し元ウィンドウ (通常は root)
            equipment_code: 表示対象の器材ID
        """
        super().__init__(parent)
        self.equipment_db_id = None  # DBの主キー
        self.equipment_code = equipment_code  # 表示用の器材番号

        # 🎯 参照関係の名称変換は RepairModel に一括管理させるため、
        # 　 画面側での個別 lookup 構築処理は不要（RepairModel側で結合して取得するため削除）
        self.equipment_data: Dict[str, Any] = {}
        self.input_vars: Dict[str, tk.StringVar] = {}
        self.repair_tree: ttk.Treeview = None

        self.title("器材情報（参照）")
        self.geometry("1500x500")
        self.transient(parent)     # 親ウィンドウの手前に表示
        self.grab_set()            # モーダル表示    

        self._setup_ui()
        self._load_and_display_data()

    def _setup_ui(self):
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        form_frame = tk.Frame(main_frame)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        repair_frame = tk.Frame(main_frame)
        repair_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._create_form_widgets(form_frame)
        self._create_repair_history_widgets(repair_frame)

    def _create_form_widgets(self, parent: tk.Frame):
        for i, (label, key) in enumerate(self.FORM_CONFIG):
            tk.Label(parent, text=label).grid(row=i, column=0, padx=5, pady=3, sticky="w")
            var = tk.StringVar()
            self.input_vars[key] = var
            tk.Entry(parent, textvariable=var, state="readonly", width=30).grid(
                row=i, column=1, padx=5, pady=3, sticky="we"
            )

        button_frame = tk.Frame(parent)
        button_frame.grid(row=len(self.FORM_CONFIG), column=0, columnspan=2, pady=20)
        tk.Button(button_frame, text="修理情報追加", command=self._open_add_repair).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="修理情報修正", command=self._open_edit_repair).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="閉じる", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _create_repair_history_widgets(self, parent: tk.Frame):
        columns_ids = list(self.REPAIR_HISTORY_COLUMNS.keys())
        self.repair_tree = ttk.Treeview(parent, columns=columns_ids, show='headings')

        for col_id in columns_ids:
            config = self.REPAIR_HISTORY_COLUMNS[col_id]
            self.repair_tree.heading(col_id, text=config["text"])
            self.repair_tree.column(col_id, width=config["width"], anchor="w", stretch=False)
            
            anchor = "center"
            if col_id in ("details", "remarks"):
                anchor = "w"

            self.repair_tree.column(
                col_id,
                width=config["width"],
                anchor=anchor,
                stretch=False
            )

        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.repair_tree.yview)
        self.repair_tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.repair_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _load_and_display_data(self):
        """🎯 Model層(RepairModel)を経由して器材の基本情報を取得"""
        try:
            data = RepairModel.fetch_equipment_detail(self.equipment_code)
        except Exception as e:
            messagebox.showerror("システムエラー", f"器材情報の取得に失敗しました:\n{e}")
            self.destroy()
            return

        if not data:
            messagebox.showerror("データエラー", f"器材コード = {self.equipment_code} のデータが見つかりません。")
            self.destroy()
            return

        self.equipment_db_id = data["id"]  # DB主キーを保持
        self.equipment_data = data

        self._update_form()
        self.refresh_repair_history()

    def _update_form(self):
        for key, var in self.input_vars.items():
            var.set(self.equipment_data.get(key, ""))

    def refresh_repair_history(self):
        """🎯 Model層(RepairModel)を経由して修理履歴を取得し描画"""
        for item in self.repair_tree.get_children():
            self.repair_tree.delete(item)

        try:
            # 🎯 SQLクエリは書かず、Model層のメソッドを呼び出すだけ
            repairs = RepairModel.fetch_history_by_code(self.equipment_code)
            
            for row in repairs:
                # row[0] = id, 以降(values)を TreeView に渡す
                self.repair_tree.insert("", tk.END, iid=str(row[0]), values=row[1:])
        except Exception as e:
            messagebox.showerror("読込エラー", f"修理履歴の取得中にエラーが発生しました:\n{e}")

    def _open_add_repair(self):
        try:
            if not getattr(self, "equipment_code", None):
                messagebox.showwarning("注意", "器材が選択されていません。")
                return

            EditRepairWindow(
                parent=self,
                db_name=self.DB_NAME,
                equipment_code=self.equipment_code,
                repair_id=None,
                refresh_callback=self.refresh_repair_history
            )
        except Exception as e:
            messagebox.showerror("例外発生", f"修理情報追加中にエラーが発生しました:\n{e}")

    def _open_edit_repair(self):
        selected_ids = self.repair_tree.selection()
        if not selected_ids:
            messagebox.showwarning("選択なし", "修正する修理情報を選択してください。")
            return

        repair_id = int(selected_ids[0])
        try:
            EditRepairWindow(
                parent=self,
                db_name=self.DB_NAME,
                equipment_code=self.equipment_code,
                repair_id=repair_id,                
                refresh_callback=self.refresh_repair_history
            )
        except Exception as e:
            messagebox.showerror("例外発生", f"修理情報修正中にエラーが発生しました:\n{e}")