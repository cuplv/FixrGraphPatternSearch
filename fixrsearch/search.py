"""
Given a GROUM, searches for all the similar patterns
"""

import sys
import os
import optparse
import logging
import json

JSON_OUTPUT = True

RESULT_CODE="result_code"
ERROR_MESSAGE="error_messages"
SEARCH_SUCCEEDED_RESULT = 0
ERROR_RESULT = 1


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

    # TODO: build the index
    # TODO: search the index

if __name__ == '__main__':
    main()

