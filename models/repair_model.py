# ==================================================
# C:\equipment_management\models\repair_model.py
# ==================================================
from models.db_manager import DBManager

class RepairModel:  # 🎯 ここが RepairMoeel になっていないか確認！
    """修理履歴および器材詳細のデータアクセスを担当するModelクラス"""

    @classmethod
    def fetch_equipment_detail(cls, equipment_code: str) -> dict:
        """
        指定された器材コードに対応する詳細情報を、マスタ名称を結合した状態で1件取得する。
        """
        query = """
            SELECT 
                e.id, e.equipment_code, e.name, e.remarks, e.purchase_date, e.model,
                cat.name AS categorie_name,
                st.name AS status_name,
                dept.name AS department_name,
                rm.name AS room_name,
                mfr.name AS manufacturer_name,
                sel.name AS celler_name
            FROM equipment e
            LEFT JOIN categorie_master cat ON e.categorie_id = cat.id
            LEFT JOIN statuse_master st ON e.statuse_id = st.id
            LEFT JOIN department_master dept ON e.department_id = dept.id
            LEFT JOIN room_master rm ON e.room_id = rm.id
            LEFT JOIN manufacturer_master mfr ON e.manufacturer_id = mfr.id
            LEFT JOIN celler_master sel ON e.celler_id = sel.id
            WHERE e.equipment_code = ?;
        """
        # 🎯 インデント（行頭のスペース）がずれていないか注意
        with DBManager.get_cursor() as cursor:
            cursor.execute(query, (equipment_code,))
            row = cursor.fetchone()
            
        if not row:
            return {}

        # 辞書型にマッピングしてView側が扱いやすいように返却
        return {
            "id": row[0],
            "equipment_code": row[1],
            "name": row[2],
            "remarks": row[3],
            "purchase_date": row[4],
            "model": row[5],
            "categorie_name": row[6] or "不明",
            "status_name": row[7] or "不明",
            "department_name": row[8] or "不明",
            "room_name": row[9] or "不明",
            "manufacturer_name": row[10] or "不明",
            "celler_name": row[11] or "不明"
        }

    @classmethod
    def fetch_history_by_code(cls, equipment_code: str) -> list:
        """
        指定された器材コードの修理履歴一覧を、マスタ名称を結合した状態で取得する。
        """
        query = """
            SELECT r.id,
                rs.name AS status, 
                r.request_date,
                r.completion_date,
                rt.name AS repair_type,
                c.name AS vendor,
                r.technician,
                r.details,
                r.remarks
            FROM repair r
            LEFT JOIN repair_statuse_master rs ON r.repairstatuses = rs.id
            LEFT JOIN repair_type_master rt ON r.repairtype = rt.id
            LEFT JOIN celler_master c ON r.vendor = c.id
            WHERE r.equipment_code = ?
            ORDER BY r.request_date DESC;
        """
        with DBManager.get_cursor() as cursor:
            cursor.execute(query, (equipment_code,))
            return cursor.fetchall()

    @classmethod
    def fetch_by_id(cls, repair_id: int):
        """
        指定された修理IDの生データを1件取得する（EditRepairWindow用）
        """
        query = """
            SELECT repairstatuses, request_date, completion_date, repairtype, vendor,
                   technician, details, remarks
            FROM repair WHERE id = ?
        """
        with DBManager.get_cursor() as cursor:
            cursor.execute(query, (repair_id,))
            return cursor.fetchone()