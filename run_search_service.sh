#!/bin/bash
python fixrsearch/search_service.py -a localhost -p 8081 -g ./fixrsearch/test/data/graphs -c ./fixrsearch/test/data/clusters -i ../FixrGraphIso/build/src/fixrgraphiso/searchlattice -d -l 8080 -z localhost
