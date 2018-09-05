#!/bin/bash

python ./fixrsearch/search_service.py  -c /persist/clusters -i /home/biggroum/biggroum/FixrGraphIso/build/src/fixrgraphiso/searchlattice -g /persist/graphs --address 0.0.0.0 -p 8081

while sleep 60; do
    echo "Monitoring..."
done
