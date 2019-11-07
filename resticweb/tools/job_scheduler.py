import logging
from threading import Thread, Lock
from schedule import Scheduler, Job, ScheduleError, ScheduleValueError
from resticweb.tools.job_build import JobBuilder
from resticweb.tools.local_session import LocalSession
from resticweb.models.general import Schedule, ScheduleJobMap
from wtforms import ValidationError
from time import sleep
from datetime import datetime, timedelta
from queue import Queue, Empty
import json
import random

class JobScheduler(Scheduler):

    t_lock = Lock()
    # janky way of updating the next_run for each schedule after
    # the job runs
    update_queue = Queue()

    def __init__(self):
        super().__init__()
        #self.logger = logging.getLogger("mainLogger")
        missed_schedules = []
        with LocalSession() as session:
            schedules = session.query(Schedule)
            for schedule in schedules:
                if self.should_run_missed_schedule(schedule):
                    missed_schedules.append(schedule.id)
                if schedule.next_run is not None and schedule.next_run < datetime.now():
                    schedule.next_run = self.init_schedule(schedule)
                else:
                    schedule.next_run = self.init_schedule(schedule, schedule.next_run)
            session.commit()
        for missed_schedule in missed_schedules:
            self.populate_queue_from_schedule_id(missed_schedule)
        #print(self.jobs)

    def pause_schedule(self, schedule_id):
        with LocalSession() as session:
            schedule = session.query(Schedule).filter_by(id=schedule_id).first()
            schedule.paused = True
            schedule.next_run = None
            session.commit()
        self.t_lock.acquire()
        self.clear(schedule_id)
        self.t_lock.release()

    def resume_schedule(self, schedule_id):
        #schedule_missed = False
        with LocalSession() as session:
            schedule = session.query(Schedule).filter_by(id=schedule_id).first()
        #    if self.should_run_missed_schedule(schedule):
        #        schedule_missed = True
            schedule.paused = False
            schedule.next_run = self.init_schedule(schedule)
            session.commit()
        #if schedule_missed:
        #    self.populate_queue_from_schedule_id(schedule_id)

    def toggle_pause(self, schedule_id):
        with LocalSession() as session:
            schedule = session.query(Schedule).filter_by(id=schedule_id).first()
            paused = schedule.paused
        if paused:
            self.resume_schedule(schedule_id)
        else:
            self.pause_schedule(schedule_id)

    def should_run_missed_schedule(self, schedule):
        if not schedule.next_run:
            return False
        minute_delta = (datetime.now() - schedule.next_run).seconds / 60
        return minute_delta < schedule.missed_timeout and minute_delta > 0

    def init_schedule(self, schedule, _next_run=None):
        if not schedule.paused:
            self.t_lock.acquire()
            time_unit = schedule.time_unit
            next_run = None
            if time_unit != 'week' and time_unit != 'weeks':
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
                    try:
                        job.at(schedule.time_at)
                    except ScheduleValueError:
                        pass
                    job._schedule_next_run()
                if _next_run:
                    job.next_run = _next_run
                next_run = job.next_run
            else:
                next_run = self.process_week_schedule(schedule, _next_run)
            self.t_lock.release()
            return next_run

    def process_week_schedule(self, schedule, _next_run=None):
        scheduled_days = json.loads(schedule.days)
        closest_time = None
        for day in scheduled_days:
            if day == 'monday':
                job = self.every().monday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif day == 'tuesday':
                job = self.every().tuesday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif day == 'wednesday':
                job = self.every().wednesday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif day == 'thursday':
                job = self.every().thursday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif day == 'friday':
                job = self.every().friday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif day == 'saturday':
                job = self.every().saturday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            elif day == 'sunday':
                job = self.every().sunday.do(self.populate_queue_from_schedule_id, schedule_id=schedule.id).tag(schedule.id)
            job.interval = schedule.time_interval if schedule.time_interval else 1

            if schedule.time_at and len(schedule.time_at) > 0:
                try:
                    job.at(schedule.time_at)
                except ScheduleValueError:
                    pass
                job._schedule_next_run()
            if (closest_time is None or job.next_run < closest_time):
                closest_time = job.next_run
        return closest_time
            

    def run_background(self):
        self.scheduler_thread = Thread(target=self.run, daemon=True)
        self.scheduler_thread.start()
    
    def run(self):
        while True:
            self.run_pending()
            self.process_update_queue()
            sleep(5)


    # need to customize the Job object itself a bit so we have to change
    # the "every" method to use the CustomJob instead of the regular Job
    def every(self, interval=1):
        """
        Schedule a new periodic job.

        :param interval: A quantity of a certain time unit
        :return: An unconfigured :class:`Job <Job>`
        """
        job = CustomJob(interval, self)
        return job

    def process_update_queue(self):
        self.t_lock.acquire()
        while True:
            try:
                item = self.update_queue.get(block=False)
                self.update_next_run(item)
            except Empty:
                self.t_lock.release()
                return
            
    # gets the next run time from the scheduler instance and stores it in the
    # database's schedule table
    def update_next_run(self, schedule_id):
        with LocalSession() as session:
            schedule = session.query(Schedule).filter_by(id=schedule_id).first()
            # schedule.next_run = self.get_job_from_tag(schedule_id).next_run
            schedule.next_run = self.get_next_run_from_tag(schedule_id)
            session.commit()

    def get_job_from_tag(self, tag):
        for job in self.jobs:
            if tag in job.tags:
                return job
        return None

    def get_next_run_from_tag(self, tag):
        jobs = self.get_jobs_from_tag(tag)
        closest_time = None
        for job in jobs:
            if closest_time is None or job.next_run < closest_time:
                closest_time = job.next_run
        return closest_time

    def get_jobs_from_tag(self, tag):
        job_list = []
        for job in self.jobs:
            if tag in job.tags:
                job_list.append(job)
        return job_list

    def populate_queue_from_schedule_id(self, schedule_id):
        self.t_lock.acquire()
        self.update_queue.put(schedule_id)
        self.t_lock.release()
        self.t_lock.acquire()
        job_ids = []
        with LocalSession() as session:
            schedule_job_maps = session.query(ScheduleJobMap).filter_by(schedule_id=schedule_id).order_by(ScheduleJobMap.sort.asc())
            for job_map in schedule_job_maps:
                job_ids.append(job_map.job_id)
            schedule = session.query(Schedule).filter_by(id=schedule_id).first()
            # schedule.next_run = self.get_job_from_tag(schedule_id).next_run
            schedule.next_run = self.get_next_run_from_tag(schedule_id)
            session.commit()
        for job_id in job_ids:
            builder = JobBuilder(saved_job_id=job_id)
            builder.run_job()
        self.t_lock.release()

    def add_schedule(self, name, time_unit, description=None, time_interval=None, time_at=None, missed_timeout=60, jobs=None, scheduled_days=None):
        with LocalSession() as session:
            new_schedule = Schedule(name=name, 
                                    description=description,
                                    time_unit=time_unit,
                                    time_interval=time_interval,
                                    time_at=time_at,
                                    missed_timeout=missed_timeout,
                                    days=json.dumps(scheduled_days))
            session.add(new_schedule)
            session.commit()
            sort_counter = 0
            if jobs:
                for job_id in jobs:
                    job_map = ScheduleJobMap(schedule_id=new_schedule.id,
                                            job_id=job_id,
                                            sort=sort_counter)
                    session.add(job_map)
                    sort_counter += 1
            new_schedule.next_run = self.init_schedule(new_schedule)
            session.commit()

    def update_jobs(self, schedule_id, jobs):
        self.t_lock.acquire()
        with LocalSession() as session:
            old_jobs = session.query(ScheduleJobMap).filter_by(schedule_id=schedule_id).all()
            for job in old_jobs:
                session.delete(job)
            sort_counter = 0
            for job_id in jobs:
                new_job = ScheduleJobMap(schedule_id=schedule_id, job_id=job_id, sort=sort_counter)
                session.add(new_job)
                sort_counter += 1
            session.commit()
        self.t_lock.release()

    def update_schedule(self, name, time_unit, schedule_id, description=None, time_interval=None, time_at=None, missed_timeout=60, scheduled_days=None):
        with LocalSession() as session:
            schedule = session.query(Schedule).filter_by(id=schedule_id).first()
            schedule.name = name
            schedule.description = description
            schedule.time_unit = time_unit
            schedule.time_interval = time_interval
            schedule.time_at = time_at
            schedule.missed_timeout = missed_timeout
            schedule.days = json.dumps(scheduled_days)
            session.commit()
            self.t_lock.acquire()
            self.clear(schedule_id)
            self.t_lock.release()
            schedule.next_run = self.init_schedule(schedule)
            session.commit()

    def delete_schedule(self, schedule_id):
        self.t_lock.acquire()
        self.clear(schedule_id)
        self.t_lock.release()
        with LocalSession() as session:
            schedule = session.query(Schedule).filter_by(id=schedule_id).first()
            session.delete(schedule)
            session.commit()
        

