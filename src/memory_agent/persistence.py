import os
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

class Database:
    def __init__(self, db_path: str = "state_db/example.db") -> None:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        memory = SqliteSaver(conn)
        self.memory = memory

memory = Database().memory

