"""
Utilities to transform acdfgs and mappings to to code
"""

# TODO:
# Add data node as declaration
# 

from fixrsearch.codegen.acdfg_repr import (
  AcdfgRepr,
  Node, MethodNode, DataNode, MiscNode,
  Edge
)
from enum import Enum
import StringIO

class CodeGenerator(object):
  """ Generate mock source code from a pattern

  Print the sliced_acdfg.
  Uses the original one to get back the real control
  edges (the miner just hides them with the trans
  control edges)
  """

  def __init__(self, sliced_acdfg, original_acdfg):
    self.sliced_acdfg = sliced_acdfg
    self.original_acdfg = original_acdfg

  def get_code_text(self):
    ast = self._get_ast()
    return str(ast)


  def _get_ast(self):
    """ Construct an AST representing the graph control flow """
    roots = self.sliced_acdfg.find_control_roots()

    # Show only the original control edges
    self._fix_control_edges()

    main_ast = None

    # visit the graph from the root generating the AST
    for root in roots:
       cfg_analyzer = CFGAnalyzer(self.sliced_acdfg, root)
       loops = cfg_analyzer.get_loops()

       root_ast = self._get_node_ast(self.sliced_acdfg, root, loops)
       if main_ast is None:
         main_ast = root_ast
       else:
         app_ast = PatternAST(PatternAST.NodeType.IF)
         app_ast.set_children([main_ast, root_ast])
         main_ast = app_ast

    return main_ast

  def _get_node_ast(self, acdfg, root, loops):
    """ get the ast for the root node """
    helper = CodeGenerator.Helper(acdfg, loops)
    return self._get_node_ast_rec(acdfg, root, helper, [])

  def _get_node_ast_rec(self,
                        acdfg,
                        node,
                        helper,
                        stack):
    """ Returns the ast node for the the
    cfg node and the next cfg node to process
    in sequence.
    """

    # Process "base cases", when the recursion
    # must stop
    if helper.is_tail(node):
      expr_ast = self._get_expression_ast(node)
      return (expr_ast, stack)
    elif helper.is_join(node):
      stack.append(node)
      # Nothing to append to the previous nodes
      # join node processed once
      return None
    elif helper.is_back_edge(node):
      expr_ast = self._get_expression_ast(node)
      stack.append(node)
      return expr_ast

    # Get the base expression for the node
    expr_ast = self._get_expression_ast(node)

    is_loop = helper.is_head(node)
    is_if = helper.is_if(node)
    is_seq = helper.is_seq(node)

    assert ((not is_seq) or not is_if)
    assert ((not is_if) or not is_seq)

    if is_if:
      (if_ast, rest_ast) = self._process_if(acdfg,
                                            node,
                                            helper,
                                            stack)
    elif is_seq:
      rest_ast = self._process_seq(acdfg,
                                   node,
                                   helper,
                                   stack)

    if not is_loop:
      # Done, concatenate the rest with the node
      if is_if:
        app_ast = PatternAST(PatternAST.NodeType.SEQ)
        app_ast.set_children([if_ast, rest_ast])
        seq_ast = PatternAST(PatternAST.NodeType.SEQ)
        seq_ast.set_children([expr_ast, app_ast])
      elif is_seq:
        seq_ast = PatternAST(PatternAST.NodeType.SEQ)
        seq_ast.set_children([expr_ast, rest_ast])
      expr_ast = seq_ast
    else:
      # build the loop body
      assert len(stack) > 0
      loop_tail_node = stack.pop()

      # build the loop node
      app_body = PatternAST(PatternAST.NodeType.SEQ)
      if is_if:
        app_body.set_children([if_ast, rest_ast])
      else:
        app_body = rest_ast
      loop_body = PatternAST(PatternAST.NodeType.SEQ)
      loop_body.set_children([expr_ast, app_body])
      loop_ast = PatternAST(PatternAST.NodeType.WHILE)
      loop_ast.set_children([loop_body])

      # remove the current loop
      assert helper.is_loop(node, loop_tail_node)
      helper.remove_loop(node, loop_tail_node)

      if helper.is_head(loop_tail_node):
        rest_ast = self._get_node_ast_rec(acdfg,
                                          loop_tail_node,
                                          helper,
                                          stack)
        assert not rest_ast is None
      elif helper.is_if(loop_tail_node):
        (if_ast, rest_ast) = self._process_if(acdfg,
                                              loop_tail_node,
                                              helper,
                                              stack)
        assert not rest_ast is None
      elif helper.is_seq(loop_tail_node):
        rest_ast = self._process_seq(acdfg,
                                     loop_tail_node,
                                     helper,
                                     stack)
        assert not rest_ast is None
      else:
        # Tail
        rest_ast = None

      if rest_ast is None:
        expr_ast = loop_ast
      else:
        expr_ast = PatternAST(PatternAST.NodeType.SEQ)
        expr_ast.set_children([loop_ast, rest_ast])

    return expr_ast

  def _get_expression_ast(self, node):
    if isinstance(node, DataNode):
      if node.data_type == DataNode.DataType.VAR:
        ast = PatternAST(PatternAST.NodeType.VAR)
      else:
        ast = PatternAST(PatternAST.NodeType.CONST)
      ast._set_data("name", node.name)

      return ast
    elif isinstance(node, MethodNode):
      ast = PatternAST(PatternAST.NodeType.METHOD)

      children = []
      if not node.invokee is None:
        invokee_ast = self._get_expression_ast(node.invokee)
        children.append(invokee_ast)
      for c in node.arguments:
        p_ast = self._get_expression_ast(c)
        children.append(p_ast)
      ast._set_data("method_name", node.name)
      ast.set_children(children)

      if (not node.assignee is None):
        assignee_ast = self._get_expression_ast(node.assignee)
        assign_ast = PatternAST(PatternAST.NodeType.ASSIGN)
        assign_ast.set_children([assignee_ast, ast])
        ast = assign_ast

      return ast
    else:
      assert False

  def _process_seq(self, acdfg, node, helper, stack):
    next_node = helper.get_next(node)
    rest_ast = self._get_node_ast_rec(acdfg,
                                      next_node,
                                      helper,
                                      stack)
    return rest_ast


  def _process_if(self, acdfg, node, helper, stack):
    # Creates the AST for the two branches
    (left_node, right_node) = helper.get_if_branches(node)
    left_ast = self._get_node_ast_rec(acdfg,
                                      left_node,
                                      helper,
                                      stack)
    assert len(stack) > 0
    join_node_left = stack.pop()

    left_ast = self._get_node_ast_rec(acdfg,
                                      rigt_node,
                                      helper,
                                      stack)
    assert len(stack) > 0
    join_node_left = stack.pop()

    # The join must be the same
    assert (not join_node_left is None and
            join_node_left == join_node_right)

    if_ast = PatternAST(PatternAST.NodeType.IF)
    if_ast.set_children([left_ast, right_ast])

    rest_ast = self._get_node_ast_rec(acdfg,
                                      join_node_left,
                                      helper,
                                      stack)
    return (if_ast, rest_ast)

  def _fix_control_edges(self):
    nodes_to_keep = [n for n in self.sliced_acdfg._nodes]
    control_edges = self.original_acdfg.get_slice_edges(nodes_to_keep)

    new_edges = []
    for e in self.sliced_acdfg._edges:
      if (e.edge_type in {Edge.Type.TRANS}):
        if (e.from_node.id, e.to_node.id) in control_edges:
          e.edge_type = Edge.Type.CONTROL
          new_edges.append(e)
      else:
        new_edges.append(e)
    self.sliced_acdfg._edges = new_edges

  class Helper():
    """ Helper class storing transition functions for the
    CFG, the loop information, and simple accessors to node and
    their successors.

    """

    def __init__(self, acdfg, loops):
      # node -> list_of_successors edges (with a control edge)
      self._fwd = {}
      # node -> list_of_predecessors edges (with a control edge)
      self._bwd = {}

      # node -> list of use *nodes*
      self._used_node = {}
      # node -> list of defined *nodes* (it should one)
      self._def_nodes = {}

      # set of loops (head, tail)
      self._loops = set()
      # node -> count of loops s.t. node is a head
      self._loop_heads = {}
      # node -> count of loops s.t. node is a back edge
      self._loop_back_edges = {}

      # Fill the transition relation, use and def edges
      for node in acdfg._control:
        self._fwd[node] = set()
        self._bwd[node] = set()
        self._used_node[node] = set()
        self._def_nodes[node] = set()


      for e in acdfg._edges:
        if (e.edge_type == Edge.Type.CONTROL):
          assert e.from_node in acdfg._control
          assert e.to_node in acdfg._control

          self._fwd[e.from_node].add(e)
          self._bwd[e.to_node].add(e)

        elif (e.edge_type == Edge.Type.USE):
          assert e.from_node in acdfg._data
          assert e.to_node in acdfg._control
          self._used_node[e.to_node].add(e.from_node)

        elif (e.edge_type == Edge.Type.DEF_EDGE):
          assert e.from_node in acdfg._control
          assert e.to_node in acdfg._data

          self._def_nodes[e.from_node].add(e.to_node)

      # Fill the loop information
      for (head, back_edge, body_nodes) in loops:
        self._loops.add( (head, back_edge) )

        count = self._loop_heads[head] if head in self._loop_heads else 0
        self._loop_heads[head] = count + 1

        if back_edge in self._loop_back_edges:
          count = self._loop_back_edges[back_edge]
        else:
          count = 0
        self._loop_back_edges[back_edge] = count + 1

    def is_tail(self, node):
      return len(self._fwd[node]) == 0

    def is_join(self, node):
      """ join (for an if) if has at least 2 incoming
      edges that are not a loop head
      """
      if node in self._loop_heads:
        count_loops = self._loop_heads[node]
      else:
        count_loops = 0
      incoming = len(self._bwd[node]) - count_loops
      return incoming == 2

    def _count_outgoing(self, node):
      if node in self._loop_back_edges:
        count_be = self._loop_back_edges[node]
      else:
        count_be = 0
      outgoing = len(self._fwd[node]) - count_be
      return outgoing

    def is_if(self, node):
      return self._count_outgoing(node) == 2

    def is_seq(self, node):
      return self._count_outgoing(node) == 1

    def is_head(self, node):
      if node in self._loop_heads:
        return self._loop_heads[node] > 0
      else:
        return False

    def is_back_edge(self, node):
      if node in self._loop_back_edges:
        return self._loop_back_edges[node] > 0
      else:
        return False

    def is_loop(self, head, back_edge):
      return (head in self._loop_heads and 
              back_edge in self._loop_back_edges and
              self._loop_heads[head] > 0 and
              self._loop_back_edges[back_edge] > 0 and
              (head, back_edge) in self._loops and
              back_edge in self._fwd and
              head in self._bwd)

    def remove_loop(self, head, back_edge):
      # loop should already be here...
      self._loops.remove( (head, back_edge) )

      self._loop_heads[head] = self._loop_heads[head] - 1
      self._loop_back_edges[back_edge] = self._loop_back_edges[back_edge] - 1

      found = None
      for e in self._fwd[back_edge]:
        if (e.from_node == back_edge and e.to_node == head):
          found = e
      assert not found is None
      self._fwd[back_edge].remove(found)

      found = None
      for e in self._bwd[head]:
        if (e.from_node == back_edge and e.to_node == head):
          found = e
      assert not found is None
      self._bwd[head].remove(found)

    def get_next(self, node):
      branches = []
      for e in self._fwd[node]:
        if not (node, e.from_node) in self._loops:
          branches.append(e.to_node)
      assert len(branches) == 1
      return branches[0]

    def get_if_branches(self, node):
      branches = []
      for e in self._fwd[node]:
        if not (node, e.from_node) in self._loops:
          branches.append(e.to_node)
      assert len(branches) == 2
      return (branches[0], branches[1])

