"""
Search script.


"""
import json
import optparse
import logging
import os
import sys
import string
import html
import traceback

from fixrsearch.search import Search
from fixrsearch.index import ClusterIndex
from fixrsearch.groum_index import GroumIndex

from fixrsearch.utils import (
  RepoRef,
  PullRequestRef,
  CommitRef,
  MethodRef,
  ClusterRef,
  PatternRef
)
from fixrsearch.src_service_client import SrcClientService, SrcClientMock
from fixrsearch.process_pr import PrProcessor



def search() :
    # TMP: test parameter, to move in the args
    iso_path = "/Users/sergiomover/works/projects/muse/repos/FixrGraphIso/build/src/fixrgraphiso/searchlattice"
    graph_path = "/Users/sergiomover/works/projects/muse/repos/biggroum/FixrGraphPatternSearch/demo_meeting/graphs"
    cluster_file = "/Users/sergiomover/works/projects/muse/repos/biggroum/FixrGraphPatternSearch/demo_meeting/clusters/clusters.txt"
    cluster_path = "/Users/sergiomover/works/projects/muse/repos/biggroum/FixrGraphPatternSearch/demo_meeting/clusters"


    # filter_keys = set(["Kaain/ToDoPlus/9d3c3ba347c1b3a93391b075b3073e1f1dcd97d2"])
    filter_keys = set(["smover/AwesomeApp/04f68b69a6f9fa254661b481a757fa1c834b52e1"])
    # max_res = 3
    max_res = -1

    # 451: ['android.database.sqlite.SQLiteClosable.close', 'android.database.sqlite.SQLiteDatabase.rawQuery', 'android.database.sqlite.SQLiteOpenHelper.getReadableDatabase']
    # 130: ['android.database.Cursor.close', 'android.database.Cursor.getCount', 'android.database.Cursor.getInt', 'android.database.Cursor.getString', 'android.database.Cursor.moveToFirst', 'android.database.sqlite.SQLiteClosable.close', 'android.database.sqlite.SQLiteDatabase.rawQuery']
    # 469: ['android.database.Cursor.moveToFirst', 'android.database.sqlite.SQLiteClosable.close', 'android.database.sqlite.SQLiteOpenHelper.getReadableDatabase']
    # 174: ['android.content.ContentValues.<init>', 'android.content.ContentValues.put', 'android.database.sqlite.SQLiteClosable.close', 'android.database.sqlite.SQLiteDatabase.insert', 'android.database.sqlite.SQLiteDatabase.update', 'android.database.sqlite.SQLiteOpenHelper.getWritableDatabase']
    # 105: ['android.content.ContentResolver.query', 'android.content.Context.getContentResolver', 'android.content.ContextWrapper.getContentResolver', 'android.database.Cursor.close', 'android.database.Cursor.getColumnIndex', 'android.database.Cursor.getColumnIndexOrThrow', 'android.database.Cursor.getCount', 'android.database.Cursor.getInt', 'android.database.Cursor.getLong', 'android.database.Cursor.getString', 'android.database.Cursor.isAfterLast', 'android.database.Cursor.moveToFirst', 'android.database.Cursor.moveToNext', 'android.database.sqlite.SQLiteClosable.close', 'android.database.sqlite.SQLiteDatabase.query', 'android.database.sqlite.SQLiteDatabase.rawQuery', 'android.database.sqlite.SQLiteOpenHelper.getReadableDatabase', 'android.util.Log.e']
    # 437: ['android.database.sqlite.SQLiteClosable.close', 'android.database.sqlite.SQLiteOpenHelper.getWritableDatabase', 'android.util.Log.e']
    # filter_clusters = [174]
    filter_clusters = None


    assert (os.path.isdir(graph_path))
    assert (os.path.isdir(cluster_path))
    assert (os.path.exists(cluster_file))
    assert (os.path.exists(iso_path))

    # create logger
    logging.basicConfig(level=logging.DEBUG,
                        filename='output_run.log',
                        filemode='w')
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # output file
    res_file = open("resfile.txt", 'w')
    html_res = open("resfile.html", 'w')


    groum_index = GroumIndex(graph_path)

    # app_key = groum_index.get_app_key(u"smover", u"AwesomeApp",
    #                                   u"9d759f47dc6b7b404a32eafcbc654b134bf6778a")
    groum_path = "/Users/sergiomover/works/projects/muse/repos/biggroum/FixrGraphPatternSearch/demo_meeting/graphs/smover/AwesomeApp/9d759f47dc6b7b404a32eafcbc654b134bf6778a/fixr.plv.colorado.edu.awesomeapp.MainActivity_recycleItems.acdfg.bin"
    # groum_index.process_groum(set([app_key]), groum_path)
    # groum_index.write_index(groum_index.index_file_name)


    cluster_index = ClusterIndex(cluster_file)
    search = Search(cluster_path,
                    iso_path,
                    cluster_index,
                    groum_index,
                    60)
    #src_client = SrcClientMock()
    src_client = SrcClientService("localhost", "8080")

    # # DEBUG
    # with open("cluster_index_repr.txt", "w") as f:
    #     cluster_index.index_node._dbg_print_(f)
    #     f.flush()
    #     f.close()
    # exit(0)
    # # END DEBUG

    html_res.write("<HTML><BODY>\n")

    count_apps = 0
    some_results = 0
    all_apps = groum_index.get_apps()
    tot_apps = len(all_apps)

    for repo in all_apps:
        count_apps += 1
        app_key = repo["app_key"]

        if ((not filter_keys is None) and (not app_key in filter_keys)):
            continue

        processing_msg = "Processing app %s [%d/%d]..." % (app_key,
                                                           count_apps,
                                                           tot_apps)
        print (processing_msg)
        logging.info(processing_msg + "\n")
        res_file.write(processing_msg + "\n")
        res_file.flush()


        repo_ref = RepoRef(repo["repo_name"], repo["user_name"])
        commit_hash = repo["commit_hash"]
        pull_request_ref = PullRequestRef(repo_ref, 1, CommitRef(repo_ref,
                                                                 commit_hash))
        groum_records = groum_index.get_groums(app_key)

        has_results = False
        for groum_record in groum_records:
            groum_id = groum_record["groum_key"]
            groum_file = groum_index.get_groum_path(groum_id)

            # DEBUG
