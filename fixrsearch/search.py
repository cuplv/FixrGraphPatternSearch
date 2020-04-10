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

from fixrsearch.codegen.acdfg_repr import AcdfgRepr
from fixrsearch.codegen.mappings import Mappings, LineNum
from fixrsearch.codegen.diff import AcdfgPatch, AcdfgDiff
from fixrsearch.codegen.generator import CodeGenerator, CFGAnalyzer

from fixrgraph.pipeline.pipeline import Pipeline

def get_cluster_file(cluster_path):
  return os.path.join(cluster_path, "clusters.txt")

def get_duplicate_file(cluster_path):
  return os.path.join(cluster_path,
                      Pipeline.PATTERN_DUPLICATES)

def get_duplicate_file(cluster_path):
  return os.path.join(cluster_path,
                      Pipeline.PATTERN_DUPLICATES)


class DuplicateMap():
  def __init__(self, duplicate_files):
    self.duplicate_map = {}

    with open(duplicate_files, "r") as f:
      for line in f.readlines():
        line = line.strip()
        c1,id1,c2,id2 = line.split(",")
        p1 = (c1,id1)
        p2 = (c2,id2)

        # merge sets
        if p1 in self.duplicate_map:
          s1 = self.duplicate_map[p1]
        else:
          s1 = set(p1)
          self.duplicate_map[p1] = s1
        s2 = self.duplicate_map if p2 in self.duplicate_map else set(p2)
        s1 = s1.update(s2)
        for p_in_s2 in s2:
          self.duplicate_map[p_in_s2] = s1

  def find_set(self, pattern_id):
    if not pattern_id in self.duplicate_map:
      return {pattern_id}
    else:
      return self.duplicate_map[pattern_id]

  def remove_duplicates(self, results):
    visited_id = {}
    new_results = []
    total = 0
    new = 0
    for cluster_res in results:
      assert "cluster_info" in cluster_res
      cluster_id = cluster_res["cluster_info"]["id"]

      added = {}
      added["cluster_info"] = cluster_res["cluster_info"]

      added["search_results"] = []
      new_results.append(added)
      for elem in cluster_res["search_results"]:
        total += 1
        bin_res = elem["popular"]
        bin_id = int(bin_res["id"])
        pattern_id = (cluster_id, bin_id)

        if not pattern_id in visited_id:
          visited = self.find_set(pattern_id)
          visited_id.update(visited)
          added["search_results"].append(elem)
          new += 1

    logging.info("Filtering from %d to %d" % (total,new))

    return new_results


class PatternFilters:

  @staticmethod
  def get_from_blacklist(cluster_path):
    pf = PatternFilters()
    pf.__fill__(cluster_path)
    return pf

  def __init__(self):
    self.blacklist = {}

  def __fill__(self, cluster_path):
    # ClusterId (Int) -> List[PatternId(int)]
    # if the list is empty then we cut all the patterns in the
    # cluster
    self.blacklist = {}

    # Read the blacklist
    try:
      blacklist_file = os.path.join(cluster_path, "blacklist.json")
      with open(blacklist_file, "r") as f:
        data = json.load(f)

        for d in data:
          cluster_id = int(d["id"])


          patterns = []
          for pattern_id in d["patterns"]:
            patterns.append(int(pattern_id))

          if (len(patterns) == 0):
            logging.info("Will skip cluster id %d" % cluster_id)

          self.blacklist[cluster_id] = list(patterns)
    except Exception as e:
      logging.error(e.message)
      logging.error("Cannot read blacklist")

  def has_all_cluster(self, cluster_id):
    return (cluster_id in self.blacklist and
            0 == len(self.blacklist[cluster_id]))

  def has_pattern(self, cluster_id, pattern_id):
    return (cluster_id in self.blacklist and
            pattern_id in self.blacklist[cluster_id])