class CFGAnalyzer(object):
  def __init__(self, acdfg, root_node):
    super(CFGAnalyzer, self).__init__()
    self.acdfg = acdfg
    self.root = root_node
    self._fwd = {}
    self._bwd = {}
    self._dom = None # on demand

    # Fill the forward and backward relation
    for c in self.acdfg._control:
      self._fwd[c] = []
      self._bwd[c] = []

    edge_types = {Edge.Type.CONTROL, Edge.Type.TRANS}
    for e in self.acdfg._edges:
      if (e.from_node in self.acdfg._control and
          e.to_node in self.acdfg._control and
          # remove self loops
          e.from_node != e.to_node and
          # remove non control edges
          e.edge_type in edge_types):

        self._fwd[e.from_node].append(e.to_node)
        self._bwd[e.to_node].append(e.from_node)

    self._reachable = self._reachable_dfs(self.root)

    def shrink_map(map_to_shrink):
      """ Reduce the map to the reachable states """
      new_map = {}
      for node, node_list in map_to_shrink.iteritems():
        if node in self._reachable:
          new_list = []
          for c in node_list:
            if c in self._reachable:
              new_list.append(c)
          new_map[node] = new_list
      return new_map

    self._fwd = shrink_map(self._fwd)
    self._bwd = shrink_map(self._bwd)


  def _build_dominator_relation(self):
    # map from node i to the set of nodes that
    # dominates i
    dom = {}

    # Init the domination relation
    # only root dominates itself
    dom[self.root] = {self.root}
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

    return dom

  def _print_map(self, dom):
    for key, values in dom.iteritems():
      print("%s : [%s]" % (str(key.id),
                           ",".join([str(m.id) for m in values])))

  def get_loops(self):
    # Loops store (head_node, back_node, body_nodes)
    loops = set()

    if self._dom is None:
      self._dom = self._build_dominator_relation()

    for node in self._reachable:
      for dominator in self._dom[node]:
        if dominator in self._fwd[node]:
          # we have a back edge from node to dominator
          body_nodes = self._reachable_from(node, True, dominator)
          loops.add( (dominator, node, frozenset(body_nodes)) )
    return loops

  def _reachable_dfs(self, node, bwd=False):
    reachable = set()
    to_visit = [node]

    rel = self._bwd if bwd else self._fwd

    while len(to_visit) > 0:
      current = to_visit.pop()
      if current in reachable: continue

      reachable.add(current)

      for reach_node in rel:
        to_visit.append(reach_node)

    return reachable

  def _reachable_from(self, node, bwd, target):
    reachable_dir1 = self._reachable_dfs(node, bwd)
    reachable_dir2 = self._reachable_dfs(target, not bwd)

    reachable_dir1.intersection_update(reachable_dir2)

    return reachable_dir1


