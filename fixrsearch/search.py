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
from fixrgraph.annotator.protobuf.proto_acdfg_pb2 import Acdfg
from fixrgraph.annotator.protobuf.proto_search_pb2 import SearchResults
from fixrgraph.solr.import_patterns import _get_pattern_key

JSON_OUTPUT = True

RESULT_CODE="result_code"
ERROR_MESSAGE="error_messages"
PATTERN_KEY = "pattern_key"
ISO_DOT = "iso_dot"
RESULTS_LIST = "patterns"
OBJ_VAL = "obj_val"
SEARCH_SUCCEEDED_RESULT = 0
ERROR_RESULT = 1


class Search():
    def __init__(self, cluster_path, iso_path, timeout=10):
        self.cluster_path = cluster_path
        self.iso_path = iso_path
        self.timeout = timeout

        # 1. Build the index
        cluster_file = os.path.join(cluster_path,
                                    "clusters.txt")
        self.index = ClusterIndex(cluster_file)

        self.match_status = re.compile("Isomorphism status: (.+)")
        self.match_objective = re.compile("Objective value: (.+)")
        self.match_node_ratio = re.compile("NODETYPE: (\d+) = ([\d|\.]+)")
        self.match_method_node = re.compile("TOT_MET_NODES: ([\d|\.]+)")
        self.match_edge_ratio = re.compile("EDGETYPE: (\d+) = ([\d|\.]+)")



    def search_from_groum(self, groum_path):
        logging.debug("Search for groum %s" % groum_path)

        # 1. Get the method list from the GROUM
        acdfg = Acdfg()
        with open(groum_path,'rb') as fgroum:
            acdfg.ParseFromString(fgroum.read())
            method_list = []
            for method_node in acdfg.method_node:
                method_list.append(method_node.name)
            fgroum.close()

        # 2. Search the clusters
        clusters = self.index.get_clusters(method_list,2)

        # 3. Search the clusters
        results = []
        for cluster_info in clusters:
            logging.debug("Searching in cluster %d..." % cluster_info.id)

            results_cluster = self.search_cluster(groum_path, cluster_info)

            results.extend(results_cluster)

        # # Returns patterns as Solr documents
        # if solr_results:
        #     solr_results = []
        #     for (obj_val, pattern_info, iso_dot, ci) in results:
        #         solr_key = _get_pattern_key(ci.id,
        #                                     pattern_info.id,
        #                                     pattern_info.type)
        #         solr_results.append({PATTERN_KEY : solr_key,
        #                              OBJ_VAL : str(obj_val),
        #                              ISO_DOT : iso_dot})
        #     results = solr_results

        return results



    def search_cluster(self, groum_path, cluster_info):
        current_path = os.path.join(self.cluster_path,
                                    "all_clusters",
                                    "cluster_%d" % cluster_info.id)
        lattice_path = os.path.join(current_path,
                                    "cluster_%d_lattice.bin" % cluster_info.id)
        result = self.call_iso(groum_path, lattice_path)

        return result


    def call_iso(self, groum_path, lattice_path):
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

            # TODO: Read an construct result
            result = self.formatOutput(search_path)

        if os.path.isfile(search_path):
            os.remove(search_path)

        return result


    def formatOutput(self, search_path):
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

        id2bin = {}
        for acdfbBin in proto_lattice.bins:
            id2bin[acdfbBin.id] = acdfbBin


        # Process each single result
        search_res_list = []
        for proto_search in proto_results.results:
            search_res = {}
            subsumes_ref = True
            subsumes_anom = True

            if (proto_search.type == SearchResults.SearchResult.CORRECT):
                search_res["type"] = "CORRECT"
                subsumes_ref = True
                subsumes_anom = True
            elif (proto_search.type ==
                  SearchResults.SearchResult.CORRECT_SUBSUMED):
                search_res["type"] = "CORRECT_SUBSUMED"
                subsumes_ref = False
                subsumes_anom = True
            elif (proto_search.type ==
                  SearchResults.SearchResult.ANOMALOUS_SUBSUMED):
                search_res["type"] = "ANOMALOUS_SUBSUMED"
                subsumes_ref = False
                subsumes_anom = False
            elif (proto_search.type ==
                  SearchResults.SearchResult.ISOLATED_SUBSUMED):
                search_res["type"] = "ISOLATED_SUBSUMED"
                subsumes_ref = False
                subsumes_anom = False
            elif (proto_search.type ==
                  SearchResults.SearchResult.ISOLATED_SUBSUMING):
                search_res["type"] = "ISOLATED_SUBSUMING"
                subsumes_anom = False

            # Process the reference pattern
            bin_id = proto_search.referencePatternId
            ref_bin = id2bin[bin_id]
            bin_res = self.format_bin(ref_bin,
                                      proto_search.isoToReference,
                                      subsumes_ref)
            search_res["popular"] = bin_res

            # Process the anomalous
            if (proto_search.HasField("anomalousPatternId") and
                proto_search.HasField("isoToAnomalous")):
                bin_id = proto_search_res.anomalousPatternId
                ref_bin = id2bin[bin_id]
                bin_res = self.format_bin(ref_bin,
                                          proto_search.isoToAnomalous,
                                          subsumes_ref)
                search_res["anomalous"] = bin_res

            search_res_list.append(search_res)
        results["search_results"] = search_res_list

        print results

        return results

    def format_bin(self, acdfbBin, isoRes, subsumes):
        res_bin = {}

        if (acdfbBin.popular):
            res_bin["type"] = "popular"
        elif (acdfbBin.anomalous):
            res_bin["type"] = "anomalous"
        elif (acdfbBin.isolated):
            res_bin["type"] = "isolated"

        res_bin["frequency"] = len(acdfbBin.names_to_iso)

        # Computes the isomorphism relation with all the
        # samples in the pattern
        

        return res_bin

