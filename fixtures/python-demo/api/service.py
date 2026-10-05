from .storage import read_tasks, save_task
def list_tasks():
    return read_tasks()
def create_task(title):
    return save_task(title)
