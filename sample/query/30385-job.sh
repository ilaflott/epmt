#!/bin/sh

export PAPIEX_TAGS="app:w;phase:load"
w | grep load
export PAPIEX_TAGS="app:users;phase:user-count"
users|sort| uniq| wc -l
