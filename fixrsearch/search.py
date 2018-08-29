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

            results.append(results_cluster)

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
            assert not acdfbBin.id in id2bin
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
            bin_res = self.format_bin(id2bin[bin_id],
                                      proto_search.isoToReference,
                                      subsumes_ref)
            search_res["popular"] = bin_res

            # Process the anomalous
            if (proto_search.HasField("anomalousPatternId") and
                proto_search.HasField("isoToAnomalous")):
                bin_id = proto_search_res.anomalousPatternId

                bin_res = self.format_bin(id2bin[bin_id],
                                          proto_search.isoToAnomalous,
                                          subsumes_ref)
                search_res["anomalous"] = bin_res

            search_res_list.append(search_res)
        results["search_results"] = search_res_list

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

        # Creates three lists of lines association betweem
        # the query acdf and all the other acdfgs in the
        # pattern:
        #   -
        # acdfg in the pattern
        acdfg_mappings = []
        for isoPair in acdfbBin.names_to_iso:
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

            # Computes the mapping from the acdfg used in the
            # query and the acdfg in the bin
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
        def get_all(lists):
            res = []
            for l in lists:
                for elem in l:
                    elem_id = elem.id
                    line_no = 0
                    line_no = int(elem.id) # DEBUG
                    res.append((elem_id, line_no))
                return res

        def get_nodes(acdfg):
            return get_all([acdfg.data_node, acdfg.misc_node,
                            acdfg.method_node])

        def get_edges(acdfg):
            return get_all([acdfg.def_edge, acdfg.use_edge,
                            acdfg.trans_edge])

        # 1. Remap the maps of nodes and edges to be from
        # acdfg_1 to acdfg_2 (it is a join on the id of ref!)
        nodes_1_to_2 = {}
        edges_1_to_2 = {}
        for (my, iso_1_ref, iso_2_ref) in zip([nodes_1_to_2, edges_1_to_2],
                                              [isorel_1_ref.nodesMap, isorel_1_ref.edgesMap],
                                              [isorel_2_ref.nodesMap, isorel_2_ref.edgesMap]):
            if not reverse_1:
                ref_dst = [pair.id_1 for pair in isorel_1_ref.nodesMap]
            else:
                ref_dst = [pair.id_2 for pair in isorel_1_ref.nodesMap]

            # Build a map from elements in ref to elements in acdfg_2
            map_ref_2 = {}
            for pair in iso_2_ref:
                if pair.id_2 in map_ref_2:
                    logging.error("%d is mapped to multiple nodes!" % pair.id_2)
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
                    logging.error("%d is not mapped!" % el_2)


        # Compute the common, added, and removed lines
        idx_iso = 0
        idx_to_add = 1
        idx_to_remove = 2

        nodes_res = ([],[],[])
        edges_res = ([],[],[])
        nodes_lists = (get_nodes(acdfg_1), get_nodes(acdfg_2))
        edges_lists = (get_edges(acdfg_1), get_edges(acdfg_2))

        for (res, elem_1_to_2, elem_lists) in zip([nodes_res, edges_res],
                                                  [nodes_1_to_2, edges_1_to_2],
                                                  [nodes_lists, edges_lists]):
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

    # with open("/tmp/app.json", "w") as f:
    #     json.dump(result, f)
    #     f.close()



    # TODO CATCH EXCEPTION


if __name__ == '__main__':
    main()

