import sqlite3
def read_tasks():
    with sqlite3.connect(':memory:') as db:
        return []
def save_task(title):
    return {'title': title}
