import sqlite3
import json
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from models.master_data_fetcher import MasterDataFetcher
from models.new_equipment_number import EquipmentManager

class NewEquipmentWindow(tk.Toplevel):
    """新規器材を登録するためのポップアップウィンドウクラス。"""
    
    def __init__(self, parent, db_name="equipment_management.db", refresh_callback=None):
        super().__init__(parent)
        self.db_name = db_name
        self.refresh_callback = refresh_callback
        
        self.title("新規器材登録")
        self.geometry("420x550")
        
        # 親画面を操作できないようにロック（モーダル化）
        self.transient(parent)
        self.grab_set()

        # マスタデータと管理クラスの初期化
        self.fetcher = MasterDataFetcher(self.db_name)
        self.manager = EquipmentManager()
        
        # 各マスタからデータ取得
        self.categories = self.fetcher.fetch_all("categorie_master")
        self.statuses = self.fetcher.fetch_all("statuse_master")
        self.departments = self.fetcher.fetch_all("department_master")
        self.rooms = self.fetcher.fetch_all("room_master")
        self.manufacturers = self.fetcher.fetch_all("manufacturer_master")
        self.cellers = self.fetcher.fetch_all("celler_master")

        # 自動生成された新しい器材番号を取得
        self.equipment_code = self.manager.get_next_equipment_code()

        self.input_vars = {}
        self._create_widgets()

    def _get_id_from_name(self, name, data_list):
        """選択した名前に対応するIDを取得"""
        for item_id, item_name in data_list:
            if item_name == name:
                return item_id
        return None

    def _create_widgets(self):
        """画面ウィジェットの配置とスタイル設定"""
        
        # 🎨 コンボボックスが初回から「白背景・黒文字」になるように共通ルールをマッピング
        style = ttk.Style()
        style.theme_use('clam')  # 描画エンジンを統一してキャッシュバグを回避
        style.map('TCombobox',
            fieldbackground=[('readonly', 'white')],
            foreground=[('readonly', 'black')]
        )
        style.configure('TCombobox', fieldbackground='white', background='white')

        # 1. 器材番号の表示エリア
        tk.Label(self, text="器材番号").grid(row=0, column=0, padx=15, pady=10, sticky="e")
        tk.Label(self, text=self.equipment_code, fg="blue", font=("Arial", 12, "bold")).grid(row=0, column=1, padx=15, pady=10, sticky="w")

        # 入力項目の定義
        labels = ["カテゴリ名", "器材名", "状態", "部門", "部屋", "製造元", "販売元", "購入日", "備考"]
        keys = ["categorie_name", "name", "statuse_name", "department_name", "room_name", "manufacturer_name", "celler_name", "purchase_date", "remarks"]

        # 2. 各種入力フィールドの動的生成
        for i, (label, key) in enumerate(zip(labels, keys)):
            tk.Label(self, text=label).grid(row=i+1, column=0, padx=15, pady=6, sticky="e")
            
            var = tk.StringVar()
            self.input_vars[key] = var
            
            if key in ["categorie_name", "statuse_name", "department_name", "room_name", "manufacturer_name", "celler_name"]:
                # 対応するマスタデータリストをクラス内から取得
                prefix = key.split("_", 1)[0]
                master_list = getattr(self, prefix + "s", [])
                combo_values = [name for _, name in master_list]
                
                # 🎯 最初は "normal" で作成して強制的に白背景で描画させる
                entry = ttk.Combobox(self, textvariable=var, values=combo_values, state="normal", width=25)
                # 🎯 画面表示の直後（100ミリ秒後）に、自動で "readonly"（手入力不可）にロックする
                self.after(100, lambda c=entry: c.configure(state="readonly"))
                
            elif key == "purchase_date":
                entry = DateEntry(self, textvariable=var, date_pattern='yyyy-mm-dd', width=24)
            else:
                entry = tk.Entry(self, textvariable=var, width=27)
                
            entry.grid(row=i+1, column=1, padx=15, pady=6, sticky="w")

        # 3. ボタンエリア
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=len(labels)+1, column=0, columnspan=2, pady=25)

        tk.Button(btn_frame, text="保存", width=12, bg="#2E7D32", fg="white", 
                  activebackground="#1B5E20", activeforeground="white",
                  command=self._add_equipment).pack(side=tk.LEFT, padx=15)
                  
        tk.Button(btn_frame, text="キャンセル", width=12, command=self.destroy).pack(side=tk.LEFT, padx=15)

    def _add_equipment(self):
        """新規器材をデータベースに登録"""
        new_data = {key: var.get().strip() for key, var in self.input_vars.items()}
        new_data["equipment_code"] = self.equipment_code

        # 必須入力チェック（例としてカテゴリ、器材名、状態を必須にしています）
        if not new_data["categorie_name"] or not new_data["name"] or not new_data["statuse_name"]:
            messagebox.showwarning("入力チェック", "「カテゴリ名」「器材名」「状態」は必須入力項目です。")
            return

        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # 各名前に対応するマスタIDを取得
            categorie_id = self._get_id_from_name(new_data["categorie_name"], self.categories)
            statuse_id = self._get_id_from_name(new_data["statuse_name"], self.statuses)
            department_id = self._get_id_from_name(new_data["department_name"], self.departments)
            room_id = self._get_id_from_name(new_data["room_name"], self.rooms)
            manufacturer_id = self._get_id_from_name(new_data["manufacturer_name"], self.manufacturers)
            celler_id = self._get_id_from_name(new_data["celler_name"], self.cellers)

            query = """
            INSERT INTO equipment (equipment_code, categorie_id, name, statuse_id, department_id, room_id, manufacturer_id, celler_id, purchase_date, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """
            cursor.execute(query, (
                new_data["equipment_code"],
                categorie_id,
                new_data["name"],
                statuse_id,
                department_id,
                room_id,
                manufacturer_id,
                celler_id,
                new_data["purchase_date"],
                new_data["remarks"] if new_data["remarks"] else None
            ))
            conn.commit()
            messagebox.showinfo("成功", "新しい器材が追加されました。")
            
            # 🎯 保存成功時、メイン画面の一覧を自動で再検索・リフレッシュする
            if self.refresh_callback:
                self.refresh_callback()
                
            self.destroy()  # 画面を閉じる

        except sqlite3.Error as e:
            messagebox.showerror("データベースエラー", f"登録に失敗しました:\n{e}")
        finally:
            if conn:
                conn.close()

# =====================================================================
# 💡 メイン画面から呼び出す際の実装イメージ
# =====================================================================
# メイン画面（MainWindow）に「新規登録」ボタンを作り、以下のように呼び出します。
# 
# def open_new_equipment_window(self):
#     # self.search_equipments はメイン画面の一覧を再描画するメソッド
#     NewEquipmentWindow(self.root, db_name="equipment_management.db", refresh_callback=self.search_equipments)
# =====================================================================

if __name__ == "__main__":
    # 単体テスト用のダミー起動コード
    root = tk.Tk()
    root.withdraw() # 親ウィンドウは隠す
    
    # テスト起動 (DBが存在し、マスタクラスが揃っている必要があります)
    try:
        app = NewEquipmentWindow(root)
        root.mainloop()
    except Exception as e:
        print(f"起動テストエラー (環境依存): {e}")