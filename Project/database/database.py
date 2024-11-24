import mysql.connector
from mysql.connector import Error
from typing import Optional
from ..core.config import settings

class Database:
    def __init__(self):
        self.connection = None

    async def connect(self) -> Optional[mysql.connector.MySQLConnection]:
        try:
            if not self.connection or not self.connection.is_connected():
                self.connection = mysql.connector.connect(
                    host=settings.DB_HOST,
                    database=settings.DB_NAME,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    charset='utf8mb4',
                    collation='utf8mb4_general_ci'
                )
            return self.connection
        except Error as e:
            print(f"DB 연결 오류: {e}")
            return None

    async def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()