"""
Search script from command line.

The search script allow to perform a search from the command line.

The search script takes as input a single groum or an apk file and returns a set
of results in json format.

[Still in progress]
The search script is flexible and it allows to:
- Choose between a local and a remote search.
- Choose between using the source files or not.
"""

import optparse
import logging
import os
import sys
import json
import tempfile
import shutil

from fixrsearch.search import Search
from fixrsearch.groum_index import GroumIndexBase, GroumIndex
from fixrsearch.anomaly import AnomalyEncoder

from fixrsearch.search_script.utils import (
  extract_apk, to_html, get_java_files,
  get_src_archive_zip)
from fixrsearch.utils import CommitRef, RepoRef
from fixrsearch.process_pr import PrProcessor
from fixrsearch.src_service_client import SrcClientMock, SrcClientService

import fixrgraph.wireprotocol.search_service_wire_protocol as wp

def parse_args():
  p = optparse.OptionParser()
  p.add_option('-g', '--groum', help="Path to the GROUM file to search")

  p.add_option('-a', '--apk', help="Path to the apk file to search")
  p.add_option('-s', '--source_code', help="Path to the apk source code")

  p.add_option('-d', '--graphs_path', help="Path containing the graphs used to mine the patterns")
  p.add_option('-c', '--clusters_path', help="Path to the mined clusters")
  p.add_option('-e', '--graph_extractor_jar', help="Path to the graph extractor")

  p.add_option('-i', '--search_lattice_path', help="Path to the search_lattice executable")
  p.add_option('-t', '--timeout', help="Timeout to stop the search on a cluster")

  p.add_option('-o', '--output', help="Path of the output file to print the results")
  p.add_option('-p', '--html_output', help="Path of the output file in html")

  def usage(msg=""):
    if msg:
        print("----%s----\n" % msg)
        p.print_help()

    print("Example of usage %s" % ("python search_script.py "
                                   "-g groum.acdfg.bin "
                                   "-d /extractionpath/graphs "
                                   "-c /extractionpath/clusters "
                                   "-i search_lattice "
                                   "-o output.json "
                                   "-p output.html"))
    sys.exit(1)

  opts, args = p.parse_args()

  use_groum_file = False
  use_apk = False
  input_file = None
  graphs_path = None
  cluster_path = None
  search_lattice_path = None
  timeout = None
  output_file = None
  html_output = None
  source_code_path = None
  graph_extractor_jar = None

  if (opts.groum):
    if (opts.apk):
      usage("You cannot provide both a groum and a apk file")
    use_groum_file = True
    input_file = os.path.abspath(opts.groum)
    if (not os.path.isfile(input_file)):
      usage("The provided groum file %s does not exist!" % input_file)
  elif (opts.apk):
    if (opts.groum):
      usage("You cannot provide both a groum and a apk file")
    use_apk = True
    input_file = os.path.abspath(opts.apk)
    if (not os.path.isfile(input_file)):
      usage("The provided apk file %s does not exist!" % input_file)
  else:
    usage("You have to provide either a groum file or an apk file!")

  assert ((use_apk and not use_groum_file) or
          (not use_apk and use_groum_file))

  if (not opts.graphs_path):
    usage("Graphs path not provided!")
  graphs_path = os.path.abspath(opts.graphs_path)
  if (not opts.clusters_path):
    usage("Cluster path not provided!")
  clusters_path = os.path.abspath(opts.clusters_path)
  if (not opts.search_lattice_path):
    usage("Iso executable not provided!")
  search_lattice_path = os.path.abspath(opts.search_lattice_path)
  if (not opts.output):
    usage ("Did not provide an output file")
  output_file = os.path.abspath(opts.output)
  if (opts.html_output):
    html_output = opts.html_output
  if (opts.source_code):
    source_code_path = os.path.abspath(opts.source_code)
    if not os.path.isdir(source_code_path):
      usage("%s dir does not exists!" % source_code_path)

  for d in [graphs_path,clusters_path]:
    if not os.path.isdir(d):
      usage("%s dir does not exists!" % d)

  if (use_apk):
    if not opts.graph_extractor_jar:
      usage("You need to provide the path to the graph extractor when using "
            "apks.")
    else:
      graph_extractor_jar = opts.graph_extractor_jar

  files = [search_lattice_path]
  if use_apk: files.append(graph_extractor_jar)
  for f in files:
    if (not os.path.isfile(f)):
      usage("%s file does not exist!" % f)

  if opts.timeout:
    try:
      timeout = int(opts.timeout)
    except ValueError:
      usage("Timeout %s is not an integer value" % opts.timeout)
  else:
    # a week of computation, technically unbounded
    timeout = 604800


  return (use_groum_file,
          use_apk,
          input_file,
          graphs_path,
          clusters_path,
          search_lattice_path,
          graph_extractor_jar,
          timeout,
          output_file,
          html_output,
          source_code_path)


