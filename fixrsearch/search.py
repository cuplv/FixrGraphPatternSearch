"""
Given a GROUM, searches for all the similar patterns
"""

import sys
import os
import optparse
import logging
import json
import tempfile
from threading import Timer
from subprocess import Popen, PIPE
import re
import tempfile

from fixrsearch.index import ClusterIndex
from fixrsearch.groum_index import GroumIndex
from fixrgraph.annotator.protobuf.proto_acdfg_pb2 import Acdfg
from fixrgraph.annotator.protobuf.proto_search_pb2 import SearchResults
from fixrgraph.solr.import_patterns import _get_pattern_key

JSON_OUTPUT = True

MIN_METHODS_IN_COMMON = 2

RESULT_CODE="result_code"
ERROR_MESSAGE="error_messages"
PATTERN_KEY = "pattern_key"
ISO_DOT = "iso_dot"
RESULTS_LIST = "patterns"
OBJ_VAL = "obj_val"
SEARCH_SUCCEEDED_RESULT = 0
ERROR_RESULT = 1


def get_cluster_file(cluster_path):
  return os.path.join(cluster_path, "clusters.txt")

class Search():
  def __init__(self, cluster_path, iso_path, index = None, timeout=10):
    self.cluster_path = cluster_path
    self.iso_path = iso_path
    self.timeout = timeout

    # 1. Build the index
    if (index is None):
      cluster_file = get_cluster_file(cluster_path)
      self.index = ClusterIndex(cluster_file)
    else:
      self.index = index

  def _get_clusters(self, groum_path):
    # 1. Get the method list from the GROUM
    acdfg = Acdfg()
    with open(groum_path,'rb') as fgroum:
      acdfg.ParseFromString(fgroum.read())
      method_list = []
      for method_node in acdfg.method_node:
        std_str = str(method_node.name)

        method_list.append(std_str)
      fgroum.close()

    # 2. Search the clusters
    clusters = self.index.get_clusters(method_list, MIN_METHODS_IN_COMMON)

    return clusters

  def search_from_groum(self, groum_path):
    logging.info("Search for groum %s" % groum_path)

    # 1. Search the clusters
    clusters = self._get_clusters(groum_path)

    # 2. Search the clusters
    results = []
    for cluster_info in clusters:
      logging.debug("Searching in cluster %d (%s)..." % (cluster_info.id,
                                                         ",".join(cluster_info.methods_list)))

      results_cluster = self.search_cluster(groum_path, cluster_info)
      if results_cluster is None:
        logging.debug("Found 0 in cluster %d..." % cluster_info.id)
      else:
        logging.debug("Found %d in cluster %d..." % (len(results_cluster),
                                                     cluster_info.id))
        cluster_info_map = {}
        cluster_info_map["id"] = cluster_info.id
        cluster_info_map["methods_list"] = [n for n in
                                            cluster_info.methods_list]
        results_cluster["cluster_info"] = cluster_info_map

        results.append(results_cluster)

    # 3. sort results by popularity
    def mysort(res_list):
      if "search_results" in res_list:
        if len(res_list["search_results"]) > 0:
          elem = res_list["search_results"][0]

          if "popular" in elem:
            return elem["popular"]["frequency"]
          if "anomalous" in elem:
            return elem["anomalous"]["frequency"]

      return 0

    results = sorted(results, key=lambda res: mysort(res), reverse=True)
    return results


  def search_cluster(self, groum_path, cluster_info):
    """
    Search for similarities and anomalies inside a single lattice
    """
    current_path = os.path.join(self.cluster_path,
                                "all_clusters",
                                "cluster_%d" % cluster_info.id)
    lattice_path = os.path.join(current_path,
                                "cluster_%d_lattice.bin" % cluster_info.id)

    if (os.path.exists(lattice_path)):
      logging.debug("Searching lattice %s..." % lattice_path)
      result = self.call_iso(groum_path, lattice_path)
    else:
      logging.debug("Lattice file %s not found" % lattice_path)
      result = None

    return result


  def call_iso(self, groum_path, lattice_path):
    """
    Search the element in the lattice that are similar to the groum
    """
    search_file, search_path = tempfile.mkstemp(suffix=".bin",
                                                prefix="search_res",
                                                text=True)
    os.close(search_file)

    args = [self.iso_path,
            "-q", groum_path,
            "-l", lattice_path,
            "-o", search_path]
    logging.debug("Command line %s" % " ".join(args))

    # Kill the process after the timout expired
    def kill_function(p, cmd):
      logging.info("Execution timed out executing %s" % (cmd))
      p.kill()

    # proc = subprocess.Popen(args, stdout=out, stderr=err, cwd=None)
    proc = Popen(args, cwd=None, stdout=PIPE,  stderr=PIPE)
    timer = Timer(self.timeout, kill_function, [proc, "".join(args)])
    try:
      timer.start()
      (stdout, stderr) = proc.communicate() # execute the process
    except Exception as e:
      logging.error(e.message)
    finally:
      timer.cancel() # Cancel the timer, no matter what

    result = None
    return_code = proc.returncode
    if (return_code != 0):
      err_msg = "Error code is %s\nCommand line is: " \
                "%s\n%s" % (str(return_code), str(" ".join(args)),"\n")
      logging.error("Error executing %s\n%s" % (" ".join(args), err_msg))

      # result = TODO_ERROR

    else:
      logging.info("Search finished...")

      result = self.formatOutput(search_path)

    if os.path.isfile(search_path):
      os.remove(search_path)

    return result


  def get_res_type(self, proto_search_type):
    if (proto_search_type == SearchResults.SearchResult.CORRECT):
      res_type = "CORRECT"
      subsumes_ref = True
      subsumes_anom = True
    elif (proto_search_type ==
          SearchResults.SearchResult.CORRECT_SUBSUMED):
      res_type = "CORRECT_SUBSUMED"
      subsumes_ref = False
      subsumes_anom = True
    elif (proto_search_type ==
          SearchResults.SearchResult.ANOMALOUS_SUBSUMED):
      res_type = "ANOMALOUS_SUBSUMED"
      subsumes_ref = False
      subsumes_anom = False
    elif (proto_search_type ==
          SearchResults.SearchResult.ISOLATED_SUBSUMED):
      res_type = "ISOLATED_SUBSUMED"
      subsumes_ref = True
      subsumes_anom = False
    elif (proto_search_type ==
          SearchResults.SearchResult.ISOLATED_SUBSUMING):
      res_type = "ISOLATED_SUBSUMING"
      subsumes_anom = False
    else:
      res_type = None
      subsumes_ref = True
      subsumes_anom = True

    return (res_type, subsumes_ref, subsumes_anom)


  def formatOutput(self, search_path):
    """
    Read the results from the search and produce the json output
    """
    logging.debug("Formatting output...")

    results = {}

    proto_results = SearchResults()
    with open(search_path,'rb') as fsearch:
      proto_results.ParseFromString(fsearch.read())
      fsearch.close()

    # Read the method names
    proto_lattice = proto_results.lattice
    method_names = []
    for proto_name in proto_lattice.method_names:
      method_names.append(proto_name)
      results["method_names"] = method_names

    # Map from id of the bin to bin representation
    id2bin = {}
    for acdfbBin in proto_lattice.bins:
      assert not acdfbBin.id in id2bin
      id2bin[acdfbBin.id] = acdfbBin

    # Process each single result
    search_res_list = []
    for proto_search in proto_results.results:
      logging.debug("Processing proto search...")

      search_res = {}

      # Get the type of the pattern
      (res_type, subsumes_ref, subsume_anom) = self.get_res_type(proto_search.type)
      search_res["type"] = res_type
      logging.debug("Search res: " + search_res["type"])

      # print("Lines iso to reference %d" %
      #       len(proto_search.isoToReference.acdfg_1.node_lines))

      # Process the reference pattern, and set it as
      # popular key in the result
      bin_id = proto_search.referencePatternId
      bin_res = self.format_bin(proto_results.lattice,
                                id2bin,
                                id2bin[bin_id],
                                proto_search.isoToReference,
                                subsumes_ref)
      search_res["popular"] = bin_res

      # Process the results that have an anomalous pattern
      # and a map showing how to transform the pattern in the
      # popular one
      if (proto_search.HasField("anomalousPatternId") and
          proto_search.HasField("isoToAnomalous")):
        bin_id = proto_search_res.anomalousPatternId
        bin_res = self.format_bin(proto_results.lattice,
                                  id2bin,
                                  id2bin[bin_id],
                                  proto_search.isoToAnomalous,
                                  subsumes_ref)
        search_res["anomalous"] = bin_res

      search_res_list.append(search_res)

    if len(search_res_list) == 0:
      results = None
    else:
      # order the set of results wrt the popular pattern representing the bin
      search_res_list = sorted(search_res_list,
                               key=lambda res: res["popular"]["frequency"] if "popular" in res else (res["anomalous"]["frequency"] if "anomalous" in res else 0),
                               reverse=True)

      results["search_results"] = search_res_list

    return results

  def get_popularity(self, lattice, id2bin, acdfg_bin):
    """
    Get the popular measure exploring the lattice
    """

    visited = set()
    subsumed = [acdfg_bin]
    popularity = 0
    while (len(subsumed) != 0):
      current = subsumed.pop()
      if current.id in visited:
        continue

      popularity = popularity + len(current.names_to_iso)

      for binId in current.subsuming_bins:
        subsumed.append(id2bin[binId])

      visited.add(current.id)

    return popularity


  def format_bin(self, lattice, id2bin, acdfgBin, isoRes, subsumes):
    """
    Format one of the result of the search --- i.e. a relation from a
    pattern (either popular/anomalous/isolated) to the groum used in the
    search.

    The input are:
    - the lattice used for the search
    - the map from id of the bin to the bin protobuf
    - the acdfg representative for the bin to format
    - the isomorphism relation from the groum to the representative of the bin
    - a boolean flag that is true iff the groum subsumes the bin

    The output is a map containing:
      - type: popular/anomalous/isolated
      - frequency: the popularity of the bin in the lattice
      - acdfg_mappings: a list of mappings, one for each groum in the bin.
      A mapping maps nodes and edges from the analyzed groum to a groum in the
      bin.
      A mapping contains two maps, one for nodes and the other for edges.
      Each map maps a list of nodes that are isomorphic, added from one graph
      to the other, or removed from one graph to the other.
    """
    res_bin = {}

    if (acdfgBin.popular):
      res_bin["type"] = "popular"
    elif (acdfgBin.anomalous):
      res_bin["type"] = "anomalous"
    elif (acdfgBin.isolated):
      res_bin["type"] = "isolated"

    res_bin["frequency"] = self.get_popularity(lattice, id2bin, acdfgBin)
    res_bin["cardinality"] = len(acdfgBin.names_to_iso)

    # Creates three lists of lines association between
    # the query acdf and all the other acdfgs in the
    # pattern
    acdfg_mappings = []
    visitedMapping = set()
    for isoPair in acdfgBin.names_to_iso:
      mapping = {}
      source_info = {}
      if (isoPair.iso.acdfg_1.HasField("source_info")):
        protoSource = isoPair.iso.acdfg_1.source_info
        if (protoSource.HasField("package_name")):
          source_info["package_name"] = protoSource.package_name
        if (protoSource.HasField("class_name")):
          source_info["class_name"] = protoSource.class_name
        if (protoSource.HasField("method_name")):
          source_info["method_name"] = protoSource.method_name
        if (protoSource.HasField("class_line_number")):
          source_info["class_line_number"] = protoSource.class_line_number
        if (protoSource.HasField("method_line_number")):
          source_info["method_line_number"] = protoSource.method_line_number
        if (protoSource.HasField("source_class_name")):
          source_info["source_class_name"] = protoSource.source_class_name
        if (protoSource.HasField("abs_source_class_name")):
          source_info["abs_source_class_name"] = protoSource.abs_source_class_name
          mapping["source_info"] = source_info

      repo_tag = {}
      if (isoPair.iso.acdfg_1.HasField("repo_tag")):
        proto_tag = isoPair.iso.acdfg_1.repo_tag
        if proto_tag.HasField("repo_name"):
          repo_tag["repo_name"] = proto_tag.repo_name
        if proto_tag.HasField("user_name"):
          repo_tag["user_name"] = proto_tag.user_name
        if proto_tag.HasField("url"):
          repo_tag["url"] = proto_tag.url
        if proto_tag.HasField("commit_hash"):
          repo_tag["commit_hash"] = proto_tag.commit_hash
        if proto_tag.HasField("commit_date"):
          repo_tag["commit_date"] = proto_tag.commit_date
        mapping["repo_tag"] = repo_tag

      # remove duplicates
      key = "%s/%s/%s/%s/%s/%s" % (repo_tag["user_name"],
                                   repo_tag["repo_name"],
                                   repo_tag["commit_hash"],
                                   source_info["class_name"],
                                   source_info["method_name"],
                                   source_info["method_line_number"])

      if key in visitedMapping:
        continue
      visitedMapping.add(key)

      # Computes the mapping from the acdfg used in the
      # query and the acdfg in the bin
      # logging.debug("Computing mapping...")
      # logging.debug("%d" % len(isoRes.nodesMap))
      # logging.debug("%d" % len(isoPair.iso.nodesMap))
      (nodes_res, edges_res) = Search.get_mapping(isoRes.acdfg_1,
                                                  isoPair.iso.acdfg_1,
                                                  isoRes,
                                                  isoPair.iso,
                                                  # Never reverse, the data is already ok
                                                  False)
      mapping["nodes"] = {"iso" : nodes_res[0],
                          "add" : nodes_res[1],
                          "remove" : nodes_res[2]}
      mapping["edges"] = {"iso" : edges_res[0],
                          "add" : edges_res[1],
                          "remove" : edges_res[2]}
      acdfg_mappings.append(mapping)

    res_bin["acdfg_mappings"] = acdfg_mappings

    return res_bin


  @staticmethod
  def get_mapping(acdfg_1, acdfg_2,
                  isorel_1_ref, isorel_2_ref,
                  reverse_1=False):
    """ acdfg_1 and acdfg_2 are two (protobuffer) acdfg,

    isorel_1_ref the unweightediso protobuf from acdfg_1 to
    the reference groum

    isorel_2_ref the unweightediso protobuf from acdfg_2 to
    the reference groum

    reverse is True if isorel_1_ref contains pairs
    from ref to acdfg_1.
    """
    def get_all(id2num, lists):
      res = []
      for l in lists:
        for elem in l:
          elem_id = elem.id
          if elem_id in id2num:
            line_no =id2num[elem_id]
            res.append((elem_id, line_no))
      return res

    def get_nodes(acdfg):
      id2num = {}
      for line_num in acdfg.node_lines:
        id2num[line_num.id] = line_num.line

      # logging.error("Node lines " + str(id2num))

      return get_all(id2num,
                     [acdfg.data_node,
                      acdfg.misc_node,
                      acdfg.method_node])

    def get_edges(acdfg):
      return get_all({},
                     [acdfg.def_edge, acdfg.use_edge,
                      acdfg.trans_edge])

    # 1. Remap the maps of nodes and edges to be from
    # acdfg_1 to acdfg_2 (it is a join on the id of ref!)
    nodes_1_to_2 = {}
    # edges_1_to_2 = {}
    # for (my, iso_1_ref, iso_2_ref) in zip([nodes_1_to_2, edges_1_to_2],
    #                                       [isorel_1_ref.nodesMap, isorel_1_ref.edgesMap],
    #                                       [isorel_2_ref.nodesMap, isorel_2_ref.edgesMap]):
    for (my, iso_1_ref, iso_2_ref) in zip([nodes_1_to_2],
                                          [isorel_1_ref.nodesMap],
                                          [isorel_2_ref.nodesMap]):
      if not reverse_1:
        ref_dst = [pair.id_1 for pair in isorel_1_ref.nodesMap]
      else:
        ref_dst = [pair.id_2 for pair in isorel_1_ref.nodesMap]

      # Build a map from elements in ref to elements in acdfg_2
      map_ref_2 = {}
      for pair in iso_2_ref:
        if pair.id_2 in map_ref_2:
          logging.debug("%d is mapped to multiple nodes!" % pair.id_2)
        map_ref_2[pair.id_2] = pair.id_1

      # Build my from elements in 1 to elements in 2
      for pair in iso_1_ref:
        if not reverse_1:
          (el_1,el_2) = (pair.id_1, pair.id_2)
        else:
          (el_1,el_2) = (pair.id_2, pair.id_1)

        if el_2 in map_ref_2:
          my[el_1] = map_ref_2[el_2]
        else:
          logging.debug("%d is not mapped!" % el_2)


    # logging.debug("Map " + str(nodes_1_to_2))

    # Compute the common, added, and removed lines
    idx_iso = 0
    idx_to_add = 1
    idx_to_remove = 2

    nodes_res = ([],[],[])
    edges_res = ([],[],[])
    nodes_lists = (get_nodes(acdfg_1), get_nodes(acdfg_2))
    # edges_lists = (get_edges(acdfg_1), get_edges(acdfg_2))

    # logging.debug("Nodes acdfg1 " + str(nodes_lists[0]))
    # logging.debug("Nodes acdfg2 " + str(nodes_lists[1]))

    # for (res, elem_1_to_2, elem_lists) in zip([nodes_res, edges_res],
    #                                           [nodes_1_to_2, edges_1_to_2],
    #                                           [nodes_lists, edges_lists]):
    for (res, elem_1_to_2, elem_lists) in zip([nodes_res],
                                              [nodes_1_to_2],
                                              [nodes_lists]):
      elem_list_1 = elem_lists[0]
      elem_list_2 = elem_lists[1]

      id_to_line_no_2 = {} # From elem id of acdfg 2 to line numbers
      elem_2_to_1 = {}
      for (e1, e2) in elem_1_to_2.iteritems(): elem_2_to_1[e2] = e1
      for (e2_id, e2_line) in elem_list_2:
        if e2_id in elem_2_to_1:
          e1_id = elem_2_to_1[e2_id]
          id_to_line_no_2[e1_id] = e2_line
        else:
          res[idx_to_add].append(e2_line)

      for (e1_id, e1_line) in elem_list_1:
        if e1_id in id_to_line_no_2:
          res[idx_iso].append((e1_line, id_to_line_no_2[e1_id]))
        else:
          res[idx_to_remove].append(e1_line)

    return (nodes_res, edges_res)


