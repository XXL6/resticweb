from resticweb.tools.local_session import LocalSession
from resticweb.models.general import Schedule, ScheduleJobMap, SavedJobs

def add_schedule(info_dict):
    new_schedule = Schedule(
        name=info_dict['name'],
        description=info_dict.get('description'),
        time_unit=info_dict['time_unit'],
        time_interval=info_dict.get('time_interval'),
        time_at=info_dict['time_at'],
        missed_timeout=info_dict['missed_timeout']
    )
    with LocalSession() as session:
        session.add(new_schedule)
        session.commit()
        sort_counter = 0
        for job in info_dict['job_list']:
            job_map = ScheduleJobMap(
                schedule_id=new_schedule.id,
                job_id=job,
                sort=sort_counter
            )
            session.add(job_map)
            sort_counter += 1
        session.commit()

def update_schedule(info_dict):
    with LocalSession() as session:
        schedule = session.query(Schedule).filter_by(info_dict['schedule_id']).first()
        schedule.name=info_dict['name'],
        schedule.description=info_dict.get('description'),
        schedule.time_unit=info_dict['time_unit'],
        schedule.time_interval=info_dict.get('time_interval'),
        schedule.time_at=info_dict['time_at'],
        schedule.missed_timeout=info_dict['missed_timeout']