def main():
  logging.basicConfig(level=logging.DEBUG)
  logger = logging.getLogger(__name__)

  # Parse the data
  args_res = parse_args()
  (use_groum_file,
   use_apk,
   input_file,
   graphs_path,
   clusters_path,
   search_lattice_path,
   graph_extractor_jar,
   timeout,
   output_file,
   html_output,
   source_code_path) = args_res

  # Creates the search object
  search = Search(clusters_path, search_lattice_path,
                  None, GroumIndex(graphs_path), timeout)
  src_client = SrcClientMock()
  src_client = SrcClientService("localhost", "8080")

  # Search the Groums
  anomalies = None
  commit_ref = CommitRef(RepoRef("temporary_search", "cuplv"), "0")
  if use_groum_file:
    # results = search.search_from_groum(input_file, False, None)
    index = GroumIndexBase(os.path.dirname(input_file))
    index.process_groum(set(), input_file)
    pr_processor = PrProcessor(index, search, src_client)
    anomalies = pr_processor.process_graphs_from_commit(commit_ref, None, None)
  elif use_apk:
    graphs_zip_file = tempfile.NamedTemporaryFile()
    src_zip = tempfile.NamedTemporaryFile()
    src_path = tempfile.mkdtemp()
    graphs_path = tempfile.mkdtemp()

    try:
      source_code_list = get_java_files(source_code_path)
      graphs_zip_name = graphs_zip_file.name
      graphs_zip_name_res = extract_apk(input_file,
                                        source_code_list,
                                        graph_extractor_jar,
                                        graphs_zip_name,
                                        commit_ref.repo_ref.user_name,
                                        commit_ref.repo_ref.repo_name,
                                        commit_ref.commit_hash)
      if graphs_zip_name_res is None:
        logging.debug("Error in the extraction of the grapsh from the APKs")
        print("Error in the extraction of the grapsh from the APKs")
        sys.exit(1)
      assert graphs_zip_name == graphs_zip_name_res

      # Call the search
      logging.debug("Decompressing the graphs in %s" % graphs_path)
      wp.decompress(graphs_zip_name, graphs_path)

      if not source_code_path is None:
        get_src_archive_zip(src_zip.name, source_code_path,
                            source_code_list)
      wp.decompress(src_zip.name, src_path)

      index = GroumIndexBase(graphs_path)
      index.build_index()
      pr_processor = PrProcessor(index, search, src_client)
      anomalies = pr_processor.process_graphs_from_commit(None,
                                                          None,
                                                          src_path)
    finally:
      shutil.rmtree(graphs_path)
      shutil.rmtree(src_path)
      src_zip.close()
      graphs_zip_file.close()

  # Prints the results
  if not anomalies is None:
    # Saves the anomalies on the output file
    print("Found %s anomalies" % len(anomalies))

    for a in anomalies:
      new = a.pattern_text.replace("\n","</BR>")
      a.pattern_text = new

    anomalies_json = json.dumps(anomalies, cls=AnomalyEncoder)
    with open(output_file, 'w') as f:
      json.dump(anomalies_json, f)

    if not html_output is None:
      print("Printing to file %s" % html_output)
      html_text = to_html(anomalies_json)
      with open(html_output, 'w') as f:
        f.write(html_text)

if __name__ == '__main__':
  main()
