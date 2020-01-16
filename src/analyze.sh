#!/bin/bash

# Run me like ./analyse.sh /root/out/repos results4.log

# Whitespace save way over iterating over filenames
find $1 -name "*.zip" | while read fname; do
  python analyze.py "$fname" >> $2 2>&1 &
done
  
# Wait for the processes to finish
wait