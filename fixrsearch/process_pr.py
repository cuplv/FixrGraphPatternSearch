"""
Implement the logic that process a pull request
"""

import logging
from fixrsearch.groum_index import GroumIndex
import fixrsearch.db
from fixrsearch.anomaly import Anomaly

from fixrsearch.utils import (
  RepoRef,
  PullRequestRef,
  CommitRef,
  MethodRef,
  ClusterRef,
  PatternRef
)

class PrProcessor:
  def __init__(self, groum_index, db, search):
    self.groum_index = groum_index
    self.db = db
    self.search = search

  def find_pr_commit(self, repo_user, repo_name, pull_request_id):
    """
    Find the pr in the database --- need to get the commit of the pull
    request to process it.

    The commit id of the pull request must have been set when extracting
    the graphs for the last commit.
    """
    pr_ref = PullRequestRef(RepoRef(repo_name, repo_user),
                            pull_request_id,
                            None)
    pr_ref = self.db.get_pr_ignore_commit(pr_ref)
    return pr_ref


  def process_graphs_from_pr(self, pull_request_ref):
    """ Process all the graphs produced in the pull request creating the
    anomalies.

    Side effect on the internal database

    Return the list of anomalies created for all the graphs.
    """
    anomalies = []
    app_key = GroumIndex.get_app_key(pull_request_ref.repo_ref.user_name,
                                     pull_request_ref.repo_ref.repo_name,
                                     pull_request_ref.commit_ref.commit_hash)
    groum_records = self.groum_index.get_groums(app_key)
    for groum_record in groum_records:
      groum_id = groum_record["groum_key"]
      groum_file = self.groum_index.get_groum_path(groum_id)

      if groum_file is None:
        error_msg = "Cannot find groum for %s in %s. " \
                    "Skipping the groum... " % (groum_id, groum_file)
        logging.debug(error_msg)
        continue

      method_ref = MethodRef(pull_request_ref.commit_ref,
                             groum_record["class_name"],
                             groum_record["package_name"],
                             groum_record["method_name"],
                             groum_record["method_line_number"],
                             groum_record["source_class_name"])

      # Search for anomalies
      results = self.search.search_from_groum(groum_file)
      for cluster_res in results:
        assert "cluster_info" in cluster_res
        cluster_info = cluster_res["cluster_info"]
        assert "id" in cluster_info and "methods_list" in cluster_info

        method_list = ClusterRef.build_methods_str(cluster_info["methods_list"])
        cluster_ref = ClusterRef(cluster_info["id"], method_list)

        for search_res in cluster_res["search_results"]:
          # TODO: Test, skip for now
          if (search_res["type"] != "ANOMALOUS_SUBSUMED" and
              search_res["type"] != "CORRECT_SUBSUMED"):
            continue

          # get the pattern
          assert "popular" in search_res
          binRes = search_res["popular"]

          binResField = ["type", "acdfg_mappings", "frequency",
                         "cardinality", "id"]
          for i in binResField: assert i in binRes
          assert binRes["type"] == "popular"

          # TODO: Generate pattern id (propagate from search)
          pattern_ref = PatternRef(cluster_ref,
                                   binRes["id"],
                                   PatternRef.Type.POPULAR,
                                   binRes["frequency"],
                                   binRes["cardinality"])

          # TODO: Generate patch text
          patch_text = ""
          # TODO: Generate anomaly text
          pattern_anomaly_text = ""
          # TODO: Generate an error text for the anomaly

          # Create the anomaly
          anomaly = Anomaly(0, # tmp id, to be set with the sorting
                            method_ref,
                            pull_request_ref,
                            patch_text,
                            pattern_anomaly_text,
                            pattern_ref)

          # insert the frequency to sort the anomalies
          anomalies.append((binRes["frequency"], anomaly))


    # sort the anomalies
    sorted_anomalies = sorted(anomalies, key = lambda pair : pair[0],
                       reverse=False)
    anomaly_out = []
    anomaly_id = 0
    for (score, anomaly) in sorted_anomalies:
        anomaly_id += 1
        anomaly.numeric_id = anomaly_id
        self.db.new_anomaly(anomaly)
        anomaly_out.append(anomaly)

    return anomaly_out



  def get_pattern_text(self, ):
    code_gen = CodeGenerator(acdfg_reduced, acdfg_original)
    text = code_gen.get_code_text()

