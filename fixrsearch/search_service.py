from flask import Flask, request, Response, render_template, current_app
import json
import optparse
import logging
import os
import sys

CLUSTER_PATH = "cluster_path"
ISO_PATH = "iso_path"
INDEX = "index"

from search import (Search, RESULT_CODE,
                    ERROR_MESSAGE,
                    PATTERN_KEY ,
                    ISO_DOT ,
                    RESULTS_LIST ,
                    OBJ_VAL ,
                    SEARCH_SUCCEEDED_RESULT ,
                    ERROR_RESULT,
                    get_cluster_file)

from search import get_cluster_file
from index import ClusterIndex
#from fixrsearch.search import Search, ClusterIndex, get_cluster_file

#@app.route('/search', methods=['POST'])
def search_pattern():
    reply_json = {"hello" : "hello"}

    search = Search(current_app.config[CLUSTER_PATH],
                    current_app.config[ISO_PATH],
                    current_app.config[INDEX])

    groum_file = "/Users/sergiomover/works/projects/muse/repos/FixrGraphIso/test/test_data/com.dagwaging.rosewidgets.db.widget.UpdateService_update.acdfg.bin"

    results = search.search_from_groum(groum_file)

    reply_json = {RESULT_CODE : SEARCH_SUCCEEDED_RESULT,
                  RESULTS_LIST : results}



    return Response(json.dumps(reply_json),
                    status=200,
                    mimetype='application/json')



def flaskrun(default_host="127.0.0.1", default_port="5000"):
    logging.basicConfig(level=logging.INFO)

    p = optparse.OptionParser()

    p.add_option('-a', '--address', help="Host name")
    p.add_option('-p', '--port', help="Port name")
    p.add_option('-d', '--debug', help="Debug mode",
                 action="store_true", default=False)

    p.add_option('-c', '--cluster_path', help="Base path to the cluster directory")
    p.add_option('-i', '--iso_path', help="Path to the isomorphism computation")

    def usage(msg=""):
        if msg:
            print "----%s----\n" % msg
            p.print_help()
            print "Example of usage %s" % ("python search_service.py " \
                                           "-c <cluster_path>" \
                                           "-i <searchlattice>")
        sys.exit(1)
    opts, args = p.parse_args()


    host = opts.address if opts.address else default_host
    port = opts.port if opts.port else default_port

    if (not opts.cluster_path):
        usage("Cluster path not provided!")
    if (not os.path.isdir(opts.cluster_path)):
        usage("Cluster path %s does not exist!" % (opts.cluster_path))
    if (not opts.iso_path): usage("Iso executable not provided!")
    if (not os.path.isfile(opts.iso_path)):
        usage("Iso executable %s does not exist!" % opts.iso_path)

    app = create_app(opts.cluster_path, opts.iso_path)

    app.route('/search', methods=['POST'])(search_pattern)

    app.run(
        debug=opts.debug,
        host=host,
        port=int(port)
    )


def create_app(cluster_path, iso_path):
    app = Flask(__name__)
    app.config[CLUSTER_PATH] = cluster_path
    app.config[ISO_PATH] = iso_path

    cluster_file = get_cluster_file(cluster_path)
    app.config[INDEX] = ClusterIndex(cluster_file)

    return app


if __name__ == '__main__':
    flaskrun()
