from fastapi import APIRouter
from .service import list_tasks, create_task
router = APIRouter()
@router.get('/api/tasks')
def get_tasks():
    return list_tasks()
@router.post('/api/tasks')
def post_task():
    return create_task('demo')
