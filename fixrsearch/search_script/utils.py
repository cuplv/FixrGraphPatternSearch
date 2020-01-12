"""
Utility functions used to implement the command line search tool.
"""

import logging
import os
import sys
import tempfile
import shutil
from json2html import *
from io import StringIO

from fixrgraph.extraction.extract_single import BuildInfoApk
from fixrgraph.extraction.run_extractor import RepoProcessor
import fixrgraph.wireprotocol.search_service_wire_protocol as wp

def extract_apk(apk_path,
                graph_extractor_jar_path,
                output_zip,
                username = "cuplv",
                repo = "temporary_search",
                commit_hash="0"):
  """
  Extracts the graphs from the APK and saves them in a zip file.
  Returns the path to the zip file or None

  [TODO] Refactor with muse APIs.
  """

  logger = logging.getLogger(__name__)
  tmp_out = tempfile.mkdtemp()
  try:
    # Extract the graphs for the APK
    logger.info("Extracting the graphs from the APK %s" % apk_path)
    tmp_graphs_out = os.path.join(tmp_out, "graphs")
    tmp_provenance_out = os.path.join(tmp_out, "provenance")
    processed = RepoProcessor.extract_static_apk(repo,
                                                 None,
                                                 os.environ['ANDROID_HOME'],
                                                 tmp_graphs_out,
                                                 tmp_provenance_out,
                                                 graph_extractor_jar_path,
                                                 BuildInfoApk(apk_path),
                                                 os.path.dirname(apk_path))
    if processed is None:
      raise Exception("Processing of %s failed!" % str(repo))

    # Compressing the file
    logger.info("Compressing the graphs to %s" % output_zip)
    wp.compress(tmp_graphs_out, output_zip)
    return output_zip
  except Exception as e:
    logger.error(str(e))
    return None
  finally:
    shutil.rmtree(tmp_out)
    pass

def to_json(anomaly):
  json_anomaly = {"id" : anomaly.numeric_id,
                  "error" : anomaly.description,
                  "packageName" : anomaly.method_ref.package_name,
                  "className" : anomaly.method_ref.class_name,
                  "methodName" : anomaly.method_ref.method_name,
                  "fileName" : anomaly.git_path,
                  "line" : anomaly.method_ref.start_line_number,
                  "pattern" : anomaly.pattern_text,
                  "patch" : anomaly.patch_text}
  return json_anomaly

def to_html(anomalies):
  return json2html.convert(json = anomalies)