class CustomJob(Job):

    @property
    def monday(self):
        self.start_day = 'monday'
        return self.weeks

    @property
    def tuesday(self):
        self.start_day = 'tuesday'
        return self.weeks

    @property
    def wednesday(self):
        self.start_day = 'wednesday'
        return self.weeks

    @property
    def thursday(self):
        self.start_day = 'thursday'
        return self.weeks

    @property
    def friday(self):
        self.start_day = 'friday'
        return self.weeks

    @property
    def saturday(self):
        self.start_day = 'saturday'
        return self.weeks

    @property
    def sunday(self):
        self.start_day = 'sunday'
        return self.weeks

    def _schedule_next_run(self):
        """
        Compute the instant when this job should run next.
        """
        if self.unit not in ('seconds', 'minutes', 'hours', 'days', 'weeks'):
            raise ScheduleValueError('Invalid unit')

        if self.latest is not None:
            if not (self.latest >= self.interval):
                raise ScheduleError('`latest` is greater than `interval`')
            interval = random.randint(self.interval, self.latest)
        else:
            interval = self.interval

        self.period = timedelta(**{self.unit: interval})
        self.next_run = datetime.now() + self.period
        if self.start_day is not None:
            if self.unit != 'weeks':
                raise ScheduleValueError('`unit` should be \'weeks\'')
            weekdays = (
                'monday',
                'tuesday',
                'wednesday',
                'thursday',
                'friday',
                'saturday',
                'sunday'
            )
            if self.start_day not in weekdays:
                raise ScheduleValueError('Invalid start day')
            weekday = weekdays.index(self.start_day)
            days_ahead = weekday - self.next_run.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            #print("--------")
            #print(self.next_run)
            #print(timedelta(days_ahead))
            #print(self.period)
            self.next_run += timedelta(days_ahead) - (self.period / self.interval)
            #print(self.next_run)
        if self.at_time is not None:
            if (self.unit not in ('days', 'hours', 'minutes')
                    and self.start_day is None):
                raise ScheduleValueError(('Invalid unit without'
                                          ' specifying start day'))
            kwargs = {
                'second': self.at_time.second,
                'microsecond': 0
            }
            if self.unit == 'days' or self.start_day is not None:
                kwargs['hour'] = self.at_time.hour
            if self.unit in ['days', 'hours'] or self.start_day is not None:
                kwargs['minute'] = self.at_time.minute
            self.next_run = self.next_run.replace(**kwargs)
            # If we are running for the first time, make sure we run
            # at the specified time *today* (or *this hour*) as well
            if not self.last_run:
                now = datetime.now()
                if (self.unit == 'days' and self.at_time > now.time() and
                        self.interval == 1):
                    self.next_run = self.next_run - timedelta(days=1)
                elif self.unit == 'hours' \
                        and self.at_time.minute > now.minute \
                        or (self.at_time.minute == now.minute
                            and self.at_time.second > now.second):
                    self.next_run = self.next_run - timedelta(hours=1)
                elif self.unit == 'minutes' \
                        and self.at_time.second > now.second:
                    self.next_run = self.next_run - \
                                    timedelta(minutes=1)
        if self.start_day is not None and self.at_time is not None:
            # Let's see if we will still make that time we specified today
            if (self.next_run - datetime.now()).days >= 7 * self.interval:
                self.next_run -= self.period / self.interval
        #print(self.next_run)
        #print("--------")