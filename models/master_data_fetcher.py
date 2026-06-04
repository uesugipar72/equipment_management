import sqlite3

class MasterDataFetcher:
    """データベースのマスタテーブルからデータを取得するクラス"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path

    def fetch_all(self, table_name: str):
        """
        指定されたマスタテーブルからすべてのデータを取得し、(id, name) のリストを返す。
        存在しないテーブルやカラムエラーが発生した場合は空のリストを返す。
        """
        # 各テーブルの一般的なカラム名（id, 名称カラム）
        # ※もし実際のマスタの名称カラムが「name」以外（例: c_name等）ならここを調整します
        name_column = "name"
        
        # 例外的なカラム名マッピング（必要に応じて）
        if table_name == "categorie_master":
            name_column = "name"  # もしマスタ側のカラム名が異なる場合はここを変更
            
        query = f"SELECT id, {name_column} FROM {table_name} ORDER BY id ASC;"
        
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()  # [(1, 'カテゴリA'), (2, 'カテゴリB'), ...] の形式
        except sqlite3.Error as e:
            print(f"[Warning] マスタデータ取得エラー ({table_name}): {e}")
            return []
        finally:
            if conn:
                conn.close()