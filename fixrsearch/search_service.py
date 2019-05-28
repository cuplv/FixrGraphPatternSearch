from flask import Flask, request, Response, render_template, current_app
import json
import optparse
import logging
import os
import sys

CLUSTER_PATH = "cluster_path"
ISO_PATH = "iso_path"
INDEX = "index"
GROUM_INDEX = "groum_index"

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
from groum_index import GroumIndex
#from fixrsearch.search import Search, ClusterIndex, get_cluster_file


def get_apps():
    groum_index = current_app.config[GROUM_INDEX]
    apps = groum_index.get_apps()    
    return Response(json.dumps(apps),
                    status=200,
                    mimetype='application/json')

def get_groums():
    content = request.get_json(force=True)
    if (not content is None) and ("app_key" in content):
        app_key = content["app_key"]

        groum_index = current_app.config[GROUM_INDEX]
        groums = groum_index.get_groums(app_key)

        return Response(json.dumps(groums),
                        status=200,
                        mimetype='application/json')
    else:
        print 'Malformed requests'
        response = {'Malformed requests': 'No app_key provided'}
        return Response(json.dumps(response),
                        status=404,
                        mimetype='application/json')


def search_pattern():
    content = request.get_json(force=True)

    if (not content is None) and ("groum_key" in content):
        groum_id = content["groum_key"]
        groum_index = current_app.config[GROUM_INDEX]
        groum_file = groum_index.get_groum_path(groum_id)


        if groum_file is None:
            error_msg = "Cannot find groum for %s" % groum_id
            reply_json = {"status" : 1,
                          "error" : error_msg}

            return Response(json.dumps(reply_json),
                            status=404,
                            mimetype='application/json')

        else:
            search = Search(current_app.config[CLUSTER_PATH],
                            current_app.config[ISO_PATH],
                            current_app.config[INDEX])

            results = search.search_from_groum(groum_file)

            reply_json = {"status" : 0,
                          "results" : results}

            return Response(json.dumps(reply_json),
                            status=200,
                            mimetype='application/json')
    else:
        reply_json = {"status": 1, "error" : "Malformed requests"}
        return Response(json.dumps(reply_json),
                        status=404,
                        mimetype='application/json')


# def process_pull_request(self):
    

# def get_patch(self):
    

# def get_pattern(self):



def flaskrun(default_host="127.0.0.1", default_port="5000"):
    p = optparse.OptionParser()

    p.add_option('-a', '--address', help="Host name")
    p.add_option('-p', '--port', help="Port name")
    p.add_option('-d', '--debug', help="Debug mode",
                 action="store_true", default=False)

    p.add_option('-g', '--graph_path', help="Base path to the acdfgs")
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
    if (not opts.graph_path):
        usage("Graph path not provided!")
    if (not os.path.isdir(opts.graph_path)):
        usage("Graph path %s does not exist!" % (opts.graph_path))

    if (not opts.iso_path): usage("Iso executable not provided!")
    if (not os.path.isfile(opts.iso_path)):
        usage("Iso executable %s does not exist!" % opts.iso_path)

    if (opts.debug):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


    app = create_app(opts.graph_path, opts.cluster_path, opts.iso_path)

    app.run(
        debug=opts.debug,
        host=host,
        port=int(port)
    )
    logging.info("Running server...")


def create_app(graph_path, cluster_path, iso_path):
    app = Flask(__name__)
    app.config[CLUSTER_PATH] = cluster_path
    app.config[ISO_PATH] = iso_path

    cluster_file = get_cluster_file(cluster_path)

    logging.info("Creating cluster index...")
    app.config[INDEX] = ClusterIndex(cluster_file)

    logging.info("Creating graph index...")
    app.config[GROUM_INDEX] = GroumIndex(graph_path)

    logging.info("Set up routes...")
    app.route('/search', methods=['POST'])(search_pattern)
    app.route('/get_apps', methods=['GET'])(get_apps)
    app.route('/get_groums', methods=['POST'])(get_groums)

    return app


if __name__ == '__main__':
    flaskrun()
