import os
import json
import shutil  # 🎯 確実にシステム全体で有効化
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from tkcalendar import DateEntry
from datetime import datetime
from typing import Dict, Any

# models フォルダから各モデルをインポート
from models.master_model import MasterModel
from models.repair_model import RepairModel

# ==================================================
# 1. NullableDateEntry (日付拡張ウィジェット)
# ==================================================
class NullableDateEntry(DateEntry):
    def __init__(self, master=None, **kwargs):
        self._date_pattern = kwargs.get("date_pattern", "yyyy-mm-dd")
        self._default_fg = kwargs.get("foreground", "black")
        super().__init__(master, **kwargs)
        self._var = self["textvariable"] or tk.StringVar()
        self.configure(textvariable=self._var)
        self._var.trace_add("write", self._on_write)

    def _on_write(self, *args):
        value = self._var.get().strip()
        if not value:
            self.configure(foreground=self._default_fg)
            return
        try:
            datetime.strptime(value, self._date_pattern.replace("yyyy", "%Y").replace("mm", "%m").replace("dd", "%d"))
            self.configure(foreground=self._default_fg)
        except ValueError:
            self.configure(foreground="red")

    def get(self):
        value = super().get().strip()
        return "" if not value else value

    def set_date(self, value):
        if not value:
            self.delete(0, tk.END)
        else:
            super().set_date(value)


# ==================================================
# 2. RepairInfoWindow (履歴一覧画面)
# ==================================================
class RepairInfoWindow(tk.Toplevel):
    """器材情報と修理履歴を管理するウィンドウクラス。"""
    DB_NAME = RepairModel.DB_PATH if hasattr(RepairModel, "DB_PATH") else "equipment_management.db"

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
        super().__init__(parent)
        self.equipment_db_id = None
        self.equipment_code = equipment_code
        self.equipment_data: Dict[str, Any] = {}
        self.input_vars: Dict[str, tk.StringVar] = {}
        self.repair_tree: ttk.Treeview = None

        self.title("器材情報（参照）")
        self.geometry("1500x500")
        self.transient(parent)
        self.grab_set()

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
            anchor = "center"
            if col_id in ("details", "remarks"):
                anchor = "w"
            self.repair_tree.column(col_id, width=config["width"], anchor=anchor, stretch=False)

        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.repair_tree.yview)
        self.repair_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.repair_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.repair_tree.bind("<Double-Button-1>", lambda e: self._open_edit_repair())

    def _load_and_display_data(self):
        try:
            data = RepairModel.fetch_equipment_detail(self.equipment_code)
        except Exception as e:
            messagebox.showerror("システムエラー", f"器材情報の取得に失敗しました:\n{e}")
            self.destroy()
            return
        if not data:
            messagebox.showerror("データエラー", f"器材コード = {self.equipment_code} のデータが見つালীません。")
            self.destroy()
            return
        self.equipment_db_id = data["id"]
        self.equipment_data = data
        self._update_form()
        self.refresh_repair_history()

    def _update_form(self):
        for key, var in self.input_vars.items():
            var.set(self.equipment_data.get(key, ""))

    def refresh_repair_history(self):
        for item in self.repair_tree.get_children():
            self.repair_tree.delete(item)
        try:
            repairs = RepairModel.fetch_history_by_code(self.equipment_code)
            for row in repairs:
                self.repair_tree.insert("", tk.END, iid=str(row[0]), values=row[1:])
        except Exception as e:
            messagebox.showerror("読込エラー", f"修理履歴の取得中にエラーが発生しました:\n{e}")

    def _open_add_repair(self):
        if not getattr(self, "equipment_code", None):
            messagebox.showwarning("注意", "器材が選択されていません。")
            return
        EditRepairWindow(self, self.DB_NAME, self.equipment_code, None, self.refresh_repair_history)

    def _open_edit_repair(self):
        selected_ids = self.repair_tree.selection()
        if not selected_ids:
            messagebox.showwarning("選択なし", "修正する修理情報を選択してください。")
            return
        repair_id = int(selected_ids[0])
        EditRepairWindow(self, self.DB_NAME, self.equipment_code, repair_id, self.refresh_repair_history)


