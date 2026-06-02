import sqlite3
import os
import json
from contextlib import contextmanager
from typing import Iterator

class DBManager:
    """データベース接続と絶対パスの管理を行うベースクラス"""
    
    # 1. プロジェクトルートの絶対パスを取得 (このファイルから見て2つ上の階層)
    # ※ DBManagerが「models/db_manager.py」などにある場合はこれ、
    # 　 一番上のルート直下にある場合は os.path.dirname(__file__) に調整してください。
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    _config_path = os.path.join(_PROJECT_ROOT, "config.json")
    try:
        with open(_config_path, "r", encoding="utf-8") as f:
            _config = json.load(f)
        _db_filename = _config.get("db_name", "equipment_management.db")
    except FileNotFoundError:
        _db_filename = "equipment_management.db"

    # 🎯【最重要】読み込んだデータベース名を「絶対パス」に一元化
    DB_PATH = os.path.join(_PROJECT_ROOT, _db_filename)

    @classmethod
    @contextmanager
    def get_connection(cls) -> Iterator[sqlite3.Connection]:
        """
        データの検索（SELECT）や、複数処理を一つのトランザクションでまとめたい時に
        Connectionオブジェクトそのものを提供するコンテキストマネージャ
        """
        conn = sqlite3.connect(cls.DB_PATH)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @classmethod
    @contextmanager
    def get_cursor(cls) -> Iterator[sqlite3.Cursor]:
        """SQLを一発実行するためのカーソルを提供するコンテキストマネージャ"""
        # 先ほど追加した get_connection を中で使い回すことで安全性を向上
        with cls.get_connection() as conn:
            yield conn.cursor()