#         results.
#         proto_search_pb2
# [
# {
#  "method_names" : ["", "",""],
#  "search_results" : [{
#      "type" : "CORRECT",
#      "popular" : {
#          "type" : "popular",
#          "frequency" : "3",
#          "nodes_to_ref" : [[1,2],[2,3],..],
#          "edges_to_ref" : [[],[]],
#          "acdfgs_infos" : [{"name": "", ...}]
#      },
#      "anomalous" : {
#      }
#  }
#  ]
# }
# ]


def main():
    logging.basicConfig(level=logging.DEBUG)

    p = optparse.OptionParser()
    p.add_option('-g', '--groum', help="Path to the GROUM file to search")

    p.add_option('-d', '--graph_dir', help="Base path containing the graphs")
    p.add_option('-u', '--user', help="Username")
    p.add_option('-r', '--repo', help="Repo name")
    p.add_option('-z', '--hash', help="Hash number")
    p.add_option('-m', '--method', help="Fully qualified method name")

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
        if (not os.path.isdir(opts.graph_dir)): usage("%s does not exist!" % opts.graph_dir)
        if (not opts.user): usage("User not provided")
        if (not opts.repo): usage("Repo not provided")
        if (not opts.method): usage("Method not provided")
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
        repo_path = os.path.join(opts.graph_dir,
                                 opts.user,
                                 opts.repo)
        if (opts.hash):
            repo_path = os.path.join(repo_path, opts.hash)
        else:
            first_hash = None
            for root, dirs, files in os.walk(repo_path):
                if len(dirs) > 0:
                    first_hash = dirs[0]
                break
            if first_hash is None:
                usage("Username/repo not found!")
            repo_path = os.path.join(repo_path, first_hash)

        splitted = opts.method.split(".")
        class_list = splitted[:-1]
        method_list = splitted[-1:]
        fs_name = ".".join(class_list) + "_" + "".join(method_list)
        groum_file = os.path.join(repo_path, fs_name + ".acdfg.bin")

        if (not os.path.isfile(groum_file)):
            usage("Groum file %s does not exist!" % groum_file)

    search = Search(opts.cluster_path, opts.iso_path)
    results = search.search_from_groum(groum_file)

    result = {RESULT_CODE : SEARCH_SUCCEEDED_RESULT,
              RESULTS_LIST : results}
    json.dump(result,sys.stdout)
    # TODO CATCH EXCEPTION


if __name__ == '__main__':
    main()