#            if not groum_file.endswith(groum_path):
#                continue


            processing_msg = "   processing %s, %s...\n" % (str(groum_id), groum_file)
            # print(processing_msg)
            logging.info(processing_msg)
            res_file.write(processing_msg)
            res_file.flush()


            method_ref = MethodRef(pull_request_ref.commit_ref,
                                   groum_record["class_name"],
                                   groum_record["package_name"],
                                   groum_record["method_name"],
                                   groum_record["method_line_number"],
                                   groum_record["source_class_name"])



            if groum_file is None:
                error_msg = "Cannot find groum for %s in %s. " \
                            "Skipping the groum... " % (str(groum_id), groum_file)
                logging.debug(error_msg)
                continue


            try:
                # Search for anomalies
                results = search.search_from_groum(groum_file, True,
                                                   filter_clusters)
                if (len(results) == 0):
                    continue

                res_file.write("--- Found %s clusters for: %s\n" % (str(len(results)),
                                                                    groum_file))
                res_file.flush()

                for cluster_res in results:
                    cluster_info = cluster_res["cluster_info"]
                    cluster_id = cluster_info["id"]
                    method_list = cluster_info["methods_list"]
                    search_results = cluster_res["search_results"]

    #                print type(search_results)

                    method_list_ref = ClusterRef.build_methods_str(cluster_info["methods_list"])
                    cluster_ref = ClusterRef(cluster_info["id"], method_list_ref)


                    res_file.write("------ Found %s results in cluster %s\n"\
                                   "------ [%s]\n" % (
                        str(len(search_results)),
                        cluster_id,
                        ",".join(method_list)))
                    res_file.flush()

                    if len(search_results) > 0 :
                        has_results = True
                        FormatResult.write_cluster(html_res, cluster_ref)


                    for search_res in search_results:
                        bin_res = search_res["popular"]

                        res_file.write("Bin data:\n")
                        for fname in ["id", "type", "frequency", "cardinality"]:
                            res_file.write("--- %s = %s\n" % (fname,
                                                              str(bin_res[fname])))
                        res_file.flush()

                        anomaly = PrProcessor._process_search_res(src_client,
                                                                  pull_request_ref,
                                                                  method_ref,
                                                                  cluster_ref,
                                                                  bin_res)
                        FormatResult.write_anomaly(html_res, anomaly)
                        res_file.write(str(anomaly))
                        res_file.flush()

            except Exception as e:
                res_file.write("Something happened... (%s)" % str(e))
                res_file.flush()
                logging.debug("Exception: " + str(e))

                traceback.print_exc()

                pass

        if has_results:
            some_results += 1
            if (max_res > 0 and some_results >= max_res):
                break

    html_res.write("</BODY></HTML>")
    html_res.close()
    res_file.close()


