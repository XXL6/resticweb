# Local repository add form

This form is used to specify parameters needed to create/import an existing Restic repository that is located on the local machine

## Fields

* Name: A name for your repository. Can be anything, but it cannot be the same as an existing repository name.
* Repo Password: A password for your repository. Restic will use this to encrypt the filed so only you can access them.
* Description: Any additional information you might want to specify about your repository
* Cache repository objects: If checked, all of the snapshots/objects will be retrieved from the repository and added to a local database. For now this only means that you can browse the snapshots/files when the repository is disconnected/offline. In the future this might be used to search files and computer other metrics.
  * Note: If the repository has a large number of files, the database size will increase significantly.
* Concurrent job uses: how many jobs can access this repository simultaneously. Some jobs like prune will use up all of the uses as it requires an exclusive lock on the repository
* Timeout (minutes): This is the timeout value in minutes for how long a job might wait for the repository to become available before timing out. So if 2 is allocated for the concurrent job uses and there are 3 jobs attempting to use the repository, one of those jobs will try to acquire the repository for this many minutes. If the other two jobs are still running within the alotted time, the job times out.
* Address: A physical address for your repository, same as you would type into the file explorer address bar. You can use the browse button to view your file system in-browser if necessary. Do not worry about the slashes being forwards/backwards. If the folder selected already has a Restic repository within it, the app will attempt to import the existing repository
