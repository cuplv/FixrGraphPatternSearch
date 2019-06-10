"""
Computes the diff information from two acdfgs.

We compute a list of "diff" information between the
developer's code acdfg and the pattern acdfg. The diff is a first
approximation of a patch that would fix the developer's code
according to the pattern.

We have the "removed" and "added" diffs.

The removed/added diffs are the diffs that contain "paths" in the
devel/pattern acdfg and not in the pattern/devel acdfg.

We compute a "diff" as a graph formed by the nodes and edges in one graph that
are not mapped to the other graph.
We collect also the "entry" and "exit" nodes --- the nodes that are in the
isomorphism between the two graphs and would reach a node in the GRAPH ("entry"
or  would be reached by a node in the GRAPH ("exit")
"""

from enum import Enum
import StringIO

from fixrsearch.codegen.acdfg_repr import AcdfgRepr
from fixrsearch.codegen.generator import CodeGenerator


class AcdfgPatch(object):
  def __init__(self, devel_acdfg, pattern_acdfg, mappings):
    super(AcdfgPatch, self).__init__()

    self._devel_acdfg = devel_acdfg
    self._pattern_acdfg = pattern_acdfg
    self._mappings = mappings

  def _is_iso_devel(self, elem):
    return self._mappings.is_iso_a(elem)

  def _is_iso_pattern(self, elem):
    return self._mappings.is_iso_b(elem)

  def _discover_diffs(self, helper, acdfg, diff_type, is_iso_f, diffs):
    """
    Finds the nodes on the "frontier" of the iso/non-iso nodes
    (e.g., the nodes that are in the iso but that can reach a node
    not in the iso)
    """

    roots = acdfg.find_control_roots()
    stack = [n for n in roots if is_iso_f(n)]
    root_not_iso = [n for n in roots if is_iso_f(n)]

    diff = self._process_frontier(helper, None, root_not_iso,
                                  diff_type, is_iso_f)
    diffs.append(diff)

    visited = set()
    while (len(stack) > 0):
      current = stack.pop()
      if current in visited: continue
      visited.add(current)

      for edge in helper.get_all_successors(current):
        if (not is_iso_f(edge.to_node)):
          diff = self._process_frontier(helper, current, [edge.to_node],
                                        diff_type, is_iso_f)
          diffs.append(diff)
        else:
          stack.append(edge.to_node)

    return diffs

  def _process_frontier(self, helper, entry, roots, diff_type, is_iso_f):
    diff = AcdfgPatch.AcdfgDiff(entry, roots, diff_type)
    visited = set()
    stack = list(roots)

    while (len(stack) > 0):
      current = stack.pop()
      if current in visited: continue
      visited.add(current)

      for edge in helper.get_all_successors(current):
        has_next = False
        if (not is_iso_f(edge.to_node)):
          diff.add_edge(current, edge.to_node)
          stack.append(edge.to_node)
          has_next = True
        else:
          diff.add_exit(current)
          pass

    return diff


  def get_diffs(self):
    diffs = []

    helper = CodeGenerator.Helper(self._pattern_acdfg, [])
    self._discover_diffs(helper,
                         self._pattern_acdfg,
                         AcdfgPatch.AcdfgDiff.DiffType.ADD,
                         self._is_iso_pattern,
                         diffs)

    helper = CodeGenerator.Helper(self._devel_acdfg, [])
    self._discover_diffs(helper,
                         self._devel_acdfg,
                         AcdfgPatch.AcdfgDiff.DiffType.REMOVE,
                         self._is_iso_devel,
                         diffs)

    return diffs

  class AcdfgDiff(object):
    class DiffType(Enum):
      ADD = 0
      REMOVE = 0

    def __init__(self, entry_node, roots, diff_type):
      """
      graph: the set of nodes reachable from the entry node to the exit node

      The graph can be empty in the degenerate case
      entry node: entry node of the graph (None means the graph is a root node)

      exit node: exit node of the graph (None means that the last graph's node
      is a tail node)
      """
      super(AcdfgPatch.AcdfgDiff, self).__init__()

      self._roots = set(roots)
      self._nodes = set(self._roots)
      self._edges = set()
      self._entry_node = entry_node
      self._exit_nodes = set()

      self._diff_type = diff_type

    def add_edge(self, from_node, to_node):
      self._nodes.add(from_node)
      self._nodes.add(to_node)
      self._edges.add((from_node, to_node))


    def add_exit(self, exit_node):
      self._exit_nodes.add(exit_node)

    def _print(self, stream): 
      # <after> entry node
      # Calls/Misses to call
      # {set of method call in the diff}
      # <before> exit_nodes

      stream.write("After the method ")
      if self._entry_node is None:
        stream.write("entry ")
      else:
        ast = CodeGenerator.get_expression_ast(self._entry_node)
        ast._print(stream, "")

      if len(self._exit_nodes) == 0:
        stream.write("and before the method end ")
      else:
        stream.write("and before the methods:\n")
        for n in self._exit_nodes:
          ast = CodeGenerator.get_expression_ast(n)
          ast._print(stream, "  ")

      if self._diff_type == AcdfgPatch.AcdfgDiff.DiffType.ADD:
        stream.write("you should call")
      else:
        stream.write("you should not call")
      stream.write(" the methods:\n")

      # first approx
      for n in self._nodes:
        ast = CodeGenerator.get_expression_ast(n)
        ast._print(stream, "  ")

    def __repr__(self):
      output = StringIO.StringIO()
      self._print(output)
      return output.getvalue()