class Search():
  def __init__(self, cluster_path, search_lattice_path,
               index = None, groum_index = None,
               timeout=10, min_methods_in_common = 1,
               avoid_duplicates = True,
               use_blacklist = True):
    """
    Constructs the search object:

    - cluster_path: path to the mined clusters
    - search_lattice_path: path to the search_lattice executable
    - timeout: timeout to search for a match in each cluster
    - groum_index: index of groums used to mine the clusters
    - min_methods_in_common: minimum number of methods in common between
      the groum and the cluster to search for
    - avoid_duplicates: avoids the duplicate patterns (need to build the
      duplicate clusters
    - use_blacklist: use the list of blacklisted cluster/patterns
    """
    self.cluster_path = cluster_path
    self.search_lattice_path = search_lattice_path
    self.timeout = timeout
    self.groum_index = groum_index
    self.min_methods_in_common = min_methods_in_common
    self.avoid_duplicates = avoid_duplicates
    self.use_blacklist = use_blacklist

    # 1. Build the index
    if (index is None):
      cluster_file = get_cluster_file(cluster_path)
      self.index = ClusterIndex(cluster_file)
    else:
      self.index = index

    if avoid_duplicates:
      self.duplicate_map = DuplicateMap(get_duplicate_file(cluster_path))
    else:
      self.duplicate_map = None

    if use_blacklist:
      self.blacklist = PatternFilters.get_from_blacklist(cluster_path)
    else:
      self.blacklist = PatternFilters()

  def _get_clusters(self, groum_path):
    # 1. Get the method list from the GROUM
    acdfg = Acdfg()
    with open(groum_path,'rb') as fgroum:
      acdfg.ParseFromString(fgroum.read())
      method_list = []
      for method_node in acdfg.method_node:
        std_str = str(method_node.name)
        if not std_str in {"is_true",
                           "is_false",
                           "EQ",
                           "NEQ",
                           "GE",
                           "GT",
                           "LE",
                           "LT",
                           "NOT",
                           "AND",
                           "OR",
                           "XOR"}:
          method_list.append(std_str)
      fgroum.close()

    # 2. Search the clusters
    clusters = self.index.get_clusters(method_list, self.min_methods_in_common)

    new_clusters = []
    for cluster_info in clusters:
      new_clusters.append(cluster_info)

    logging.debug("Keys: %s" %
                  ",".join([str(method_name) for method_name in method_list]))

    logging.debug("Found clusters: %s" %
                  ",".join([str(cluster_info.id) for cluster_info in clusters]))

    return new_clusters

  def search_from_groum(self, groum_path,
                        filter_for_bugs = False,
                        filter_cluster = None):
    """
    Searching patterns that are similar to the groum in groum_path.

    - groum_path: path to the groum file
    - filter_for_bugs: If true only return anomalous_subsumed or correct_subsumed patterns.
    That'is, it returns the pattern that entirely contains the groum.
    - filter_cluster: id of clusters to NOT consider in the search
    """
    logging.info("Search for groum %s" % groum_path)

    # 1. Search the clusters
    clusters = self._get_clusters(groum_path)

    # 2. Search the clusters
    results = []
    for cluster_info in clusters:
      logging.debug("Searching in cluster %d (%s)..." % (cluster_info.id,
                                                         ",".join(cluster_info.methods_list)))

      if ((not filter_cluster is None) and
          (not cluster_info.id in filter_cluster)):
        logging.debug("Filtered out cluster %s", cluster_info.id)
        continue

      if  (self.blacklist.has_all_cluster(int(cluster_info.id))):
        logging.debug("Skipping blacklisted cluster %s....", cluster_info.id)
        continue

      results_cluster = self.search_cluster(groum_path, cluster_info,
                                            filter_for_bugs)
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

    if (not self.duplicate_map is None):
      results = self.duplicate_map.remove_duplicates(results)

    return results


  def search_cluster(self, groum_path, cluster_info,
                     filter_for_bugs = False):
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
      result = self.call_iso(groum_path, lattice_path,
                             int(cluster_info.id),
                             filter_for_bugs)
    else:
      logging.debug("Lattice file %s not found" % lattice_path)
      result = None

    return result


  def call_iso(self, groum_path, lattice_path,
               cluster_id,
               filter_for_bugs = False):
    """
    Search the element in the lattice that are similar to the groum
    """
    search_file, search_path = tempfile.mkstemp(suffix=".bin",
                                                prefix="search_res",
                                                text=True)
    os.close(search_file)

    args = [self.search_lattice_path,
            "-q", groum_path,
            "-l", lattice_path,
            "-o", search_path]
    logging.debug("Command line %s" % " ".join(args))

    # Kill the process after the timout expired
    def kill_function(p, cmd):
      logging.info("Execution timed out executing %s" % (cmd))
      p.kill()

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

      result = self.formatOutput(search_path, cluster_id, filter_for_bugs)

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


  def formatOutput(self, search_path, cluster_id, filter_for_bugs=False):
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

      # Just show ANOMALOUS_SUBSUMED patterns
      # anomaly_categories = ["ANOMALOUS_SUBSUMED", "CORRECT_SUBSUMED"]
      anomaly_categories = ["ANOMALOUS_SUBSUMED"]
      if (filter_for_bugs and (not res_type in anomaly_categories)):
        logging.info("Filtering cluster (not anomalous or correct subsumed)")
        continue

      # check if the pattern is blacklisted
      bin_id = proto_search.referencePatternId
      if (self.blacklist.has_pattern(cluster_id, int(bin_id))):
        logging.info("Filtering blacklisted pattern %d %d..." % (int(cluster_id),
                                                                 int(bin_id)))
        continue

      # Process the reference pattern, and set it as
      # popular key in the result
      bin_id = proto_search.referencePatternId
      bin_res = self.format_bin(proto_results.lattice,
                                id2bin,
                                id2bin[bin_id],
                                proto_search.isoToReference,
                                subsumes_ref)
      if bin_res is None:
        continue
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
        if bin_res is None:
          continue
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

    res_bin["id"] = acdfgBin.id
    res_bin["frequency"] = self.get_popularity(lattice, id2bin, acdfgBin)
    res_bin["cardinality"] = len(acdfgBin.names_to_iso)


    # Get the source code of the pattern
    (source_code, acdf_reduced) = self.get_pattern_code(lattice,
                                                        id2bin,
                                                        acdfgBin)
    res_bin["pattern_code"] = source_code

    # Compute the patch from the acdfgs
    acdfg_repr = AcdfgRepr(acdfgBin.acdfg_repr)
    acdfg_query = AcdfgRepr(isoRes.acdfg_1)
    query_to_ref_mapping = Mappings(acdfg_query, acdfg_repr, isoRes)
    patchGenerator = AcdfgPatch(acdfg_query,
                                acdfg_repr,
                                query_to_ref_mapping)
    diffs = patchGenerator.get_diffs()
    if len(diffs) == 0:
      # no diffs found
      # not significant pattern
      return None
    else:
      pass



    # get the code patch, calling the source code service
    lineNum = LineNum(isoRes.acdfg_1.node_lines)

    # Creates three lists of lines association between
    # the query acdf and all the other acdfgs in the
    # pattern
    acdfg_mappings = []
    visitedMapping = set()
    first = True
    for isoPair in acdfgBin.names_to_iso:
      mapping = {}
      source_info = self._fill_source_info(isoPair)
      mapping["source_info"] = source_info
      repo_tag = self._fill_repo_tag(isoPair)
      mapping["repo_tag"] = repo_tag

      # remove duplicates from the visit
      key = "%s/%s/%s/%s.%s/%s" % (repo_tag["user_name"],
                                   repo_tag["repo_name"],
                                   repo_tag["commit_hash"],
                                   source_info["class_name"],
                                   source_info["method_name"],
                                   source_info["method_line_number"])
      if key in visitedMapping: continue
      visitedMapping.add(key)

      acdfg_other = AcdfgRepr(isoPair.iso.acdfg_1)
      other_to_ref_mapping = Mappings(acdfg_other, acdfg_repr, isoPair.iso)

      query_to_other_mapping = Mappings()
      query_to_other_mapping.init_from_others(query_to_ref_mapping,
                                              other_to_ref_mapping)

      if first:
        patches = self.format_patches(diffs,
                                      query_to_other_mapping,
                                      lineNum)
        first = False

      try:
        (nodes_res, edges_res) = query_to_other_mapping.get_lines(
          acdfg_query,
          isoRes.acdfg_1.node_lines,
          acdfg_other,
          isoPair.iso.acdfg_1.node_lines)

        # Computes the mapping from the acdfg used in the
        # query and the acdfg in the bin
        (nodes_res, edges_res) = Search.get_mapping(isoRes.acdfg_1,
                                                    isoPair.iso.acdfg_1,
                                                    isoRes,
                                                    isoPair.iso,
                                                    # Never reverse, the data is
                                                    # already ok
                                                    False)
        mapping["nodes"] = {"iso" : nodes_res[0],
                            "add" : nodes_res[1],
                            "remove" : nodes_res[2]}
        mapping["edges"] = {"iso" : edges_res[0],
                            "add" : edges_res[1],
                            "remove" : edges_res[2]}
      except Exception as e:
        logging.debug("Error mapping nodes nodes:\n%s\n" % str(e))

      finally:
        # skip exception building the mapping, be robust if we fail
        # the mapping is used to morph my code into the examples, but now we do
        # not show this on the interface
        acdfg_mappings.append(mapping)

    if first:
      patches = self.format_patches(diffs,
                                    query_to_ref_mapping,
                                    lineNum)
    res_bin["acdfg_mappings"] = acdfg_mappings
    res_bin["diffs"] = patches

    return res_bin


  def _fill_source_info(self, isoPair):
    assert isoPair.iso.acdfg_1.HasField("source_info")

    source_info = {}
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

    return source_info

  def _fill_repo_tag(self, isoPair):
    assert (isoPair.iso.acdfg_1.HasField("repo_tag"))

    repo_tag = {}

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

    return repo_tag

  def format_patches(self, diffs, query_to_ref_mapping, lineNum):
    """ Returns a readable representatio nof the the patches.

    Out format:
    [ { "type" :  string, (either "+" or "-")
        "entry" : {
           line : integer,
           after : string, (entry method)
           what : string, (describe the patch, code or list of methods)
        },
        "exits" : [{
          line : integer,
          before : string, (exit method)
       }]
     }
    ]
    """

    def _get_other_line(mapping, node_b):
      if node_b is None:
        return None
      else:
        for (iso_a, iso_b) in mapping._isos:
          if (iso_b.id == node_b.id and 
              mapping._is_node(iso_a)):
            return iso_a

      return None


    diffs_json = []
    for diff in diffs:
      diff_json = {}

      diff_type = "+" if diff._diff_type == AcdfgDiff.DiffType.ADD else "-"

      entry = {}
      if diff._entry_node is None:
        entry_line = 0
      elif diff._diff_type == AcdfgDiff.DiffType.REMOVE:
        entry_line = lineNum.get_line(diff._entry_node)
      elif diff._diff_type == AcdfgDiff.DiffType.ADD:
        node_a = _get_other_line(query_to_ref_mapping,
                                 diff._entry_node)
        if (not node_a is None):
          entry_line = lineNum.get_line(node_a)
        else:
          entry_line = None

        # TODO --- FIX, use iso
        # entry_line = 0

      after = diff.get_entry_string()
      what = diff.get_what_string()

      # TODO -- FIX
      if entry_line is None:
        entry_line = 0

      entry = {"line" : entry_line,
               "after" : after,
               "what" : what}

      exits = []
      if len(diff._exit_nodes) == 0:
        exits.append( {"line" : 0, "before" : "exit"} )
      else:
        for exit_node in diff._exit_nodes:
          exit_line = 0
          if diff._diff_type == AcdfgDiff.DiffType.REMOVE:
            # TODO: fix
            exit_line = lineNum.get_line(exit_node)
            if exit_line is None:
              exit_line = 0
          elif diff._diff_type == AcdfgDiff.DiffType.ADD:
            # TODO --- FIX, use iso
            node_a = _get_other_line(query_to_ref_mapping,
                                     exit_node)

            if (not node_a is None):
              exit_line = lineNum.get_line(node_a)
            else:
              exit_line = 0

          before = diff.get_exit_string(exit_node)

        exits.append( {"line" : exit_line, "before" : before} )

      diff_json["type"] = diff_type
      diff_json["entry"] = entry
      diff_json["exits"] = exits

      diffs_json.append(diff_json)

    return diffs_json

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
            line_no = id2num[elem_id]
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
      # TODO: why is the initial map empty here?
      # id2num empty means that there is no
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

  def get_pattern_code(self, lattice, id2bin, acdfgBin):
    """
    Reconstruct the source code of the pattern represented in the bin.

    It uses the groum index to find the original graph representing
    the pattern.
    """
    if self.groum_index is None:
      return ("", None)

    found_orig = False;
    for isoPair in acdfgBin.names_to_iso:
      acdfg_reduced = AcdfgRepr(isoPair.iso.acdfg_1)

      source_info = self._fill_source_info(isoPair)
      repo_tag = self._fill_repo_tag(isoPair)

      key = u"%s/%s/%s/%s.%s/%s" % (repo_tag["user_name"],
                                    repo_tag["repo_name"],
                                    repo_tag["commit_hash"],
                                    source_info["class_name"],
                                    source_info["method_name"],
                                    source_info["method_line_number"])

      acdfg_orig_path = self.groum_index.get_groum_path(key)
      if not acdfg_orig_path is None:
        if os.path.exists(acdfg_orig_path):
          found_orig = True
          break

    if not found_orig:
      return ("", None)

    try:
      acdfg_proto = Acdfg()
      with open(acdfg_orig_path, "rb") as f1:
        acdfg_proto.ParseFromString(f1.read())
        f1.close()
      acdfg_original = AcdfgRepr(acdfg_proto)
      code_gen = CodeGenerator(acdfg_reduced, acdfg_original)
      code = code_gen.get_code_text()
      logging.debug("\nGENERATED CODE\n")
      logging.debug(code)
    except Exception as e:
      # import traceback
      # traceback.print_exc(file=sys.stdout)
      logging.debug("Error generating source code for:\n" \
                    "acdfg_reduced (bin id): %s\n" \
                    "acdfg_orig_path: %s\n"
                    % (acdfgBin.id,
                       acdfg_orig_path))

      code = ""

    return (code, acdfg_reduced)

