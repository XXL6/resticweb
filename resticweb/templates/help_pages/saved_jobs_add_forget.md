# Forget policy set

This form is used to set up a snapshot forget policy in order to remove old snapshots and free up space.

## Fields

* Name: Can be anything as long as it's unique between other saved jobs
* Description: Can be anything
* Backup Set: The forget policy will be set for this particular backup set on the repository. Other snapshots/backup sets will not be touched unless they contain a tag that is the same as the name of the backup set.
* Repository: The forget policy will only be run on the specified repository.
* Additional Parameters: Can add any extra parameters supported by the forget functionality

### Specify Retention Policy

The policy fields directly correspond with the supported flags by Restic. Read more about them [here](https://restic.readthedocs.io/en/latest/060_forget.html#removing-snapshots-according-to-a-policy)

* Prune: checking this box will add the --prune parameter to the restic command which will initiate a prune after the forget policy is applied. The prune can also be done via a standalone job.
