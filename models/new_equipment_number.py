import sqlite3
import re

class EquipmentManager:
    """新しい器材番号（equipment_code）を自動生成・管理するクラス"""
    
    def __init__(self, db_path: str = "equipment_management.db"):
        self.db_path = db_path

    def get_next_equipment_code(self, prefix: str = "EQ") -> str:
        """
        現在データベースにある最大の器材番号を調べ、次の番号（例: EQ0005）を自動生成する。
        データが一件もない場合は EQ0001 を返す。
        """
        query = "SELECT equipment_code FROM equipment ORDER BY equipment_code DESC LIMIT 1;"
        
        conn = None
        next_code = f"{prefix}0001"  # デフォルト値
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            
            if row and row[0]:
                last_code = row[0]  # 例: "EQ0023" などが入る
                
                # 文字列の中から数字の部分だけを抽出
                match = re.search(r'\d+', last_code)
                if match:
                    # 数字部分を取り出して+1する
                    current_number = int(match.group())
                    next_number = current_number + 1
                    
                    # 元の数字の桁数（例: 0023なら4桁）に合わせてゼロ埋めする
                    digit_length = len(match.group())
                    next_code = f"{prefix}{str(next_number).zfill(digit_length)}"
                else:
                    # 数字が含まれていないイレギュラーなコードだった場合
                    next_code = last_code + "_1"
                    
        except sqlite3.Error as e:
            print(f"[Warning] 新規器材番号の生成中にエラーが発生しました: {e}")
            # エラー時は安全のため重複しにくいタイムスタンプ等を仮発行するなどの対策
            from datetime import datetime
            next_code = f"{prefix}ERR_{datetime.now().strftime('%M%S')}"
        finally:
            if conn:
                conn.close()
                
        return next_code