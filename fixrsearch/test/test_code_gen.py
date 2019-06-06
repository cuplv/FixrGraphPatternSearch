"""
"""

import os
import sys
import logging
import requests
import json
import optparse
import httplib


import fixrsearch

from fixrsearch.code.acdfg_repr import AcdfgRepr


from fixrgraph.annotator.protobuf.proto_acdfg_pb2 import Acdfg as AcdfgProto
from fixrgraph.annotator.protobuf.proto_search_pb2 import SearchResults


try:
    import unittest2 as unittest
except ImportError:
    import unittest

class TestGen(unittest.TestCase):
    def __init__(self, *args, **kwargs):
      super(TestGen, self).__init__(*args, **kwargs)


    def test_print(self):
      graph_path = os.path.join(os.path.dirname(fixrsearch.test.__file__),
                                "data/graphs/mmcguinn/iSENSE-Hardware/" \
                                "0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad/" \
                                "edu.uml.cs.droidsense.comm.RestAPIDbAdapter_" \
                                "getExperiments.acdfg.bin")

      f = open(graph_path,'rb')
      acdfgProto = AcdfgProto() # create a new acdfg
      acdfgProto.ParseFromString(f.read())
      f.close()

      acdfg = AcdfgRepr(acdfgProto)

      acdfg.print_dot(sys.stdout)