class PatternAST(object):
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
    def __init__(self, message):
        super(PatternAST.MalformedASTException, self).__init__(message)
        # self.errors = errors

  class NodeType(Enum):
    VAR = 0
    CONST = 1
    METHOD = 2
    ASSIGN = 3
    SEQ = 4
    IF = 5
    WHILE = 6

  INDENT = "  "

  CMD_TYPES = {NodeType.METHOD, NodeType.ASSIGN, NodeType.SEQ,
               NodeType.IF, NodeType.WHILE}
  EXPR_TYPES = {NodeType.VAR, NodeType.CONST}

  DATA_MAP = {"name" : {NodeType.VAR, NodeType.CONST},
              "method_name" : {NodeType.METHOD}}

  def __init__(self, ast_type):
    super(PatternAST, self).__init__()
    self.ast_type = ast_type
    self.data = {}
    self.children = []

  def _val_data(self, field_name):
    if field_name in PatternAST.DATA_MAP:
      return self.ast_type in PatternAST.DATA_MAP[field_name]
    else:
      err = "Unkonwn %s field" % field_name
      raise PatternAST.MalformedASTException(err)

  def _val_children(self, children):
    len_c = len(children)

    if self.ast_type in {PatternAST.NodeType.SEQ, PatternAST.NodeType.IF,
                         PatternAST.NodeType.WHILE}:
      for c in children:
        if c is None:
          raise PatternAST.MalformedASTException("None children!")

        if not c.is_cmd():
          raise PatternAST.MalformedASTException("%s must be a command!" % str(c))

      if self.ast_type in {PatternAST.NodeType.SEQ, PatternAST.NodeType.IF}:
        if len_c != 2:
          err = "Node must have 2 children, %d given!" % len_c
          raise PatternAST.MalformedASTException(err)
      elif self.ast_type == PatternAST.NodeType.WHILE:
        if len_c != 1:
          err = "Node must have 1 children, %d given!" % len_c
          raise PatternAST.MalformedASTException(err)

    elif self.ast_type in {PatternAST.NodeType.ASSIGN}:
      if len_c != 2:
          err = "Node must have 2 children, %d given!" % len_c
          raise PatternAST.MalformedASTException(err)
      elif children[0].ast_type != PatternAST.NodeType.VAR:
        err = "Node %s must be a var!" % str(c)
        raise PatternAST.MalformedASTException(err)
      elif children[1].ast_type != PatternAST.NodeType.METHOD:
        err = "Node %s must be a method!" % str(c)
        raise PatternAST.MalformedASTException(err)

    elif self.ast_type in {PatternAST.NodeType.METHOD}:
      for c in children:
        if (not c is None) and (not c.is_expr()):
          err = "Node %s must be an expression!" % str(c)
          raise PatternAST.MalformedASTException(err)

    elif self.is_expr():
      if len_c != 0:
        err = "Node must have 0 children, %d given!" % len_c
        raise PatternAST.MalformedASTException(err)

    else:
      # Unknonw type
      err = "Unkonwn node type!"
      raise PatternAST.MalformedASTException(err)

  def _set_data(self, field_name, value):
    assert self._val_data(field_name)
    self.data[field_name] = value

  def _get_data(self, field_name):
    self._val_data(field_name)
    return self.data[field_name]

  def set_children(self, children):
    self._val_children(children)
    self.children = [c for c in children]

  def is_cmd(self):
    return self.ast_type in PatternAST.CMD_TYPES

  def is_expr(self):
    return self.ast_type in PatternAST.EXPR_TYPES

  def _print(self, out_stream, indent):
    if (self.ast_type in {PatternAST.NodeType.VAR, PatternAST.NodeType.CONST}):
      out_stream.write("%s%s" % (indent, self._get_data("name")))
    elif (self.ast_type == PatternAST.NodeType.METHOD):
      out_stream.write("%s%s(" % (indent, self._get_data("method_name")))

      first = True
      for c in self.children:
        if not first:
          c._print(out_stream, ", ")
        c._print(out_stream, "")
        first = False
      out_stream.write(")")

    elif (self.ast_type == PatternAST.NodeType.ASSIGN):
      self.children[0]._print(out_stream, indent)
      out_stream.write(" = ")
      self.children[1]._print(out_stream, "")
    elif (self.ast_type == PatternAST.NodeType.SEQ):
      self.children[0]._print(out_stream, indent)
      out_stream.write(";\n")
      self.children[1]._print(out_stream, indent)
    elif (self.ast_type == PatternAST.NodeType.IF):
      out_stream.write("%sif (*) {\n" % indent)
      self.children[0]._print(out_stream, indent + PatternAST.INDENT)
      out_stream.write("\n%selse (*) {" % indent)
      self.children[1]._print(out_stream, indent + PatternAST.INDENT)
      out_stream.write("\n%s}\n" % indent)
    elif (self.ast_type == PatternAST.NodeType.WHILE):
      out_stream.write("%swhile(*) {\n" % indent)
      self.children[0]._print(out_stream, indent + PatternAST.INDENT)
      out_stream.write("\n%s}\n" % indent)
    else:
      assert False

  def __repr__(self):
    output = StringIO.StringIO()
    self._print(output, "")
    return output.getvalue()

