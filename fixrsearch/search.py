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

from fixrsearch.index import ClusterIndex
import fixrgraph.annotator.protobuf.proto_acdfg_pb2 as proto_acdfg_pb2
from fixrgraph.solr.import_patterns import _get_pattern_key

JSON_OUTPUT = True

RESULT_CODE="result_code"
ERROR_MESSAGE="error_messages"
PATTERN_KEY = "pattern_key"
RESULTS_LIST = "patterns"
OBJ_VAL = "obj_val"
SEARCH_SUCCEEDED_RESULT = 0
ERROR_RESULT = 1


class Search():
    def __init__(self, cluster_path, iso_path):
        self.cluster_path = cluster_path
        self.iso_path = iso_path

        # 1. Build the index
        cluster_file = os.path.join(cluster_path,
                                    "clusters.txt")
        self.index = ClusterIndex(cluster_file)

        self.match_status = re.compile("Isomorphism status: (.+)")
        self.match_objective = re.compile("Objective value: (.+)")

    def search_from_groum(self, groum_path, solr_results=True):
        # 1. Get the method list from the GROUM
        acdfg = proto_acdfg_pb2.Acdfg()
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
            pattern_infos = self.index.get_patterns(cluster_info)
            app_results = self.search_patterns(groum_path, cluster_info, pattern_infos)
            results.extend(app_results)

        # sort by objective value
        results.sort(key=lambda res: res[0], reverse=True)

        # Returns patterns as Solr documents
        if solr_results:
            solr_results = []
            for (obj_val, pattern_info) in results:
                solr_key = _get_pattern_key(cluster_info.id,
                                            pattern_info.id,
                                            pattern_info.type)
                solr_results.append({PATTERN_KEY : solr_key,
                                     OBJ_VAL : str(obj_val)})
            results = solr_results

        return results



    def search_patterns(self, groum_path, cluster_info, pattern_infos):
        matching_patterns = []
        current_path = os.path.join(self.cluster_path,
                                    "all_clusters",
                                    "cluster_%d" % cluster_info.id)
        for p in pattern_infos:
            dot_path = os.path.join(groum_path, current_path, p.dot_name)
            bin_path = dot_path.replace(".dot",".acdfg.bin")

            (is_iso, obj_val) = self.call_iso(groum_path, bin_path)
            if is_iso:
                matching_patterns.append((obj_val, p))

        return matching_patterns


    def _parse_iso_res(self, proc_out):
        # parse the results
        is_iso = False
        objective_val = -1.0
        for line in proc_out.split("\n"):
            res = self.match_status.match(line)
            if res:
                res_string = res.group(1)
                if (res_string == "success"):
                    logging.debug("Iso found")
                    is_iso = True
                elif (res_string == "failure"):
                    logging.debug("Iso not computed successfully")

            res = self.match_objective.match(line)
            if res:
                res_string = res.group(1)
                try:
                    objective_val = float(res_string)
                    logging.debug("Objective value: %f" % objective_val)
                except Exception as e:
                    logging.debug("Error reading the objective value")
        return (is_iso, objective_val)


    def call_iso(self, g1, g2):
        args = [self.iso_path, g1, g2, "search_res"]
        logging.debug("Command line %s" % " ".join(args))

        # Kill the process after the timout expired
        def kill_function(p, cmd):
            logging.info("Execution timed out executing %s" % (cmd))
            p.kill()

        # proc = subprocess.Popen(args, stdout=out, stderr=err, cwd=None)
        proc = Popen(args, cwd=None, stdout=PIPE,  stderr=PIPE)
        timer = Timer(10, kill_function, [proc, "".join(args)])
        try:
            timer.start()
            (stdout, stderr) = proc.communicate() # execute the process
        except Exception as e:
            logging.error(e.message)
        finally:
            timer.cancel() # Cancel the timer, no matter what

        return_code = proc.returncode
        if (return_code != 0):
            err_msg = "Error code is %s\nCommand line is: %s\n%s" % (str(return_code), str(" ".join(args)),"\n")
            logging.error("Error executing %s\n%s" % (" ".join(args), err_msg))
            return (False, -1.0)
        else:
            logging.info("Computed isomorphism...")
            (is_iso, objective_val) = self._parse_iso_res(stdout)
        return (is_iso, objective_val)


def main():
    logging.basicConfig(level=logging.DEBUG)

    p = optparse.OptionParser()
    p.add_option('-g', '--groum', help="Path to the GROUM file to search")
    p.add_option('-c', '--cluster_path', help="Base path to the cluster directory")
    p.add_option('-i', '--iso_path', help="Path to the isomorphism computation executable")

    def usage(msg=""):
        if JSON_OUTPUT:
            result = {RESULT_CODE : ERROR_RESULT,
                      ERROR_MESSAGE: msg,
                      RESULTS_LIST : []}
            json.dump(result,sys.stdout)
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

    if (not opts.groum): usage("GROUM file not provided!")
    if (not os.path.isfile(opts.groum)):
        usage("GROUM file %s does not exist!" % opts.groum)
    if (not opts.cluster_path):
        usage("Cluster path not provided!")
    if (not os.path.isdir(opts.cluster_path)):
        usage("Cluster path %s does not exist!" % (opts.cluster_path))
    if (not opts.iso_path): usage("Iso executable not provided!")
    if (not os.path.isfile(opts.iso_path)):
        usage("Iso executable %s does not exist!" % opts.iso_path)


    search = Search(opts.cluster_path, opts.iso_path)
    solr_results = search.search_from_groum(opts.groum, True)

    result = {RESULT_CODE : SEARCH_SUCCEEDED_RESULT,
              RESULTS_LIST : solr_results}
    json.dump(result,sys.stdout)


if __name__ == '__main__':
    main()

