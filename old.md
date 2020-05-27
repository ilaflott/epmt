## EPMT under Docker 

Using the epmt-command docker image, we run **epmt** on a local directory to submit and set the submission DB host environment variable:

```
$ docker run --network=host -ti --rm -v `pwd`:/app -w /app -e EPMT_DB_HOST=<hostname> epmt-command:latest -v submit <localdir/>
```

This could be easily aliased for convenience.

