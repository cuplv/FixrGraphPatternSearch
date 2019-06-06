"""
Utilities to transform acdfgs and mappings to to code
"""

from fixrsearch.code_gen.acdfg_repr import (
  AcdfgRepr, Node, MethodNode, DataNode MiscNode, Edge
)
from enum import Enum
import StringIO

class CodeGenerator(object):
  """ Generate mock source code from a pattern
  """

  def __init__(self, acdfg):
    self.acdfg = acdfg

  def get_code_text(self):
    ast = self._get_ast()
    return str(ast)

  # 1. Construct an AST representing the graph control flow
  def _get_ast(self):
    ast = self._get_cfg()

  def _get_cfg(self):
    roots = self.find_control_root()

    # visit the graph from the root generating the AST
    for r in roots:
      cfg = CFG(self.acdf, r)


  def _find_control_roots(self):
    """ Get all the control nodes without incoming edges """
    roots = {}
    for n in self._control:
      roots.add(n)

    for e in self._edges:
      if e.to_node in roots: roots.remove(e)
    return roots


class CFG(object):
  def __init__(self, acdfg, root_node):
    super(object, self).__init__()
    self.acdfg = acdfg
    self.root = root

    self._reachable = self._reachable_dfs(root)

    self._fwd = {}
    self._bwd = {}

    for c in self.acdfg._control:
      self._fwd[c] = []
      self._bwd[c] = []

    edge_types = {Edge.Type.CONTROL}
    for e in self.acdfg._edges:
      if (e.from_node in self.acdfg._control and
          e.to_node in self.acdfg._control and
          # remove self loops
          e.from_node != e.to_node and
          # remove non control edges
          e.edge_type in edge_types):

        self._fwd[e.from_node].append(e.to_node)
        self._bwd[e.to_node].append(e.from_node)

    # Domination relations
    self._dom = None

  def _build_dominator_relation(self):
    # map from node i to the set of nodes that
    # dominates i
    self._dom = {}

    # Init the domination relation
    # only root dominates itself
    self.dom[self.root] = {self.root}
    # suppose that each node dominates each other node
    for node in self._reachable:
      if node == self.root: continue
      dom[node] = set(self._reachable)

    # Iterative computation of the dominator relation
    # If a node dominates all the predecessors of a
    # node n, then it also dominates node n.
    # Use a fixed-point computation to find that out.
    change = True
    while change:
      change = False

      for node in self._reachable:
        if node == self.root: continue

        # get all the nodes that dominate the
        # predecessors of node
        dom_pred_set = None
        for pred in self._bwd[node]:
          if dom_pred_set == None:
            dom_pred_set = set(dom[pred])
          dom_pred_set.intersection_update(dom[pred])

        # the nodes that dominate node are all the
        # nodes in dom_pred_set and the current node
        if dom_pred_set is None:
          dom_pred_set = {node}
        else:
          dom_pred_set.add(node)

        # if the set of dominators changed, then do another
        # iteration of the algorithm
        if not (dom_pred_set == dom[node]):
          change = True
          dom[node] = dom_pred_set

  def _find_loops(self):
    # Loops store (head_node, back_node, body_nodes)
    loops = {}

    for node in self._reachable:
      for dominator in self._dom[node]:
        if dominator in self._fwd[node]:
          # we have a back edge from node to dominator
          body_nodes = self._reachable_from(node, True, dominator)
          loops.add( (dominator, node, body_nodes) )
    return loops

  def _reachable_dfs(self, node, bwd=False):
    reachable = {}
    to_visit = [node]

    rel = self._bwd if bwd else self._fwd

    while len(to_visit) > 0:
      current = to_visit[0]
      if current in reachable: continue

      reachable.add(current)

      for reach_node in rel:
        to_visit.append(reach_node)

    return reachable

  def _reachable_from(self, node, bwd=False, target):
    reachable_dir1 = self._reachable_dfs(node, bwd)
    reachable_dir2 = self._reachable_dfs(target, not bwd)

    reachable_dir1.intersection_update(reachable_dir2)

    return reachable_dir1


