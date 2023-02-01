from flask_login import UserMixin

from db import get_db

class User(UserMixin):
    def __init__(self, id, name):
        self.id = id
        self.name = name
        

    @staticmethod
    def get(user_id):
        db = get_db()
        user = db.execute(
            "SELECT * FROM user WHERE id = ?", (user_id,)
        ).fetchone()
        if not user:
            return None

        user = User(
            id=user[0], name=user[1]
        )
        return user

    @staticmethod
    def create(id, name):
        db = get_db()
        db.execute(
            "INSERT INTO user (id, name) "
            "VALUES (?, ?)",
            (id, name),
        )
        db.commit()

class Task():
    def __init__(self, id, user_id, date, sketch, timeline, task_type):
        self.id = id
        self.user_id = user_id
        self.date = date
        self.sketch = sketch
        self.timeline = timeline
        self.task_type = task_type

    @staticmethod
    def get(task_id):
        db = get_db()
        task = db.execute(
            "SELECT * FROM task WHERE id = ?", (task_id,)
        ).fetchone()
        if not task:
            return None

        task = Task(
            id=task[0], user_id=task[1], date=task[2], sketch=task[3], timeline=task[4], task_type=task[5]
        )

        return task

    @staticmethod
    def create(id, user_id, date, sketch, timeline, task_type):
        db = get_db()
        db.execute(
            "INSERT INTO task (id, user_id, date, sketch, timeline, task_type) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (id, user_id, date, sketch, timeline, task_type),
        )
        db.commit()

    @staticmethod
    def get_all():
        db = get_db()
        tasks = db.execute(
            "SELECT * FROM task"
        ).fetchall()
        if not tasks:
            return None

        tasks = [Task(
            id=task[0], user_id=task[1], date=task[2], sketch=task[3], timeline=task[4], task_type=task[5]
        ) for task in tasks]
        return tasks


    @staticmethod
    def get_all_by_user(user_id):
        db = get_db()
        tasks = db.execute(
            "SELECT * FROM task WHERE user_id = ?", (user_id,)
        ).fetchall()
        if not tasks:
            return None
        #tasks = [task[0] for task in tasks]
        tasks = [Task(task[0], task[1], task[2], task[3], task[4], task[5]) for task in tasks]
        
        return tasks
