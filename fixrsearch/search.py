"""
Given a GROUM, searches for all the similar patterns
"""

import sys
import os
import optparse
import logging
import json

from fixrsearch.index import ClusterIndex
import fixrgraph.annotator.protobuf.proto_acdfg_pb2 as proto_acdfg_pb2

JSON_OUTPUT = True

RESULT_CODE="result_code"
ERROR_MESSAGE="error_messages"
SEARCH_SUCCEEDED_RESULT = 0
ERROR_RESULT = 1


class Search():
    def __init__(self, cluster_path):
        self.cluster_path = cluster_path

        # 1. Build the index
        cluster_file = os.path.join(cluster_path,
                                    "clusters.txt")
        self.index = ClusterIndex(cluster_file)

    def search_from_groum(self, groum_path):
        # 1. Get the method list from the GROUM
        acdfg = proto_acdfg_pb2.Acdfg()
        with open(groum_path,'rb') as fgroum:
            acdfg.ParseFromString(fgroum.read())
            method_list = []
            for m in acdfg.method_bag.method:
                method_list.append(m)
            fgroum.close()

        # 2. Search the clusters
        clusters = self.index.get_clusters(method_list,2)

        # 3. Search the clusters
        for cluster in clusters:
            # To implement
            assert False


def main():
    logging.basicConfig(level=logging.DEBUG)

    p = optparse.OptionParser()
    p.add_option('-g', '--groum', help="Path to the GROUM file to search")
    p.add_option('-c', '--cluster_path', help="Base path to the cluster directory")

    def usage(msg=""):
        if JSON_OUTPUT:
            result = {RESULT_CODE : ERROR_RESULT,
                      ERROR_MESSAGE: msg}
            json.dump(result,sys.stdout)
        else:
            if msg:
                print "----%s----\n" % msg
                p.print_help()
                print "Example of usage %s" % ("python search.py "
                                               "-g groum.acdfg.bin"
                                               "-c /extractionpath/clusters")
        sys.exit(1)
    opts, args = p.parse_args()

    if (not opts.groum): usage("GROUM file not provided!")
    if (not os.path.isfile(opts.groum)):
        usage("GROUM file %s does not exist!" % opts.groum)
    if (not opts.cluster_path):
        usage("Cluster path not provided!")
    if (not os.path.isdir(opts.cluster_path)):
        usage("Cluster path %s does not exist!" % (opts.cluster_path))

    search = Search(opts.cluster_path)
    results = search.search_from_groum(opts.groum)



if __name__ == '__main__':
    main()

