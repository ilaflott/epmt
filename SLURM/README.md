## BUGS

* We only handle ONE job step in SLURM allocations, that is the submitted script.
* srun in an empty script is essentially the second job step - currently not handled.
* Stage/collation does not work on 'remote' nodes, ie any sruns.

## SLURM Notes

TaskProlog and TaskEpilog are not run during:
 * salloc

But are run during:
 * sbatch
 * srun


