"""
Implement the services for the BigGroum tools.

The endpoints are:
- search: search for the similar patterns to a groum
- get_apps: get all the apps (repos) existing in the dataset
- get_groums: get all the groums in the dataset
- process_pull_request: process a pull request and finds the similar pattern

TODO:
- add a service that receives an apk + metadata and extract the graph,
  adding them to the filesystem and the index


"""

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
DB_NAME = "service_db"
DB="db"

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

from db import SQLiteConfig, Db

def get_malformed_request(error = None):
    if error is None:
       error = "Malformed request"
    else:
       error = "Malformed request (%s)" % error
    reply_json = {"status": 1, "error" : "Malformed requests"}
    return Response(json.dumps(reply_json),
                    status=404,
                    mimetype='application/json')

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
        return get_malformed_request("no app key provided")


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
        return get_malformed_request()


def process_pull_request(self):
    # get pr data
    content = request.get_json(force=True)
    if (content is None):
        return get_malformed_request()

    fields = ["user", "repo", "commitHashes",
              "modifiedFiles", "pullRequestId"]
    for f in fields:
        if f not in content:
            return get_malformed_request("%s not in the request" % f)

    user_name = content["user"]
    repo_name = content["repo"]
    repo_ref = RepoRef(repo_name, user_name)

    pull_request_id = content["pullRequestId"]
    commits = content["commitHashes"]
    modifiedFiles = content["modifiedFiles"]

    # Find right pr to access the commit id used in the merge
    db = current_app.config[DB]      
    pr_ref = db.PullRequestRef(repo_ref,
                               pull_request_id,
                               None)                            
    pr_ref = db.get_pr_ignore_commit(pr_ref)

    if pr_ref is None:
        # Reply with an error
        error_msg = "Cannot find pull request %s for %s/%s" % (str(pull_request_id),
                                                               repo_ref.user_name,
                                                               repo_ref.repo_name)
        reply_json = {"status" : 1,
                      "error" : error_msg}        
        return Response(json.dumps(reply_json),
                        status=404,
                        mimetype='application/json')

    # Search for similar graphs
    anomalies = []
    app_key = index.get_app_key(pr_ref.repo_ref.user_name,
                                pr_ref.repo_ref.repo_name,
                                pr_ref.commit_ref.commit_hash)
    groums = index.get_groums(app_key)
    for g in groums:
        groum_id = g["groum_key"]
        groum_file = groum_index.get_groum_path(groum_id)

        if groum_file is None:
            error_msg = "Cannot find groum for %s in %s" % (groum_id,
                                                            groum_file)
            logging.debug(error_msg)
        else:
            method_ref = CommitRef(pullRequest.repo_ref,
                                   pullRequest.commit_ref,
                                   g["class_name"],
                                   g["package_name"],
                                   g["method"],
                                   g["method_line_number"],
                                   g["source_class_name"])        

            search = Search(current_app.config[CLUSTER_PATH],
                            current_app.config[ISO_PATH],
                            current_app.config[INDEX])
            results = search.search_from_groum(groum_file)


            for cluster_res in results:
                clusterRef = ClusterRef("", 0.0)

                for search_res in cluster_res["search_results"]:
                    # Test, skip for now
                    if search_res["type"] != "ANOMALOUS_SUBSUMED":
                        continue
                
                    assert "popular" in search_res

                    # get the pattern
                    binRes = search_res["popular"]
                    
                    assert "type" in binRes
                    assert "mappings" in binRes
                    assert "frequency" in binRes

                    # binRes["frequency"]
                    assert(binRes["type"] == "popular")

                    # TODO: Generate patch text
                    patchText = ""
                    # TODO: Generate pattern text
                    patternText = ""
                    patternRef = PatternRef(cluster_ref,
                                            "",
                                            PatternRef.Type.Popular)
                
                    # Create the anomaly
                    anomaly = Anomaly(anomaly_count,
                                      method_ref,
                                      pr_ref,
                                      patchText,
                                      patternRef)

                    anomalies.append((binRes["frequency"], anomaly))


    # sort and add the anomalies
    anomalies = sorted(anomalies,
                       key = lambda pair : pair[0],
                       reverse=False)
    anomaly_id = 0
    for anomaly in anomalies:
        anomaly_id += 1
        anomaly.numeric_id = anomaly_id
        db.new_anomaly(anomaly)

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

    # p.add_option('-d', '--db_type', type='choice',
    #              choices= ["sqlite"],
    #              help="Choose db type to use",
    #              default = "sqlite")

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

    # create the db object
    config = SQLiteConfig(DB_NAME)
    db = Db(config)
    db.connect_or_create()

    app.config[DB] = db

    return app


if __name__ == '__main__':
    flaskrun()
