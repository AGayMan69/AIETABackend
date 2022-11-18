#!/bin/bash
for KILLPID in `ps ax | grep ‘aietaservice’ | awk ‘{print $1;}’`; do
kill -9 $KILLPID;
done
