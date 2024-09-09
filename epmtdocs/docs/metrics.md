Data Dictionary
---------------

papiex collects the following data for each thread:

| Key                   	| Source                                           	| Datatype       	| Scope   	| Description                                            	|
|-----------------------	|--------------------------------------------------	|----------------	|---------	|--------------------------------------------------------	|
| 1. tags                  	| getenv("PAPIEX_TAGS")                            	| Escaped string 	| Process 	| User specified tags for this executable                	|
| 2. hostname              	| gethostname()                                    	| String         	| Process 	| hostname                                               	|
| 3. exename               	| PAPI                                             	| String         	| Process 	| Name of the application, usually argv[0]               	|
| 4. path                  	| PAPI                                             	| String         	| Process 	| Path to the application                                	|
| 5. args                  	| monitor                                          	| Escaped string 	| Process 	| All arguments to exe excluding argv[0]                 	|
| 6. exitcode              	| exit()                                           	| Integer        	| Process 	| Exit code                                              	|
| 7. exitsignal              	| monitor                                           	| Integer        	| Process 	| Exited due to a signal                                       	|
| 8. pid                   	| getpid()                                         	| Integer        	| Process 	| Process id                                             	|
| 9. generation            	| monitor                                          	| Integer        	| Process 	| Incremented after every exec() or PID wrap             	|
| 10. ppid                  	| getppid()                                        	| Integer        	| Process 	| Parent process id                                      	|
| 11. pgid                  	| getpgid()                                        	| Integer        	| Process 	| Process group id                                       	|
| 12. sid                   	| getsid()                                         	| Integer        	| Process 	| Process session id                                     	|
| 13. numtids               	| monitor                                          	| Integer        	| Process 	| Number of threads caught by instrumentation            	|
| 14. numranks               	| monitor(MPI)						| Integer        	| Process 	| Number of MPI ranks detected			            	|
| 15. tid                   	| gettid()                                         	| Integer        	| Process 	| Thread id                                              	|
| 16. mpirank                  	| monitor(MPI)                                         	| Integer        	| Thread 	| MPI rank 		                                     	|
| 17. start                 	| gettimeofday()                                   	| Integer        	| Process 	| Microsecond timestamp at start                         	|
| 18. end                   	| gettimeofday()                                   	| Integer        	| Process 	| Microsecond timestamp at end                           	|
| 19. usertime              	| getrusage(RUSAGE_THREAD)                         	| Integer        	| Thread  	| Microsecond user time                                  	|
| 20. systemtime            	| getrusage(RUSAGE_THREAD)                         	| Integer        	| Thread  	| Microsecond system time                                	|
| 21. rssmax                	| getrusage(RUSAGE_THREAD)                         	| Integer        	| Thread  	| Kb max resident set size                               	|
| 22. minflt                	| getrusage(RUSAGE_THREAD)                         	| Integer        	| Thread  	| Minor faults (TLB misses/new page frames)              	|
| 23. majflt                	| getrusage(RUSAGE_THREAD)                         	| Integer        	| Thread  	| Major page faults (requiring I/O)                      	|
| 24. inblock               	| getrusage(RUSAGE_THREAD)                         	| Integer        	| Thread  	| 512B blocks read from I/O                              	|
| 25. outblock              	| getrusage(RUSAGE_THREAD)                         	| Integer        	| Thread  	| 512B blocks written to I/O                             	|
| 26. vol_ctxsw             	| getrusage(RUSAGE_THREAD)                         	| Integer        	| Thread  	| Voluntary context switches (yields)                    	|
| 27. invol_ctxsw           	| getrusage(RUSAGE_THREAD)                         	| Integer        	| Thread  	| Involuntary context switches (preemptions)             	|
| 28. cminflt           	| /proc/<pid>/task/<tid>/stat field 11             	| Integer        	| Process 	| minflt (20) for all wait()ed children                       	|
| 29. cmajflt             	| /proc/<pid>/task/<tid>/stat field 22             	| Integer        	| Thread  	| majflt (21) for all wait()ed children			     	|
| 30. cutime            	| /proc/<pid>/task/<tid>/stat field 20             	| Integer        	| Process 	| utime (17) for all wait()ed children			     	|
| 31. cstime             	| /proc/<pid>/task/<tid>/stat field 22             	| Integer        	| Thread  	| stime (18) for all wait()ed children			     	|
| 32. num_threads           	| /proc/<pid>/task/<tid>/stat field 20             	| Integer        	| Process 	| Threads in process at finish                           	|
| 33. starttime             	| /proc/<pid>/task/<tid>/stat field 22             	| Integer        	| Thread  	| Timestamp in jiffies after boot thread was started     	|
| 34. processor             	| /proc/<pid>/task/<tid>/stat field 39             	| Integer        	| Thread  	| CPU this thread last ran on                            	|
| 35. delayacct_blkio_time  	| /proc/<pid>/task/<tid>/stat field 42             	| Integer        	| Thread  	| Jiffies process blocked in D state on I/O device       	|
| 36. guest_time            	| /proc/<pid>/task/<tid>/stat field 43             	| Integer        	| Thread  	| Jiffies running a virtual CPU for a guest OS           	|
| 37. rchar                 	| /proc/<pid>/task/<tid>/io line 1                 	| Integer        	| Thread  	| Bytes read via syscall (maybe from cache not dev I/O)  	|
| 38. wchar                 	| /proc/<pid>/task/<tid>/io line 2                 	| Integer        	| Thread  	| Bytes written via syscall (maybe to cache not dev I/O) 	|
| 39. syscr                 	| /proc/<pid>/task/<tid>/io line 3                 	| Integer        	| Thread  	| Read syscalls                                          	|
| 40. syscw                 	| /proc/<pid>/task/<tid>/io line 4                 	| Integer        	| Thread  	| Write syscalls                                         	|
| 41. read_bytes            	| /proc/<pid>/task/<tid>/io line 5                 	| Integer        	| Thread  	| Bytes read from I/O device                             	|
| 42. write_bytes           	| /proc/<pid>/task/<tid>/io line 6                 	| Integer        	| Thread  	| Bytes written to I/O device                            	|
| 43. cancelled_write_bytes 	| /proc/<pid>/task/<tid>/io line 7                 	| Integer        	| Thread  	| Bytes discarded by truncation                			|
| 44. time_oncpu            	| /proc/<pid>/task/<tid>/schedstat                 	| Integer        	| Thread  	| Nanoseconds spent running                     	    	|
| 45. time_waiting          	| /proc/<pid>/task/<tid>/schedstat                 	| Integer        	| Thread  	| Nanoseconds runnable but waiting       	            	|
| 46. timeslices            	| /proc/<pid>/task/<tid>/schedstat                 	| Integer        	| Thread  	| Number of run periods on CPU                           	|
| 47. rdtsc_duration        	| PAPI                                           	| Integer        	| Thread  	| If PAPI, real time cycle duration of thread
| *                             | PAPI                                              | Integer           | Thread    | PAPI metrics 
