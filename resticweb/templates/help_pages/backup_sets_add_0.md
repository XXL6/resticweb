# Backup set Files and Folders add

This form is used to add a list of files and folders to the database so that the files can later be used in backup jobs

## Fields

* Name: an arbitrary name for your backup set (the name also acts as a tag when the backup set is backed up to a repository)
* Concurrent job uses: much like a repository, backup sets can be set up so that only a certain amount of jobs can use this backup set at one time concurrently. It might be useful if the backup set resides on a slow drive that could slow down significantly when multiple things are reading/writing.
* Timeout (minutes): This is the timeout value in minutes for how long a job might wait for the backup set to become available before timing out. So if 2 is allocated for the concurrent job uses and there are 3 jobs attempting to use the set, one of those jobs will try to acquire the set for this many minutes. If the other two jobs are still running within the alotted time, the job times out.
* File/Folder select: Tree view of all the drives on a server. 
  * Only the topmost selected nodes are considered part of the path. For example: if a folder is selected by itself or all of the items are selected under that folder, then all additions to that folder in the future will also be part of the backup set. If only certain items are selected in a folder, any other additions to the parent folder will not be added.

## Controls

* Exclude Item: All the highlighted items from the tree will be added in the exclusion list so they will not be a part of the backup set.
  * You can select a folder and then exclude individual items within that folder so they will not be backed up.
* Exclude Custom: You can enter a custom exclusion filter that is supported by Restic

## Notes

I would avoid directly selecting items with square brackets in their name as Restic ignores them for some reason. If any files with a name containing the square brackets need to be backed up, their parent directory should be selected instead.
