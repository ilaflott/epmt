#!/bin/bash
export PAPIEX_TAGS="prog:dircrawl;phase:/usr"
find /usr > /dev/null 2>&1

export PAPIEX_TAGS="prog:find;phase:stat"
(find /etc -exec stat {} \; ; ls -l /) > /dev/null 2>&1
sleep 10


