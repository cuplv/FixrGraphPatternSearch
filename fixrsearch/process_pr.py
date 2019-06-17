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

from src_service_client import (
  PatchResult, SrcMethodReq,
  DiffEntry, SourceDiff
)

class PrProcessor:
  def __init__(self, groum_index, db, search, src_client):
    self.groum_index = groum_index
    self.db = db
    self.search = search
    self.src_client = src_client

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
      results = self.search.search_from_groum(groum_file, True)
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

          # 0. Get the popular bin
          bin_res = search_res["popular"]
          bin_res_field = ["type", "acdfg_mappings", "frequency",
                         "cardinality", "id"]
          for i in bin_res_field: assert i in bin_res
          assert bin_res["type"] == "popular"

          anomaly = PrProcessor._process_search_res(self.src_client,
                                                    pull_request_ref,
                                                    method_ref,
                                                    cluster_ref,
                                                    bin_res)
          # insert the frequency to sort the anomalies
          anomalies.append((bin_res["frequency"], anomaly))


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


  @staticmethod
  def _process_search_res(src_client,
                          pull_request_ref,
                          method_ref,
                          cluster_ref,
                          bin_res):
    """ Process a single search for a single anomaly.
    """

    logging.info("Processing bin %d..." % bin_res["id"])

    # 1. Construct the reference to the pattern object
    pattern_ref = PatternRef(cluster_ref,
                             bin_res["id"],
                             PatternRef.Type.POPULAR,
                             bin_res["frequency"],
                             bin_res["cardinality"])

    # 2. Get the patch text
    diffs_json = bin_res["diffs"]
    (patch_text, git_path) = PrProcessor._get_patch_text(src_client,
                                                         pull_request_ref.commit_ref,
                                                         method_ref,
                                                         diffs_json)

    # 3. Get the anomaly text
    pattern_anomaly_text = bin_res["pattern_code"]

    # 4. Generate the error text for the anomaly
    # TODO

    # Create the anomaly
    anomaly = Anomaly(0, # tmp id, to be set with the sorting
                      method_ref,
                      pull_request_ref,
                      patch_text,
                      pattern_anomaly_text,
                      pattern_ref)
    return anomaly


  @staticmethod
  def _get_patch_text(src_client, commit_ref, method_ref, diffs_json):
    """
    Call the service that composes the patch text
    """
    github_url = "https://github.com/%s/%s" % (
      commit_ref.repo_ref.user_name,
      commit_ref.repo_ref.repo_name)
    src_method = SrcMethodReq(github_url,
                              commit_ref.commit_hash,
                              method_ref.source_class_name,
                              method_ref.start_line_number,
                              method_ref.method_name)
    source_diff = PrProcessor._get_source_diff(diffs_json)
    res_patch = src_client.getPatch(src_method, source_diff)
    if (res_patch.is_error()):
      logging.debug("Cannot compute the patch (%s)" %
                    res_patch.get_error_msg())
      patch_text = ""
      git_path = ""
    else:
      patch_text = res_patch.get_patch()
      git_path = res_patch.get_git_path()
    return (patch_text, git_path)

  @staticmethod
  def _get_source_diff(diffs_json):
    """ Format the input for the service that gets the
    patch text
    """
    def _get_entry(entry_json, is_exit=False):
      name = "before" if is_exit else "after"
      what = "" if is_exit else entry_json["what"]

      return DiffEntry(entry_json["line"],
                       entry_json[name],
                       what)

    source_diffs = []
    for diff_json in diffs_json:
      exits = []

      for diff_exit in diff_json["exits"]:
        entry = _get_entry(diff_exit, True)
        exits.append(entry)

      source_diff = SourceDiff(diff_json["type"],
                               _get_entry(diff_json["entry"]),
                               exits)
      source_diffs.append(source_diff)

    return source_diffs
