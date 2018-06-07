#!/bin/bash

sudo service ssh start

echo "starting services"
python /home/biggroum/biggroum/fixr_groum_search_frontend/app.py --host 0.0.0.0 & nohup /home/biggroum/biggroum/FixrService-Backend/target/universal/stage/bin/fixrservice-backend &

while sleep 60; do
  ps aux | fixrservice  | grep -q -v grep
  PROCESS_1_STATUS=$?

  # If the greps above find anything, they exit with 0 status
  # If they are not both 0, then something is wrong
  if [ $PROCESS_1_STATUS -ne 0 ]; then
    echo "Fixrservice  has already exited."
#    exit 1
  fi

  ps aux | app.py  | grep -q -v grep
  PROCESS_1_STATUS=$?

  # If the greps above find anything, they exit with 0 status
  # If they are not both 0, then something is wrong
  if [ $PROCESS_1_STATUS -ne 0 ]; then
    echo "The web server  has already exited."
#    exit 1
  fi
done
