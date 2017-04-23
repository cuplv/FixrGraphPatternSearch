"""
Implement the index/search for clusters
"""

import logging
import itertools
from cStringIO import StringIO
from fixrgraph.solr.patterns_utils import parse_clusters, parse_cluster_info

class IndexNode(object):
   """
   The index is optimized to search if a set is contained in another set
   Implements a SetTrie
   Index Data Structure for Fast Subset and Superset Queries
   IFIP International Federation for Information Processing 2013
   http://osebje.famnit.upr.si/~savnik/papers/cdares13.pdf

   We implement the getAllSuperSets operation
   """
   def __init__(self, key):
      self.key = key
      self.children = []
      self.clusters = []

   def is_root(self):
      return self.key < 0

   @staticmethod
   def _find_index(children, key):
      def _find_index_rec(children, key, low, high):
         if low > high:
            return (low,high)
         else:
            idx = (low + high) / 2
            if children[idx].key == key:
               return (idx,idx)
            elif key < children[idx].key:
               return _find_index_rec(children, key, low, idx-1)
            else:
               return _find_index_rec(children, key, low+1, high)

      return _find_index_rec(children, key,
                             0, len(children) - 1)

   def _insert_rec(self, int_list, value, l, h):
      if (l > h):
         self.clusters.append(value)
      else:
         first_elem = int_list[l]
         (i1,i2) = IndexNode._find_index(self.children, first_elem)

         if i1 == i2:
            # found the element, recur
            index_elem = self.children[i1]
            index_elem._insert_rec(int_list, value, l + 1, h)
         else:
            # insert the first_elem in the list at
            # position i1 + 1
            index_elem = IndexNode(first_elem)
            self.children.insert(i1 + 1, index_elem)
            index_elem._insert_rec(int_list, value, l + 1, h)

   def insert(self, int_list, value):
      self._insert_rec(int_list, value, 0, len(int_list) - 1)

   def _get_all_supersets_rec(self, int_list,
                              supersets,
                              l, h, found):
      if (l > h and found):
         supersets.extend(self.clusters)
         for c in self.children:
            c._get_all_supersets_rec(int_list,
                                     supersets,
                                     l,h, found)
      else:
         match_current = ((not self.is_root() and self.key == int_list[l]) or
                          (self.is_root()))
         current_less_than = ((not self.is_root() and self.key <= int_list[l]) or
                              (self.is_root()))
         if (l == h and match_current):
            # Consumed the word
            self._get_all_supersets_rec(int_list, supersets, l+1, h, True)
         elif match_current:
            # Explore the rest of the word
            next_elem = int_list[l+1]
            for child in self.children:
               if child.key <= next_elem:
                  child._get_all_supersets_rec(int_list, supersets, l+1, h, False)
         elif current_less_than:
            current_elem = int_list[l]
            for child in self.children:
               if child.key <= current_elem:
                  child._get_all_supersets_rec(int_list, supersets, l, h, False)

   def get_all_supersets(self, int_list):
      """
      Find all the supersets of int_list.

      - Searches for a prefix in the trie that match int_list
      - Returns all the sets contained in the trie starting 
      from the found prefix

      """
      supersets = []
      self._get_all_supersets_rec(int_list,
                                  supersets,
                                  -1, len(int_list) - 1,
                                  False)
      return supersets

   def _print_(self, stream, ind):
      stream.write("%sKey: %d\n" % (ind, self.key))
      c_repr = ",".join([str(c) for c in self.clusters])
      stream.write("%sCluster: %s\n" % (ind, c_repr))
      for c in self.children:
         new_ind = "%s  " % ind
         c._print_(stream, new_ind)

   def __repr__(self):
      stringio = StringIO()
      self._print_(stringio, "")
      return stringio.getvalue()

   def __eq__(self, other):
      if type(self) != type(other):
         return False
      elif self.key != other.key:
         return False
      elif len(self.clusters) != len(other.clusters):
         return False
      elif len(self.children) != len(other.children):
         return False
      else:
         for (c_self, c_other) in zip(self.clusters, other.clusters):
            if not (c_self == c_other):
               return False
         for (c_self, c_other) in zip(self.children, other.children):
            if not (c_self == c_other):
               return False
      return True

class ClusterIndex(object):
   """ Keep an index of the cluster by method names
   """

   def __init__(self, cluster_file):
      self.index_node = IndexNode(-1)
      self.m2i = {}
      self.i2m = {}

      self.cluster_file = cluster_file
      self.methods_set = None
      self._create_index()

      self.pattern_map = {}

   def _build_int_mappings(self,cluster_infos):
      methods_set = set()
      # collect the methods
      for ci in cluster_infos:
         for m in ci.methods_list:
            if m not in methods_set:
               methods_set.add(m)
      # assign a mapping
      count = -1
      for m in methods_set:
         count += 1
         self.m2i[m] = count
         self.i2m[count] = m
      self.methods_set = methods_set

   def _convert_list(self, src_list, src2dst):
      dst_list = []
      for src_elem in src_list:
         dst_elem = src2dst[src_elem]
         dst_list.append(dst_elem)
      dst_list.sort()
      return dst_list

   def _m2i_list(self, methods_list):
      dst_list = self._convert_list(methods_list, self.m2i)
      return dst_list

   def _i2m_list(self, int_list):
      dst_list = self._convert_list(int_list, self.i2m)
      return dst_list

   def _create_index(self):
      with open(self.cluster_file, "r") as cluster_stream:
         cluster_infos = parse_clusters(cluster_stream)
         cluster_stream.close()

      self._build_int_mappings(cluster_infos)

      for c in cluster_infos:
         int_list = self._m2i_list(c.methods_list)
         self.index_node.insert(int_list, c)

   def get_clusters(self, methods_list, min_methods_in_common):
      # Remove methods that are not in the index
      methods_set = set(methods_list)
      methods_set.intersection_update(self.methods_set)

      # enumerate all the min_methods_in_common size
      # subset of methods_set

      clusters = set()
      for s in itertools.combinations(methods_set, min_methods_in_common):
         int_method_list = self._m2i_list(s)
         new_clusters = self.index_node.get_all_supersets(int_method_list)
         clusters.update(new_clusters)
      return clusters

   def get_patterns(self, cluster_info):

      if cluster_info.id in self.pattern_map:
         return self.pattern_map[cluster_info.id]

      cluster_base_path = os.dirname(self.cluster_file)
      current_path = os.path.join(cluster_base_path,
                                  "all_clusters",
                                  "cluster_%d" % cluster_info.id)
      cluster_info_file = os.path.join(current_path,
                                       "cluster_%d_info.txt" % cluster_info.id)

      with open(cluster_info_file, 'r') as f:
         pattern_list = parse_cluster_info(f)
         f.close()
      self.pattern_map[cluster_info.id] = pattern_list
      return pattern_list
