""" Test the creation of the index

"""

import os
import logging
import shutil

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import fixrsearch
from fixrsearch.groum_index import GroumIndex


class TestGroumIndex(unittest.TestCase):
  def __init__(self, *args, **kwargs):
    super(TestGroumIndex, self).__init__(*args, **kwargs)

    self.test_path = None
    self.data_path = None
    self.graph_path = None
    self.cluster_path = None

  def setUp(self):
    self.test_path = os.path.dirname(fixrsearch.test.__file__)
    self.data_path = os.path.join(self.test_path, "data")
    assert os.path.isdir(self.data_path)
    self.graph_path = os.path.join(self.data_path, "graphs")

  def tearDown(self):
    index_file = os.path.join(self.graph_path, "graph_index.json")
    if (os.path.exists(index_file)):
      os.remove(index_file)


  def test_index_basic(self):
    index = GroumIndex(self.graph_path)

    app_key = "%s/%s/%s" % ("dfredriksen",
                            "stealthmessenger",
                            "d6612b984e9c2eca48bdd73fc7d0d29c242207ff")
    groums = index.get_groums(app_key)
    self.assertTrue(len(groums) == 1)

  def test_update_index(self):
    index = GroumIndex(self.graph_path)

    app_key = "%s/%s/%s" %("GoogleChrome",
                           "chromium-webview-samples",
                           "b18afa96ab6215eed526c19156bf0fe6f5386ad1")

    src_groum_path = os.path.join(self.data_path, "other_graphs",
                              "fullscreenvideosample.android.chrome.google.com.fullscreenvideosample.MainActivity_onNavigationDrawerItemSelected.acdfg.bin")


    dst_dir = os.path.join(self.data_path, "graphs",
                           "GoogleChrome",
                           "chromium-webview-samples",
                           "b18afa96ab6215eed526c19156bf0fe6f5386ad1")
    os.makedirs(dst_dir)
    dst_groum_path = os.path.join(dst_dir,
                                  "fullscreenvideosample.android.chrome.google.com.fullscreenvideosample.MainActivity_onNavigationDrawerItemSelected.acdfg.bin")

    shutil.copyfile(src_groum_path, dst_groum_path)

    try:
      index.process_groum(set(), dst_groum_path)
      groums = index.get_groums(app_key)
      self.assertTrue(len(groums) == 1)
    except:
      raise
    finally:
      os.remove(dst_groum_path)
      os.removedirs(dst_dir)


