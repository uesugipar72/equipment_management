import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import os
import subprocess
import json

# プロジェクトルートからの絶対インポート表記に統一
from models.master_model import MasterModel
from models.equipment_model import EquipmentModel

# 【重要】もし views/repair_window.py がまだ未完成、もしくはエラーがある場合は、
# 一旦ここをコメントアウトして、ダミーの関数で代用します。
try:
    from views.repair_window import RepairInfoWindow
    HAS_REPAIR_WINDOW = True
except Exception as e:
    print(f"[Warning] repair_window の読み込みをスキップしました (後ほど作成します): {e}")
    HAS_REPAIR_WINDOW = False


class EquipmentManagerMainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("器材管理システム (MVC版)")
        self.root.geometry("1400x750")

        # 画面表示用のマスタデータをModelから取得 (IDから名称への変換用ルックアップ)
        self.lookups = {
            "categorie_master": MasterModel.get_kv_lookup("categorie_master"),
            "statuse_master": MasterModel.get_kv_lookup("statuse_master"),
            "department_master": MasterModel.get_kv_lookup("department_master"),
            "room_master": MasterModel.get_kv_lookup("room_master"),
            "manufacturer_master": MasterModel.get_kv_lookup("manufacturer_master"),
            "celler_master": MasterModel.get_kv_lookup("celler_master"),
        }

        self.entries = {}
        self._create_widgets()
        self._create_menus()
        
        # 起動時に全件検索をかけて初期データを表示
        self.search_equipments()

    def _create_widgets(self):
        """画面ウィジェットの配置"""
        frame_search = ttk.LabelFrame(self.root, text="検索条件入力", padding=10)
        frame_search.pack(fill="x", padx=10, pady=5)

        search_fields = [
            ("器材番号", None), ("機器名", None), ("機器名カナ", None),
            ("機器分類", "categorie_master"), ("状態", "statuse_master"),
            ("部門", "department_master"), ("部屋", "room_master"),
            ("製造元", "manufacturer_master"), ("販売元", "celler_master"),
            ("備考", None)
        ]

        for i, (label, master_key) in enumerate(search_fields):
            lbl = ttk.Label(frame_search, text=label)
            lbl.grid(row=i // 4, column=(i % 4) * 2, padx=5, pady=5, sticky="e")

            if master_key:
                combo = ttk.Combobox(frame_search, state="readonly", width=18)
                master_data = MasterModel.fetch_all(master_key)
                combo["values"] = [""] + [row[1] for row in master_data]
                combo.grid(row=i // 4, column=(i % 4) * 2 + 1, padx=5, pady=5, sticky="w")
                combo.set("")
                self.entries[label] = combo
            else:
                entry = ttk.Entry(frame_search, width=20)
                entry.grid(row=i // 4, column=(i % 4) * 2 + 1, padx=5, pady=5, sticky="w")
                self.entries[label] = entry

        row_btn = (len(search_fields) - 1) // 4 + 1
        frame_buttons = ttk.Frame(frame_search)
        frame_buttons.grid(row=row_btn, column=0, columnspan=8, pady=10, sticky="ew")

        btn_search = ttk.Button(frame_buttons, text="検索", command=self.search_equipments)
        btn_search.pack(side="left", padx=5)

        btn_reset = ttk.Button(frame_buttons, text="条件初期化", command=self.reset_conditions)
        btn_reset.pack(side="left", padx=5)

        btn_export = ttk.Button(frame_buttons, text="Excel出力", command=self.export_to_excel)
        btn_export.pack(side="left", padx=5)

        frame_table = ttk.LabelFrame(self.root, text="機器一覧 (ダブルクリックで修理履歴を表示)", padding=10)
        frame_table.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("category", "code", "name", "status", "dept", "room", "maker", "vendor", "remarks", "p_date", "model")
        self.tree = ttk.Treeview(frame_table, columns=columns, show="headings")
        
        headers = {
            "category": "機器分類", "code": "器材番号", "name": "機器名", "status": "状態",
            "dept": "部門", "room": "部屋", "maker": "製造元", "vendor": "販売元",
            "remarks": "備考", "p_date": "購入日", "model": "モデル"
        }
        for col, text in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=100, anchor="center" if "date" in col or "code" in col else "w")

        vsb = ttk.Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame_table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frame_table.grid_rowconfigure(0, weight=100)
        frame_table.grid_columnconfigure(0, weight=100)

        self.tree.bind("<Double-1>", self.open_repair_info)

    def _create_menus(self):
        menubar = tk.Menu(self.root)
        master_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="マスタ管理", menu=master_menu)
        self.root.config(menu=menubar)

    def search_equipments(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        def get_master_id(label, lookup_dict):
            val = self.entries[label].get()
            if not val:
                return None
            for k, v in lookup_dict.items():
                if v == val:
                    return k
            return None

        category_id = get_master_id("機器分類", self.lookups["categorie_master"])
        status_id = get_master_id("状態", self.lookups["statuse_master"])
        department_id = get_master_id("部門", self.lookups["department_master"])
        room_id = get_master_id("部屋", self.lookups["room_master"])
        manufacturer_id = get_master_id("製造元", self.lookups["manufacturer_master"])
        celler_id = get_master_id("販売元", self.lookups["celler_master"])

        records = EquipmentModel.search_equipments(
            equipment_code=self.entries["器材番号"].get().strip(),
            name=self.entries["機器名"].get().strip(),
            name_kana=self.entries["機器名カナ"].get().strip(),
            category_id=category_id,
            statuse_id=status_id,
            department_id=department_id,
            room_id=room_id,
            manufacturer_id=manufacturer_id,
            celler_id=celler_id,
            remarks=self.entries["備考"].get().strip()
        )

        for record in records:
            cat_name = self.lookups["categorie_master"].get(record[4], "不明")
            status_name = self.lookups["statuse_master"].get(record[5], "不明")
            dept_name = self.lookups["department_master"].get(record[6], "不明")
            room_name = self.lookups["room_master"].get(record[7], "不明")
            maker_name = self.lookups["manufacturer_master"].get(record[8], "不明")
            vendor_name = self.lookups["celler_master"].get(record[9], "不明")

            tag = "normal"
            if status_name == "修理中":
                tag = "repairing"
            elif status_name == "廃棄":
                tag = "scrapped"

            self.tree.insert("", tk.END, values=(
                cat_name, record[1], record[2], status_name, dept_name,
                room_name, maker_name, vendor_name, record[10], record[11], record[12]
            ), tags=(tag,))

        self.tree.tag_configure("repairing", background="#ffcccc")
        self.tree.tag_configure("scrapped", background="#d3d3d3")

    def reset_conditions(self):
        for label, widget in self.entries.items():
            if isinstance(widget, ttk.Combobox):
                widget.set("")
            else:
                widget.delete(0, tk.END)
        self.search_equipments()

    def open_repair_info(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        
        row_values = self.tree.item(selected[0], "values")
        equipment_code = row_values[1]

        # repair_window が正しく読み込めている場合のみ呼び出す安全策
        if HAS_REPAIR_WINDOW:
            RepairInfoWindow(self.root, equipment_code)
        else:
            messagebox.showinfo("案内", f"器材番号: {equipment_code}\n修理履歴画面は、次のステップで views/repair_window.py を配置した後に連動します。")

    def export_to_excel(self):
        all_data = [self.tree.item(item, "values") for item in self.tree.get_children()]
        if not all_data:
            messagebox.showinfo("情報", "エクスポートするデータがありません。")
            return
        headers = ["機器分類", "機器コード", "機器名", "状態", "部門", "部屋", "製造元", "販売元", "備考", "購入日", "モデル"]
        try:
            json_data = json.dumps(all_data, ensure_ascii=False)
            json_headers = json.dumps(headers, ensure_ascii=False)
            subprocess.run(["python", "export_to_excel.py", json_data, json_headers], check=True)
            messagebox.showinfo("成功", "Excelファイルを出力しました。")
        except Exception as e:
            messagebox.showerror("エラー", f"Excel出力中にエラーが発生しました:\n{e}")