class FormatResult:
    ANOMALY_TEMPLATE="""

<div class="anomalyClass">
<h2>Anomaly ${ID}</h2>
<div>
  <ul>
    <li>Repo: <a href="${REPO}">${REPO}</a></li>
    <li><a href="${METHOD}">${METHOD}</a> at line ${LINE} in ${FILE}</li>
    <li>Pattern id: ${PATTERNID}</li>
    <li>frequency = ${FREQUENCY}</li>
    <li>cardinality = ${CARDINALITY}</li>
  </ul>
  <h4>Description</h4>
${DESCRIPTION}
  <h4>Pattern</h4>
  <pre>
${PATTERN}
  </pre>
  <h4>Patch</h4>
  <pre>
${PATCH}
  </pre>
</div>
</div>
"""

    CLUSTER_TEMPLATE = """
<div>
<h2>Cluster ${ID}</h2>
Methods: ${METHODS}
</div>
"""

    @staticmethod
    def encode_map(subs):
        new_subs = {}
        for k,v in subs.iteritems():
            new_subs[k] = html.escape(v)
        return new_subs


    @staticmethod
    def write_anomaly(stream, anomaly):
        repo_url = "http://github.com/%s/%s/" % (
            anomaly.pull_request.repo_ref.user_name,
            anomaly.pull_request.repo_ref.repo_name,
        )

        file_url = "http://github.com/%s/%s/blob/%s/%s" % (
            anomaly.pull_request.repo_ref.user_name,
            anomaly.pull_request.repo_ref.repo_name,
            anomaly.pull_request.commit_ref.commit_hash,
            anomaly.git_path
        )

        subs = {
            "ID" : str(anomaly.numeric_id),
            "REPO" : repo_url,
            "METHOD" : anomaly.method_ref.method_name,
            "LINE" : str(anomaly.method_ref.start_line_number),
            "FILE" : file_url,
            "PATTERNID" : str(anomaly.pattern.pattern_id),
            "FREQUENCY" : str(anomaly.pattern.frequency),
            "CARDINALITY" : str(anomaly.pattern.cardinality),
            "DESCRIPTION" : str(anomaly.description),
            "PATTERN" : anomaly.pattern_text,
            "PATCH" : anomaly.patch_text,
        }

        subs = FormatResult.encode_map(subs)
        temp = string.Template(FormatResult.ANOMALY_TEMPLATE)
        res = temp.substitute(subs)

        stream.write(res)
        stream.write("\n")
        stream.flush()

    @staticmethod
    def write_cluster(stream, cluster_ref):
        subs = {"ID" : str(cluster_ref.cluster_id),
                "METHODS" : str(cluster_ref.methods)}
        subs = FormatResult.encode_map(subs)
        temp = string.Template(FormatResult.CLUSTER_TEMPLATE)
        res = temp.substitute(subs)
        stream.write(res)
        stream.write("\n")
        stream.flush()


search()
