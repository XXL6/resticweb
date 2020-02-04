from resticweb.tools.rv_process import RVProcess
from resticweb.tools.local_session import LocalSession
from resticweb.tools.repository_tools import clear_snapshot_objects, clear_repo_snapshot_objects
import os
import subprocess
import traceback

class ClearSnapshotObjects(RVProcess):

    def __init__(self, **kwargs):
        super().__init__()
        self.name = 'ClearSnapshotObjects'
        self.repo_id = kwargs['repo_id']
        self.snapshot_id = kwargs.get('snapshot_id')


    def run(self):
        super().run()
        if self.snapshot_id:
            self.log(f"Clearing objects for snapshot: {self.snapshot_id}")
            self.step("Clearing database")
            try:
                clear_snapshot_objects(self.repo_id, self.snapshot_id)
            except Exception as e:
                self.log(f"Clearing the database failed.")
                self.log(e)
                self.status('error')
                return
            self.status("success")
        else:
            self.log(f"Clearing objects from repository with id: {self.repo_id}")
            self.step("Clearing database")
            try:
                clear_repo_snapshot_objects(self.repo_id)
            except Exception as e:
                self.log(f"Clearing the database failed.")
                self.log(e)
                self.status('error')
                return
            self.status("success")


class VacuumDatabase(RVProcess):

    def __init__(self, **kwargs):
        super().__init__()
        self.name = 'VacuumDatabase'

    def run(self):
        super().run()
        with LocalSession() as session:
            try:
                session.execute("VACUUM")
            except Exception as e:
                self.log(e)
                self.status('error')
                return
        self.log('Successfully vacuumed the database')
        self.status('success')
        return