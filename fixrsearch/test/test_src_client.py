"""
Test the invocation of the web services

"""

import os
import sys
import logging
import json

try:
  import unittest2 as unittest
except ImportError:
  import unittest


import fixrsearch
from fixrsearch.src_service_client import (
  SrcMethodReq,
  SrcClientService,
  DiffEntry, SourceDiff
)

class TestSrcClient(unittest.TestCase):
  def __init__(self, *args, **kwargs):
    super(TestSrcClient, self).__init__(*args, **kwargs)

  def testPatch(self):
    src_client = SrcClientService("localhost", 8080)

    src_method = SrcMethodReq("https://github.com/square/retrofit",
                              "684f975",
                              "ParameterHandler.java",
                              58,
                              "apply")
    diffs_to_apply = [SourceDiff(
      "+",
      DiffEntry(60, "read", "banana"),
      [DiffEntry(0, "exit", "")])]

    expected_patch = """@java.lang.Override
void apply(retrofit2.RequestBuilder builder, @javax.annotation.Nullable
java.lang.Object value) {
    retrofit2.Utils.checkNotNull(value, "@Url parameter is null.");
    /* [0] After this method method call (read)
    You should invoke the following methods:
    banana
     */
    builder.setRelativeUrl(value);
    // [0] The change should end here (before calling the method exit)
}"""

    expected_path = "retrofit/src/main/java/retrofit2/ParameterHandler.java"

    res = src_client.getPatch(src_method, diffs_to_apply)

    self.assertFalse(res.is_error())
    self.assertTrue(res.get_patch() == expected_patch)
    self.assertTrue(res.get_git_path() == expected_path)
