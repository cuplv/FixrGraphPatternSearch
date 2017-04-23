""" Test the creation of the index

"""

import os
import logging
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from fixrsearch.index import IndexNode, ClusterIndex
import fixrsearch

class TestIndex(unittest.TestCase):

    def test_find_index(self):
        def _find_index(l,el,l_e,h_e):
            l_index = []
            for key in l:
                l_index.append(IndexNode(key))

            (low,high) = IndexNode._find_index(l_index, el)
            self.assertTrue(low == l_e)
            self.assertTrue(high == h_e)

        _find_index([], 1, 0, -1)
        _find_index([1], 2, 1, 0)
        _find_index([1,2,4], 3, 2, 1)

        _find_index([1], 1, 0, 0)
        _find_index([1,2,4], 2, 1, 1)

    def test_insert(self):
        index = IndexNode(-1)
        index.insert([], set())

        res = IndexNode(-1)
        res.clusters = [set()]
        self.assertTrue(index == res)

        child1 = IndexNode(1)
        child1.clusters = [set([1])]
        res.children.append(child1)
        index.insert([1], set([1]))
        self.assertTrue(index == res)

        child2 = IndexNode(2)
        child2.clusters = [set([1,2])]
        child1.children.append(child2)
        #
        index.insert([1,2], set([1,2]))
        self.assertTrue(index == res)

        child3 = IndexNode(3)
        child3.clusters = [set([1,3])]
        child1.children.append(child3)
        #
        index.insert([1,3], set([1,3]))
        self.assertTrue(index == res)

    def test_search_subsets(self):
        index = IndexNode(-1)
        self.assertTrue(index.get_all_supersets([1]) == [])

        # {1,2}, {3,4,5}, {5}
        index = IndexNode(-1)
        index.insert([1,2], set([1,2]))
        index.insert([3,4,5], set([3,4,5]))
        index.insert([5], set([5]))

        self.assertTrue(index.get_all_supersets([1]) == [set([1,2])])
        self.assertTrue(index.get_all_supersets([5]) == [set([3,4,5]),set([5])])
        self.assertTrue(index.get_all_supersets([5,7]) == [])
        self.assertTrue(index.get_all_supersets([3,4]) == [set([3,4,5])])

        self.assertTrue(index.get_all_supersets([]) == [set([1,2]),
                                                        set([3,4,5]),
                                                        set([5])])

    def test_index(self):
        test_path = os.path.dirname(fixrsearch.test.__file__)
        index = ClusterIndex(os.path.join(test_path,"clusters.txt"))

        set_1 = ["<get>.android.graphics.Point.x_int",
                 "<get>.android.graphics.Point.y_int",
                 "android.util.Log.d"]
        set_2 = ["android.content.Intent.<init>", "android.content.Intent.setData",
                 "android.net.Uri.parse"]
        set_3 = ["android.content.Intent.<init>", "android.content.Intent.setData"]
        set_4 = ["android.content.Intent.<init>", "android.content.Intent.setData",
                 "cavallo"]

        res = index.get_clusters(set_1, 2)
        self.assertTrue(len(res) == 1)

        res = index.get_clusters(set_2, 2)
        self.assertTrue(len(res) == 1)

        res = index.get_clusters(set_3, 2)
        self.assertTrue(len(res) == 1)

        res = index.get_clusters(set_4, 2)
        self.assertTrue(len(res) == 1)

        res = index.get_clusters(set([]), 2)
        self.assertTrue(len(res) == 0)

        res = index.get_clusters(set([]), 0)
        self.assertTrue(len(res) == 2)