class PatternAst(object):
  """ Ast of the mini-language representing the pattern.

  The grammar of the language is:
  expr := var | const
  cmd := method(expr, ..., expr)
         | var := method(expr, ..., expr)
         | cmd ; cmd
         | if * then cmd else cmd
         | while * do cmd
  """

  class MalformedASTException(Exception):
    def __init__(self, message, errors):
        super(MalformedASTException, self).__init__(message)
        self.errors = errors

  class NodeType(Enum):
    VAR = 0
    CONST = 1
    METHOD = 2
    DECL = 3
    SEQ = 4
    IF = 5
    WHILE = 6

  INDENT = "  "

  CMD_TYPES = {NodeType.METHOD, NodeType.DECL, NodeType.SEQ,
               NodeType.IF, NodeType.WHILE}
  EXPR_TYPES = {NodeType.VAR, NodeType.CONST}

  DATA_MAP = {"name" : {NodeType.VAR, NodeType.CONST},
              "method_name" : {NodeType.METHOD}}

  def __init__(self, ast_type):
    super(object, self).__init__()
    self.ast_type = ast_type
    self.data = {}
    self.children = []

  def _val_data(self, field_name):
    if field_name in DATA_MAP:
      return self.ast_type in DATA_MAP[field_name]
    else:
      err = "Unkonwn %s field" % field_name
      raise MalformedASTException(err)

  def _val_children(self, children):
    len_c = len(children)

    if self.ast_type in {NodeType.SEQ, NodeType.IF, NodeType.WHILE}:
      for c in children:
        if not c.is_cmd():
          raise MalformedASTException("%s must be a command!" % str(c))

      if self.ast_type in {NodeType.SEQ, NodeType.IF}:
        if len_c != 2:
          err = "Node must have 2 children, %d given!" % len_c
          raise MalformedASTException(err)
      elif self.ast_type == NodeType.WHILE:
        if len_c != 1:
          err = "Node must have 1 children, %d given!" % len_c
          raise MalformedASTException(err)

    elif self.ast_type in {NodeType.DECL}:
      if len_c != 2:
          err = "Node must have 2 children, %d given!" % len_c
          raise MalformedASTException(err)
      elif children[0].ast_type != NodeType.VAR:
        err = "Node %s must be a var!" % str(c)
        raise MalformedASTException(err)
      elif children[1].ast_type != NodeType.METHOD:
        err = "Node %s must be a method!" % str(c)
        raise MalformedASTException(err)

    elif self.ast_type in {NodeType.METHOD}:
      for c in children:
        if not c.is_expr():
          err = "Node %s must be an expression!" % str(c)
          raise MalformedASTException(err)

    elif self.is_expr():
      if len_c != 0:
        err = "Node must have 0 children, %d given!" % len_c
        raise MalformedASTException(err)

    else:
      # Unknonw type
      err = "Unkonwn node type!"
      raise MalformedASTException(err)

  def _set_data(self, field_name, value):
    assert self._val_data(field_name)
    self.data[field_name] = value

  def _get_data(self, field_name, value):
    self._val_data(field_name)
    return self.data[field_name]

  def set_children(self, children):
    self._val_children(children)
    self.children = [c for c in children]

  def is_cmd(self):
    return self.ast_type in CMD_TYPES

  def is_expr(self):
    return self.ast_type in EXPR_TYPES

  def _print(self, out_stream, indent):
    if (self.ast_type in {NodeType.VAR, NodeType.CONST}):
      out_stream.write("%s%s" % (indent, self._get_data("name")))
    elif (self.ast_type == NodeType.METHOD):
      out_stream.write("%s%s(" % (indent, self._get_data("method_name")))

      first = True
      for c in self.children:
        if not first:
          c._print(out_stream, ", ")
        c._print(out_stream, "")
        first = False
      out_stream.write(")")

    elif (self.ast_type == NodeType.DECL):
      self.children[0]._print(out_stream, indent)
      out_stream.write(" = ")
      self.children[1]._print(out_stream, "")
    elif (self.ast_type == NodeType.SEQ):
      self.children[0]._print(out_stream, indent)
      out_stream.write(";\n")
      self.children[1]._print(out_stream, indent)
    elif (self.ast_type == NodeType.IF):
      out_stream.write("%sif (*) {\n" % indent)
      self.children[0]._print(out_stream, indent + INDENT)
      out_stream.write("\n%selse (*) {" % indent)
      self.children[1]._print(out_stream, indent + INDENT)
      out_stream.write("\n%s}\n" % indent)
    elif (self.ast_type == NodeType.WHILE):
      out_stream.write("%swhile(*) {\n" % indent)
      self.children[0]._print(out_stream, indent + INDENT)
      out_stream.write("\n%s}\n" % indent)
    else:
      assert False

  def __repr__(self):
    output = StringIO.StringIO()
    self._print(output)
    return output.getvalue()