def main():
  logging.basicConfig(level=logging.DEBUG)

  p = optparse.OptionParser()
  p.add_option('-g', '--groum', help="Path to the GROUM file to search")

  p.add_option('-d', '--graph_dir', help="Base path containing the graphs")
  p.add_option('-u', '--user', help="Username")
  p.add_option('-r', '--repo', help="Repo name")
  p.add_option('-z', '--hash', help="Hash number")
  p.add_option('-m', '--method', help="Fully qualified method name")
  p.add_option('-l', '--line', help="Line number of the method")

  p.add_option('-c', '--cluster_path', help="Base path to the cluster directory")
  p.add_option('-i', '--iso_path', help="Path to the isomorphism computation")

  def usage(msg=""):
    if JSON_OUTPUT:
      result = {RESULT_CODE : ERROR_RESULT,
                ERROR_MESSAGE: msg,
                RESULTS_LIST : []}
      json.dump(result,sys.stdout)
      sys.exit(0)
    else:
      if msg:
        print "----%s----\n" % msg
        p.print_help()
        print "Example of usage %s" % ("python search.py "
                                       "-g groum.acdfg.bin"
                                       "-c /extractionpath/clusters",
                                       "-i /home/sergio/works/projects/muse/repos/FixrGraphIso/build/src/fixrgraphiso")
      sys.exit(1)

  opts, args = p.parse_args()

  use_groum_file = False
  if (not opts.groum):
    if (not opts.graph_dir): usage("Graph dir not provided!")
    if (not os.path.isdir(opts.graph_dir)):
      usage("%s does not exist!" % opts.graph_dir)
    if (not opts.user): usage("User not provided")
    if (not opts.hash): usage("Hash not provided")
    if (not opts.repo): usage("Repo not provided")
    if (not opts.method): usage("Method not provided")
    if (not opts.line): usage("Line not provided")
  else:
    use_groum_file = True
    if (not os.path.isfile(opts.groum)):
      usage("GROUM file %s does not exist!" % opts.groum)
  if (not opts.cluster_path):
    usage("Cluster path not provided!")
  if (not os.path.isdir(opts.cluster_path)):
    usage("Cluster path %s does not exist!" % (opts.cluster_path))
  if (not opts.iso_path): usage("Iso executable not provided!")
  if (not os.path.isfile(opts.iso_path)):
    usage("Iso executable %s does not exist!" % opts.iso_path)

  if use_groum_file:
    groum_file = opts.groum
  else:
    groum_index = GroumIndex(opts.graph_dir)
    key = groum_index.get_groum_key(opts.user, opts.repo, opts.hash,
                                    opts.method, opts.line)

    groum_file = groum_index.get_groum_path(key)
    if groum_file is None:
      usage("Cannot find groum for %s" % key)

  search = Search(opts.cluster_path, opts.iso_path)
  results = search.search_from_groum(groum_file)

  result = {RESULT_CODE : SEARCH_SUCCEEDED_RESULT,
            RESULTS_LIST : results}
  json.dump(result,sys.stdout)


if __name__ == '__main__':
  main()

