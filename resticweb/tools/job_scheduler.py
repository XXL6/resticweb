import logging
from threading import Thread, Lock
from schedule import Scheduler
from resticweb.tools.job_build import JobBuilder
from resticweb.tools.local_session import LocalSession
from resticweb.models.general import Schedule, ScheduleJobMap
from time import sleep
from datetime import datetime


class JobScheduler(Scheduler):

    t_lock = Lock()

    def __init__(self):
        super().__init__()
        #self.logger = logging.getLogger("mainLogger")
        missed_schedules = []
        with LocalSession() as session:
            schedules = session.query(Schedule)
            for schedule in schedules:
                if self.should_run_missed_schedule(schedule):
                    missed_schedules.append(schedule.id)
                self.init_schedule(schedule)
        for missed_schedule in missed_schedules:
            self.populate_queue_from_schedule_id(missed_schedule)
        print("ayylmao")

    def pause_schedule(self, schedule_id):
        with LocalSession() as session:
            schedule = session.query(Schedule).filter_by(id=schedule_id).first()
            schedule.next_run = None
            schedule.paused = True
            session.commit()
        self.t_lock.acquire()
        self.clear(schedule_id)
        self.t_lock.release()

    def resume_schedule(self, schedule_id):
        schedule_missed = False
        with LocalSession() as session:
            schedule = session.query(Schedule).filter_by(id=schedule_id).first()
            if self.should_run_missed_schedule(schedule):
                schedule_missed = True
            schedule.next_run = self.init_schedule(schedule)
            schedule.paused = False
            session.commit()
        if schedule_missed:
            self.populate_queue_from_schedule_id(schedule_id)

    def should_run_missed_schedule(self, schedule):
        minute_delta = (datetime.now() - schedule.next_run).seconds / 60
        return minute_delta < schedule.missed_timeout and minute_delta > 0

    def init_schedule(self, schedule):
        if not schedule.paused:
            self.t_lock.acquire()
            time_unit = schedule.time_unit
            if time_unit == 'minute':
                job = self.every().minute.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'minutes':
                job = self.every(schedule.time_interval).minutes.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'hour':
                job = job = self.every().hour.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'hours':
                job = self.every(schedule.time_interval).hours.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'day':
                job = self.every().day.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'days':
                job = self.every(schedule.time_interval).days.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'week':
                job = self.every().week.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'weeks':
                job = self.every(schedule.time_interval).weeks.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'monday':
                job = self.every().monday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'tuesday':
                job = self.every().tuesday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'wednesday':
                job = self.every().wednesday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'thursday':
                job = self.every().thursday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'friday':
                job = self.every().friday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'saturday':
                job = self.every().saturday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif time_unit == 'sunday':
                job = self.every().sunday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            if schedule.time_at and len(schedule.time_at) > 0:
                job.at(schedule.time_at)
            self.t_lock.release()
            return job.next_run

    def run_background(self):
        self.scheduler_thread = Thread(target=self.run, daemon=True)
        self.scheduler_thread.start()
    
    def run(self):
        while True:
            self.run_pending()
            sleep(5)

    def populate_queue_from_schedule_id(self, schedule_id):
        self.t_lock.acquire()
        job_ids = []
        with LocalSession() as session:
            schedule_job_maps = session.query(ScheduleJobMap).filter_by(schedule_id=schedule_id).order_by(ScheduleJobMap.sort.asc())
            for job_map in schedule_job_maps:
                job_ids.append(job_map.job_id)
        for job_id in job_ids:
            builder = JobBuilder(saved_job_id=job_id)
            builder.run_job()
        self.t_lock.release()

    def add_schedule(self, name, time_unit, description=None, time_interval=None, time_at=None, missed_timeout=60, jobs=None):
        with LocalSession() as session:
            new_schedule = Schedule(name=name, 
                                    description=description,
                                    time_unit=time_unit,
                                    time_interval=time_interval,
                                    time_at=time_at,
                                    missed_timeout=missed_timeout)
            session.add(new_schedule)
            session.commit()
            if jobs:
                for job_id, sort in jobs:
                    job_map = ScheduleJobMap(schedule_id=new_schedule.id,
                                            job_id=job_id,
                                            sort=sort)
                    session.add(job_map)
            new_schedule.next_run = self.init_schedule(new_schedule)
            session.commit()

    def update_jobs(self, schedule_id, jobs):
        self.t_lock.acquire()
        with LocalSession() as session:
            old_jobs = session.query(ScheduleJobMap).filter_by(schedule_id=schedule_id).all()
            for job in old_jobs:
                session.delete(job)
            for job_id, sort in jobs:
                new_job = ScheduleJobMap(schedule_id=schedule_id, job_id=job_id, sort=sort)
                session.add(new_job)
            session.commit()
        self.t_lock.release()

    def update_schedule(self, name, time_unit, schedule_id, description=None, time_interval=None, time_at=None, missed_timeout=60):
        with LocalSession() as session:
            schedule = session.query(Schedule).filter_by(id=schedule_id).first()
            schedule.name = name
            schedule.description = description
            schedule.time_unit = time_unit
            schedule.time_interval = time_interval
            schedule.time_at = time_at
            schedule.missed_timeout = missed_timeout
            session.commit()
        self.t_lock.acquire()
        self.clear(schedule_id)
        self.t_lock.release()
        self.init_schedule(schedule)

    def delete_schedule(self, schedule_id):
        self.t_lock.acquire()
        self.clear(schedule_id)
        self.t_lock.release()
        with LocalSession() as session:
            schedule = session.query(Schedule).filter_by(id=schedule_id).first()
            session.delete(schedule)
        