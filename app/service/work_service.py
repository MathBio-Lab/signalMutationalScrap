# repositories/work_repository.py
from app.repositories.base import BaseRepository

class WorkRepository(BaseRepository[Work]):
    def __init__(self, session):
        super().__init__(Work, session)
