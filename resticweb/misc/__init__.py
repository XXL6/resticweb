# from resticweb.tools.credential_manager import CredentialManager
from resticweb import db
from multiprocessing import current_process
from resticweb.tools.job_tools import JobQueue
from resticweb.tools.job_runner import JobRunner
from resticweb.tools.resource_manager import RWResourceManager

# this is a separate package for initializing objects that
# might not be initializable in the main __init__ file due to
# them trying to import things from the said __init__ file and
# thus causing a circular import

# if it's the main application process, that means its' db.session is
# going to have the necessary app context and we don't need to
# manually create sessions. Manually creating the sessions will
# cause issues in the main application process as some route
# handling might be multithreaded

resource_manager = RWResourceManager()
job_queue = JobQueue()
job_runner = JobRunner(queue=job_queue)
job_runner.start()
