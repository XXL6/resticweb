# Schedule add form

This form is used to set up a simple schedule and assign saved jobs.

## Fields

* Name: Can be anything as long as it's unique between other schedules
* Description: Can be anything
* Schedule Miss Timeout: How long can the application stay offline after a job is supposed to run for it to be considered missed and rescheduled.
  * Ex. A schedule is supposed to fire at 12:30 and the computer/application gets turned off at 12:29. If the timeout is set to 30 minutes, then if application is turned back on between 12:30 and 13:00, the scheduled job will go ahead and run and the schedule will be rescheduled. If the application gets turned on after 13:00, the job will not run and the schedule will be rescheduled to run next time.
* Run this schedule every [] [] at []: How often should the schedule run. If the time unit (minutes, hours, etc.) is plural, then you'll also have to set how many of these time units in between runs. 
  * The "at" field is optional, but it will specify when exactly the job should run.
    * Ex: Job is set to run every hour with the "at" field set to ":25". So the job will run every hour at 25 minutes past the hour
    * Ex: Job is set to run every Wednesday at "16:00". So the job will run evey wednesday at 4:00PM
  * Scheduler uses "schedule" as the scheduling backend. If you wish to learn more, visit [schedule](https://schedule.readthedocs.io/en/stable/) for more specific examples.

## Controls

* Clicking the little plus sign underneath the "Scheduled jobs" label will open up the job selector which is just a list of all saved jobs. You can select one or more of those and click Ok. The jobs will then get added to the table.
* Once the job is in the "Scheduled jobs" table, it can be removed, or moved up/down via the arrow buttons to the right.
* Once the schedule fires, the queue gets populated with the listed jobs in the order that they appear.
