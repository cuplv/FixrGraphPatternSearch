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
import fixrgraph.annotator.protobuf.proto_acdfg_pb2 as proto_acdfg_pb2
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

FAKE_RES="""digraph isoAB { 
rankdir=TB;
 node[shape=box,style="filled,rounded",penwidth=2.0,fontsize=13,]; 
 edge[ arrowhead=onormal,penwidth=2.0,]; 

subgraph cluster_A { 
rank=same;
 
 style="rounded"
 label="ACDFG A"
"a_1" [ shape=ellipse,color=red,style=dashed,label="DataNode #1: org.droidplanner.android.droneshare.data.DroneShareDB  $r0"];

"a_4" [ shape=ellipse,color=red,style=dashed,label="DataNode #4: android.database.sqlite.SQLiteDatabase  $r1"];

"a_5" [  shape=box, style=filled, color=lightgray, label=" android.database.sqlite.SQLiteOpenHelper.getWritableDatabase[#1]()"];

} /* Cluster A */
subgraph cluster_B { 
rank=same;
 color=gray;
 style="rounded"
 label="ACDFG B"
"b_7" [ shape=ellipse,color=red,style=dashed,label="DataNode #7: ollitos.platform.andr.AndrKeyValueDatabase  $r0"];

"b_9" [ shape=ellipse,color=red,style=dashed,label="DataNode #9: android.database.sqlite.SQLiteDatabase  db"];

"b_10" [  shape=box, style=filled, color=lightgray, label=" android.database.sqlite.SQLiteOpenHelper.getWritableDatabase[#7]()"];

} /* Cluster B */
"a_1" -> "b_7"[color=red,Damping=0.7,style=dashed]; 

"a_4" -> "b_9"[color=red,Damping=0.7,style=dashed]; 

"a_5" -> "b_10"[color=red,Damping=0.7,style=dashed]; 

"a_1" -> "a_5"[color=green, penwidth=2];

"b_7" -> "b_10"[color=green, penwidth=2];

"a_5" -> "a_4"[color=blue, penwidth=2];

"b_10" -> "b_9"[color=blue, penwidth=2];

 } """

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
            for (obj_val, pattern_info, iso_dot, ci) in results:
                solr_key = _get_pattern_key(ci.id,
                                            pattern_info.id,
                                            pattern_info.type)
                solr_results.append({PATTERN_KEY : solr_key,
                                     OBJ_VAL : str(obj_val),
                                     ISO_DOT : iso_dot})
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

            (is_iso, obj_val, iso_dot) = self.call_iso(groum_path, bin_path)
            if is_iso:
                matching_patterns.append((obj_val, p, iso_dot, cluster_info))

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
        iso_file, iso_path = tempfile.mkstemp(suffix=".dot", prefix="computed_iso", text=True)
        os.close(iso_file)

        iso_path_args = iso_path.replace(".dot","")

        args = [self.iso_path, g1, g2, iso_path_args]
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
            (is_iso, objective_val, iso_dot) = (False, -1.0, "")
        else:
            logging.info("Computed isomorphism...")
            (is_iso, objective_val) = self._parse_iso_res(stdout)
            with open(iso_path, 'r') as fiso:                
                iso_dot = fiso.read()
                fiso.close()
                
        if os.path.isfile(iso_path):
            os.remove(iso_path)

        return (is_iso, objective_val, iso_dot)


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
    p.add_option('-i', '--iso_path', help="Path to the isomorphism computation exeBarcodeEye/BarcodeEye/0e59cf40d83d3da67413b0b20410d6c57cca0b9ecutable")

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
    solr_results = search.search_from_groum(groum_file, True)

    result = {RESULT_CODE : SEARCH_SUCCEEDED_RESULT,
              RESULTS_LIST : solr_results}
    json.dump(result,sys.stdout)


if __name__ == '__main__':
    main()