# ==================================================
# 3. EditRepairWindow (詳細編集・登録用ポップアップ)
# ==================================================
class EditRepairWindow(tk.Toplevel):
    FIELD_LABELS = ["状態", "依頼日", "完了日", "対応", "業者", "技術者", "詳細", "備考"]

    def __init__(self, parent, db_name, equipment_code=None, repair_id=None, refresh_callback=None):
        super().__init__(parent)
        self.title("修理情報 編集ウィンドウ")
        self.geometry("650x600")
        self.db_name = db_name
        self.equipment_code = equipment_code
        self.repair_id = repair_id
        self.refresh_callback = refresh_callback
        self.entries = {}
        self.grab_set()

        self.statuses = MasterModel.get_kv_lookup("repair_statuse_master")
        self.types = MasterModel.get_kv_lookup("repair_type_master")
        self.vendors = MasterModel.get_kv_lookup("celler_master")

        self._create_widgets()

        if self.repair_id:
            self.load_repair_data(self.repair_id)
            self.load_pdf_list()
        else:
            self.set_widget_value(self.entries["依頼日"], datetime.now().strftime("%Y-%m-%d"))

    def get_widget_value(self, widget):
        if isinstance(widget, ttk.Combobox): return widget.get().strip()
        elif isinstance(widget, tk.Text): return widget.get("1.0", "end-1c").strip()
        elif isinstance(widget, (tk.Entry, NullableDateEntry, DateEntry)): return widget.get().strip()
        return ""

    def set_widget_value(self, widget, value):
        if isinstance(widget, (DateEntry, NullableDateEntry)):
            try:
                if value: widget.set_date(value)
                else: widget.delete(0, tk.END)
            except:
                try: widget.delete(0, tk.END)
                except: pass
        elif isinstance(widget, ttk.Combobox): widget.set(value)
        elif isinstance(widget, tk.Text):
            widget.delete("1.0", tk.END)
            widget.insert("1.0", value)
        else:
            widget.delete(0, tk.END)
            widget.insert(0, value)

    def _create_widgets(self):
        frame_top = tk.Frame(self)
        frame_top.pack(pady=10)
        for i, label in enumerate(self.FIELD_LABELS):
            tk.Label(frame_top, text=label).grid(row=i, column=0, padx=5, pady=3, sticky="e")
            if "日" in label: entry = NullableDateEntry(frame_top, date_pattern="yyyy-mm-dd", width=38)
            elif label == "対応": entry = ttk.Combobox(frame_top, values=list(self.types.values()), state="readonly", width=37)
            elif label == "状態": entry = ttk.Combobox(frame_top, values=list(self.statuses.values()), state="readonly", width=37)
            elif label == "業者": entry = ttk.Combobox(frame_top, values=list(self.vendors.values()), state="readonly", width=37)
            elif label in ("詳細", "備考"): entry = tk.Text(frame_top, width=40, height=3)
            else: entry = tk.Entry(frame_top, width=40)
            entry.grid(row=i, column=1, padx=5, pady=3, sticky="w")
            self.entries[label] = entry

        self._create_buttons()
        frame_pdf = tk.LabelFrame(self, text="添付PDF一覧")
        frame_pdf.pack(fill="both", expand=True, padx=10, pady=10)
        self.pdf_listbox = tk.Listbox(frame_pdf, height=6)
        self.pdf_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.pdf_listbox.bind("<Double-Button-1>", self.open_selected_pdf)

    def _create_buttons(self):
        frame_btn = tk.Frame(self)
        frame_btn.pack(pady=10)
        tk.Button(frame_btn, text="保存", width=12, command=self.save_changes).pack(side="left", padx=10)
        tk.Button(frame_btn, text="PDF添付", width=12, command=self.attach_pdf).pack(side="left", padx=10)
        tk.Button(frame_btn, text="保存せずに戻る", width=15, command=self.destroy).pack(side="left", padx=10)

    def load_repair_data(self, repair_id):
        try:
            data = RepairModel.fetch_by_id(repair_id)
            if not data:
                messagebox.showerror("エラー", "修理情報が見つかりません。")
                return
            keys = ["状態", "依頼日", "完了日", "対応", "業者", "技術者", "詳細", "備考"]
            for key, value in zip(keys, data):
                self.set_widget_value(self.entries[key], self.get_name_from_id(value, key))
        except Exception as e:
            messagebox.showerror("読込エラー", f"修理情報読込中にエラーが発生しました:\n{e}")

    def execute_db_save(self):
        new_values = {k: self.get_widget_value(w) for k, w in self.entries.items()}
        repairstatus_id = self.get_id_from_name(new_values["状態"], self.statuses)
        repairtype_id = self.get_id_from_name(new_values["対応"], self.types)
        vendor_id = self.get_id_from_name(new_values["業者"], self.vendors)

        if self.entries["依頼日"].cget("foreground") == "red" or not new_values["依頼日"]:
            messagebox.showwarning("入力チェック", "「依頼日」が正しく入力されていません。")
            raise ValueError("不正な日付")
        if self.entries["完了日"].get() and self.entries["完了日"].cget("foreground") == "red":
            messagebox.showwarning("入力チェック", "「完了日」の形式が正しくありません。")
            raise ValueError("不正な日付")
        if not (repairstatus_id and repairtype_id and vendor_id):
            messagebox.showwarning("入力チェック", "「状態」「対応」「業者」は必須項目です。")
            raise ValueError("必須項目未入力")

        import sqlite3
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            if self.repair_id:
                cursor.execute("""
                    UPDATE repair SET repairstatuses=?, request_date=?, completion_date=?, repairtype=?, vendor=?, technician=?, details=?, remarks=? WHERE id=?
                """, (repairstatus_id, new_values["依頼日"], new_values["完了日"] if new_values["完了日"] else None, repairtype_id, vendor_id, new_values["技術者"] if new_values["技術者"] else None, new_values["詳細"] if new_values["詳細"] else None, new_values["備考"] if new_values["備考"] else None, self.repair_id))
            else:
                cursor.execute("""
                    INSERT INTO repair (equipment_code, repairstatuses, request_date, completion_date, repairtype, vendor, technician, details, remarks) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (self.equipment_code, repairstatus_id, new_values["依頼日"], new_values["完了日"] if new_values["完了日"] else None, repairtype_id, vendor_id, new_values["技術者"] if new_values["技術者"] else None, new_values["詳細"] if new_values["詳細"] else None, new_values["備考"] if new_values["備考"] else None))
                self.repair_id = cursor.lastrowid
            conn.commit()

    def save_changes(self):
        try:
            self.execute_db_save()
            messagebox.showinfo("保存完了", "修理情報を保存しました。")
            if self.refresh_callback: self.refresh_callback()
            self.destroy()
        except ValueError: pass
        except Exception as e: messagebox.showerror("保存エラー", f"修理情報保存中にエラーが発生しました:\n{e}")

    def save_changes_without_close(self):
        self.execute_db_save()
        if self.refresh_callback: self.refresh_callback()

    def attach_pdf(self):
        """
        修理情報に対してPDFファイルを安全に添付するメソッド（絶対パス・エラー自動回避版）
        """
        # 🎯【超重要】どこから起動されても絶対にエラーにしないための強制インポート＆パス補正
        import os
        import sys
        import shutil
        import traceback

        # プロジェクトルート（C:\equipment_management）を検索パスに強制追加
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        try:
            # 1. 画面の入力内容を一時保存（新規登録時はここでDBに書き込まれIDが発番される）
            self.save_changes_without_close()
        except ValueError:
            return  # 入力チェックエラー（日付不正など）の場合は処理を中断
        except Exception as e:
            error_details = traceback.format_exc()
            messagebox.showerror("保存エラー", f"PDFを添付する前の、修理情報の保存中にエラーが発生しました:\n\n{error_details}")
            return

        # 2. 最新の repair_id がクラス変数に保持されているか厳重チェック
        current_repair_id = getattr(self, "repair_id", None)
        if not current_repair_id:
            messagebox.showwarning("注意", "修理情報の保存に失敗したか、修理IDが取得できないためPDFを添付できません。")
            return

        # 3. ユーザーに添付したいPDFファイルを選択させる
        file_path = filedialog.askopenfilename(title="PDFを選択", filetypes=[("PDFファイル", "*.pdf")])
        if not file_path:
            return  # キャンセルされた場合は終了
            
        # 4. 保存する新しいファイル名を入力させる
        default_name = os.path.basename(file_path)
        new_name = simpledialog.askstring(
            "ファイル名入力",
            "保存するPDFファイル名を入力してください（拡張子 .pdf は自動で付きます）:",
            initialvalue=os.path.splitext(default_name)[0],
            parent=self
        )
        if not new_name:
            return  # キャンセルされた場合は終了

        # 拡張子の自動補正
        if not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"

        # 5. コピー処理の実行（ここからファイル操作）
        try:
            # 🎯 保存先フォルダを「C:\equipment_management\attached_pdfs\修理ID」に絶対パスで完全固定
            # viewsフォルダの1つ上の階層（プロジェクトルート）を確実に取得
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            save_dir = os.path.join(base_dir, "attached_pdfs", str(current_repair_id))
            
            # フォルダがなければ自動作成する（attached_pdfs や 修理ID フォルダを自動で作る）
            os.makedirs(save_dir, exist_ok=True)
            
            # 最終的なコピー先フルパスを構築
            save_path = os.path.join(save_dir, new_name)
            
            # 🎯 ファイルのコピーを実行
            shutil.copy(file_path, save_path)

            # 6. 成功時の画面更新処理
            messagebox.showinfo("完了", f"PDFを正常に添付しました。\n\n保存先:\n{save_path}")
            self.load_pdf_list()
            self.load_repair_data(current_repair_id)
            
            # ウィンドウが後ろに隠れないように最前面へ引き揚げる
            self.lift()
            self.focus_force()

        except Exception as e:
            # 🎯 万が一これでも失敗した場合は、裏で起きた本物の原因（ログ）をダイアログに表示する
            detailed_log = traceback.format_exc()
            messagebox.showerror(
                "添付エラー", 
                f"PDFファイルのコピー中にエラーが発生しました。\n"
                f"フォルダのアクセス権限やファイルがロックされていないか確認してください。\n\n"
                f"【エラー詳細ログ】:\n{detailed_log}"
            )

    def load_pdf_list(self):
        self.pdf_listbox.delete(0, tk.END)
        pdf_dir = os.path.join("attached_pdfs", str(self.repair_id))
        if os.path.exists(pdf_dir):
            for pdf in [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]:
                self.pdf_listbox.insert(tk.END, pdf)

    def open_selected_pdf(self, event=None):
        selection = self.pdf_listbox.curselection()
        if not selection: return
        pdf_path = os.path.join("attached_pdfs", str(self.repair_id), self.pdf_listbox.get(selection[0]))
        try: os.startfile(pdf_path)
        except Exception as e: messagebox.showerror("エラー", f"PDFを開けませんでした:\n{e}")

    def get_name_from_id(self, id_value, key):
        mapping = {"状態": self.statuses, "対応": self.types, "業者": self.vendors}
        return mapping.get(key, {}).get(id_value, id_value or "")

    def get_id_from_name(self, name, mapping):
        for id_, nm in mapping.items():
            if nm == name: return id_
        return None