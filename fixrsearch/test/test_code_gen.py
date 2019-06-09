"""
"""

import os
import sys
import logging
import requests
import json
import optparse
import httplib
import StringIO

import fixrsearch

from fixrsearch.codegen.acdfg_repr import AcdfgRepr
from fixrsearch.codegen.generator import CodeGenerator, CFGAnalyzer


from fixrgraph.annotator.protobuf.proto_acdfg_pb2 import Acdfg as AcdfgProto
from fixrgraph.annotator.protobuf.proto_search_pb2 import SearchResults
from fixrgraph.annotator.protobuf.proto_acdfg_bin_pb2 import Lattice



try:
  import unittest2 as unittest
except ImportError:
  import unittest

class TestGen(unittest.TestCase):
  def __init__(self, *args, **kwargs):
    super(TestGen, self).__init__(*args, **kwargs)


  def test_print(self):
    graph_path = os.path.join(os.path.dirname(fixrsearch.test.__file__),
                "data", "graphs", "mmcguinn", "iSENSE-Hardware",
                "0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad",
                "edu.uml.cs.droidsense.comm.RestAPIDbAdapter_" \
                "getExperiments.acdfg.bin")

    f = open(graph_path,'rb')
    acdfgProto = AcdfgProto() # create a new acdfg
    acdfgProto.ParseFromString(f.read())
    f.close()

    acdfg = AcdfgRepr(acdfgProto)

    output = StringIO.StringIO()
    acdfg.print_dot(output)


  def test_loops(self):
    graph_path = os.path.join(os.path.dirname(fixrsearch.test.__file__),
                "data", "graphs", "mmcguinn", "iSENSE-Hardware",
                "0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad",
                "edu.uml.cs.droidsense.comm.RestAPIDbAdapter_" \
                "getExperiments.acdfg.bin")

    f = open(graph_path,'rb')
    acdfgProto = AcdfgProto() # create a new acdfg
    acdfgProto.ParseFromString(f.read())
    f.close()

    acdfg = AcdfgRepr(acdfgProto)

    roots = acdfg.find_control_roots()
    self.assertTrue(len(roots) == 1)

    for r in roots:
      cfg_analyzer = CFGAnalyzer(acdfg, r)
      loops = cfg_analyzer.get_loops()

  def test_ast_gen(self):
    # get acdfg from pattern
    lattice_path = os.path.join(os.path.dirname(fixrsearch.test.__file__),
                  "data",
                  "codegen",
                  "cluster_248_lattice.bin")
    lattice = Lattice()
    with open(lattice_path ,'rb') as fsearch:
      lattice.ParseFromString(fsearch.read())
      fsearch.close()
    popularBin = None
    for popular in lattice.bins:
      if popular.id != 5:  continue
      popularBin = popular
      break
    for f in popular.names_to_iso:
      acdfg_reduced = AcdfgRepr(f.iso.acdfg_1)
      break

    # get original acdfg
    acdfg_path = os.path.join(os.path.dirname(fixrsearch.test.__file__),
                              "data",
                              "codegen",
                              "com.callmewill.launcher2.CellLayout" \
                              "_onMeasure.acdfg.bin")
    acdfg_proto = AcdfgProto()
    with open(acdfg_path, "rb") as f1:
      acdfg_proto.ParseFromString(f1.read())
      f1.close()
    acdfg_original = AcdfgRepr(acdfg_proto)

    code_gen = CodeGenerator(acdfg_reduced, acdfg_original)
    text = code_gen.get_code_text()

    
