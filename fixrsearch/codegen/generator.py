"""
Utilities to transform acdfgs and mappings to to code
"""


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

  PROCESS_SEQ_COUNTER = 0

  def __init__(self, sliced_acdfg, original_acdfg):
    self.sliced_acdfg = sliced_acdfg
    self.original_acdfg = original_acdfg

    # Show only the original control edges
    self._fix_control_edges()

    v2n = {}
    c2n = {}
    CodeGenerator.rename_vars(self.original_acdfg, v2n, c2n)
    CodeGenerator.rename_vars(self.sliced_acdfg, v2n, c2n)

  def get_code_text(self):
    ast = self._get_ast()
    return str(ast)

  def _get_ast(self):
    """ Construct an AST representing the graph control flow """
    roots = self.sliced_acdfg.find_control_roots()

    if (len(roots) == 0):
      myroot = self.sliced_acdfg.find_first_control_node()
      roots.add(myroot)
      self.sliced_acdfg.remove_incoming(myroot)

    # visit the graph from the root generating the AST
    code_ast = None
    for root in roots:
       cfg_analyzer = CFGAnalyzer(self.sliced_acdfg, root)
       loops = cfg_analyzer.get_loops()

       root_ast = self._get_node_ast(self.sliced_acdfg, root, loops)
       if code_ast is None:
         code_ast = root_ast
       else:
         app_ast = PatternAST(PatternAST.NodeType.IF)
         app_ast.set_children([code_ast, root_ast])
         code_ast = app_ast

    main_ast = self.get_pattern_func_def(cfg_analyzer, code_ast)

    return main_ast

  def _get_node_ast(self, acdfg, root, loops):
    # print "GET NODE _AST"
    """ get the ast for the root node """
    helper = CodeGenerator.Helper(acdfg, loops)

    # get the body of the pattern
    control_ast = self._get_node_ast_rec(acdfg, root,
                                         helper, [], set())

    # add definition of variables
    ast = control_ast
    to_declare = set()
    for control_node, data_node_set in helper._def_nodes.iteritems():
      for data_node in data_node_set:
        if data_node.data_type == DataNode.DataType.VAR:
          to_declare.add(data_node)

    for data_node in to_declare:
      type_ast = PatternAST(PatternAST.NodeType.CONST)
      type_ast._set_data("name", data_node.node_type)
      data_ast = CodeGenerator.get_expression_ast(data_node)
      decl_ast = PatternAST(PatternAST.NodeType.DECL)
      decl_ast.set_children([type_ast,data_ast])
      seq_ast = PatternAST(PatternAST.NodeType.SEQ)
      seq_ast.set_children([decl_ast, ast])
      ast = seq_ast

    return ast

  def _get_node_ast_rec(self,
                        acdfg,
                        node,
                        helper,
                        stack,
                        visited,
                        force_visit = False):
    """ Returns the ast node for the the
    cfg node and the next cfg node to process
    in sequence.
    """
    # Process "base cases", when the recursion
    # must stop
    if helper.is_tail(node) and helper.is_join(node) and not force_visit:
      stack.append(node)
      return None
    if helper.is_tail(node):
      expr_ast = CodeGenerator.get_expression_ast_method(helper, node)
      return expr_ast
    elif helper.is_join(node) and not force_visit:
      stack.append(node)
      # Nothing to append to the previous nodes
      # join node processed once
      return None
    elif helper.is_back_edge(node):
      expr_ast = CodeGenerator.get_expression_ast_method(helper, node)
      stack.append(node)
      return expr_ast

    # Get the base expression for the node
    expr_ast = CodeGenerator.get_expression_ast_method(helper, node)

    is_loop = helper.is_head(node)
    is_if = helper.is_if(node) 
    is_seq = helper.is_seq(node)

    assert ((not is_seq) or not is_if)
    assert ((not is_if) or not is_seq)

    if is_if:
      (if_ast, rest_ast) = self._process_if(acdfg,
                                            node,
                                            helper,
                                            stack,
                                            visited)
    elif is_seq:
      rest_ast = self._process_seq(acdfg,
                                   node,
                                   helper,
                                   stack,
                                   visited)

    if not is_loop:
      # Done, concatenate the rest with the node
      if is_if:
        if not rest_ast is None:
          app_ast = PatternAST(PatternAST.NodeType.SEQ)
          app_ast.set_children([if_ast, rest_ast])
        else:
          app_ast = if_ast
        seq_ast = PatternAST(PatternAST.NodeType.SEQ)
        seq_ast.set_children([expr_ast, app_ast])
        expr_ast = seq_ast
      elif is_seq:
        seq_ast = PatternAST(PatternAST.NodeType.SEQ)
        assert not expr_ast is None
        if (not rest_ast is None):
          seq_ast.set_children([expr_ast, rest_ast])
          expr_ast = seq_ast
        else:
          # Just to be explicit
          expr_ast = expr_ast
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
                                          stack,
                                          visited)
        assert not rest_ast is None
      elif helper.is_if(loop_tail_node):
        (if_ast, rest_ast) = self._process_if(acdfg,
                                              loop_tail_node,
                                              helper,
                                              stack,
                                              visited)
        assert not rest_ast is None
      elif helper.is_seq(loop_tail_node):
        rest_ast = self._process_seq(acdfg,
                                     loop_tail_node,
                                     helper,
                                     stack,
                                     visited)
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

  def get_pattern_func_def(self, cfg_analyzer, body):
    (params, to_decl) = cfg_analyzer.get_vars_to_decl();

    param_decl_ast = PatternAST(PatternAST.NodeType.VAR_DECL_LIST)
    params_ast = []
    for p in params:
      params_ast.append(CodeGenerator.get_expression_decl_ast(p))
    param_decl_ast.set_children(params_ast)


    method_body_ast = body
    for v in to_decl:
      seq = PatternAST(PatternAST.NodeType.SEQ)
      seq.set_children([CodeGenerator.get_expression_decl_ast(v),
                        method_body_ast])
      method_body_ast = seq

    method_decl_node = PatternAST(PatternAST.NodeType.METHOD_DECL)
    method_decl_node.set_children([param_decl_ast, method_body_ast])
    return method_decl_node

  @staticmethod
  def get_expression_ast(node):
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
        invokee_ast = CodeGenerator.get_expression_ast(node.invokee)
        children.append(invokee_ast)
      for c in node.arguments:
        p_ast = CodeGenerator.get_expression_ast(c)
        children.append(p_ast)
      ast._set_data("method_name", node.name)
      ast.set_children(children)

      if (not node.assignee is None):
        assignee_ast = CodeGenerator.get_expression_ast(node.assignee)
        assign_ast = PatternAST(PatternAST.NodeType.ASSIGN)
        assign_ast.set_children([assignee_ast, ast])
        ast = assign_ast

      return ast
    else:
      assert False

  @staticmethod
  def get_expression_decl_ast(node):
    assert isinstance(node, DataNode)
    assert node.data_type == DataNode.DataType.VAR

    var_name = PatternAST(PatternAST.NodeType.VAR)
    var_name._set_data("name", node.name)

    var_type = PatternAST(PatternAST.NodeType.CONST)
    var_type._set_data("name", node.node_type)

    var_decl = PatternAST(PatternAST.NodeType.DECL)
    var_decl.set_children([var_type, var_name])

    return var_decl

  @staticmethod
  def get_expression_ast_method(helper, node):
    if helper.has_self_loop(node):
      node_ast = CodeGenerator.get_expression_ast(node)
      # Generate self-loop
      loop_ast = PatternAST(PatternAST.NodeType.WHILE)
      loop_ast.set_children([node_ast])
      return loop_ast
    else:
      return CodeGenerator.get_expression_ast(node)


  def _process_seq(self, acdfg, node, helper, stack, visited):
    CodeGenerator.PROCESS_SEQ_COUNTER += 1
    next_node = helper.get_next(node)
    rest_ast = self._get_node_ast_rec(acdfg,
                                      next_node,
                                      helper,
                                      stack,
                                      visited)
    return rest_ast


  def _process_if(self, acdfg, node, helper, stack, visited):
    # Creates the AST for the two branches
    (left_node, right_node) = helper.get_if_branches(node)

    left_ast = self._get_node_ast_rec(acdfg,
                                      left_node,
                                      helper,
                                      stack,
                                      visited)
    assert len(stack) > 0
    join_node_left = stack.pop()

    right_ast = self._get_node_ast_rec(acdfg,
                                       right_node,
                                       helper,
                                       stack,
                                       visited)
    assert len(stack) > 0
    join_node_right = stack.pop()

    # The join must be the same
    assert ((not join_node_left is None) and
            (join_node_left == join_node_right or
             right_ast.ast_type == PatternAST.NodeType.SKIP or
             left_ast.ast_type == PatternAST.NodeType.SKIP))

    # May not work if join is not on a leaf
    #
    if (left_node == join_node_left):
      assert (right_node != join_node_right)
      rest_ast = self._get_node_ast_rec(acdfg,
                                        join_node_left,
                                        helper,
                                        stack,
                                        visited,
                                        True)
      left_ast = PatternAST(PatternAST.NodeType.SKIP)
    elif (right_node == join_node_right):
      assert (left_node != join_node_left)
      rest_ast = self._get_node_ast_rec(acdfg,
                                        join_node_right,
                                        helper,
                                        stack,
                                        visited,
                                        True)
      right_ast = PatternAST(PatternAST.NodeType.SKIP)
    else:
      rest_ast = self._get_node_ast_rec(acdfg,
                                        join_node_left,
                                        helper,
                                        stack,
                                        visited)

    if_ast = PatternAST(PatternAST.NodeType.IF)
    if_ast.set_children([left_ast, right_ast])

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

    def __init__(self, acdfg, loops, just_control = False):
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
      #
      self._nodes_with_self_loops = set()

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

        if (not just_control):
          if (e.edge_type in {Edge.Type.TRANS,
                              Edge.Type.EXCEPTIONAL}):
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
      # For self loops:
      #   - we remove the self-loops, but remember about them
      #   - when getting the expression for a node, we generate a
      #     while loop for the single expression.
      #
      # This is a special case and kind of a ad-hoc hack for
      # self loops.
      for (head, back_edge, body_nodes) in loops:
        if head == back_edge and len(body_nodes) == 1:
          self._nodes_with_self_loops.add(head)
        else:
          self._loops.add( (head, back_edge) )

          count = self._loop_heads[head] if head in self._loop_heads else 0
          self._loop_heads[head] = count + 1

          if back_edge in self._loop_back_edges:
            count = self._loop_back_edges[back_edge]
          else:
            count = 0
          self._loop_back_edges[back_edge] = count + 1

      # remove fwd and bwd edges due to self loops
      for node in self._nodes_with_self_loops:
        new_fwd = set()
        for edge in self._fwd[node]:
          if edge.to_node != node:
            new_fwd.add(edge)
        self._fwd[node] = new_fwd

        new_bwd = set()
        for edge in self._bwd[node]:
          if edge.from_node != node:
            new_bwd.add(edge)
        self._bwd[node] = new_bwd

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

    def has_self_loop(self, node):
      return node in self._nodes_with_self_loops

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

    def get_all_successors(self, node):
      return list(self._fwd[node])


  @staticmethod
  def rename_vars(acdfg,
                  acdfg_to_var,
                  acdfg_to_const):
    prefix = "tmp"
    counter = -1

    for v in acdfg._data:
      if (v.data_type == DataNode.DataType.VAR):
        if (not v.name in acdfg_to_var):
          counter += 1
          new_val = "%s_%d" % (prefix, counter)
          acdfg_to_var[v.name] = new_val
          v.name = new_val
        else:
          v.name = acdfg_to_var[v.name]

      if (v.data_type == DataNode.DataType.CONST and
          v.node_type == "java.lang.String"):
        if (not v.name in acdfg_to_const):
          new_val = "\"\""
          acdfg_to_const[v.name] = new_val
          v.name = new_val
        else:
          v.name = acdfg_to_const[v.name]

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
          # e.from_node != e.to_node and
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
          if dominator == node:
            body_nodes = {dominator,node}
          else:
            body_nodes = self._reachable_from(node, True, dominator)
          loops.add( (dominator, node, frozenset(body_nodes)) )
    return loops

  def get_vars_to_decl(self):
    # Get a list of variables that are read but
    # not assigned in the cfgs
    #
    # Works under the assumption vars "are in SSA" form
    params = set()
    vars_to_decl =set()
    for e in self.acdfg._edges:
      if (e.edge_type == Edge.Type.USE and
          e.from_node.data_type == DataNode.DataType.VAR):
        e.from_node in self.acdfg._data
        params.add(e.from_node)

    for e in self.acdfg._edges:
      if (e.edge_type == Edge.Type.DEF_EDGE and
          e.to_node.data_type == DataNode.DataType.VAR):
        e.to_node in self.acdfg._data
        vars_to_decl.add(e.to_node)
        if e.to_node in params:
          params.remove(e.to_node)

    return (params, vars_to_decl)

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
         | type var;
         | return
         | cmd ; cmd
         | if * then cmd else cmd
         | while * do cmd
         | void method(type_var, ..., type_var)
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
    DECL = 7
    SKIP = 8
    RETURN = 9
    METHOD_DECL = 10
    VAR_DECL_LIST = 11

  INDENT = "  "
  HAVOC_COND = "?"
  HAVOC_VAR = ""
  PATTERN_NAME = "pattern"

  CMD_TYPES = {NodeType.METHOD, NodeType.ASSIGN, NodeType.SEQ,
               NodeType.IF, NodeType.WHILE, NodeType.DECL,
               NodeType.SKIP, NodeType.RETURN}
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

    if self.ast_type in {PatternAST.NodeType.SEQ,
                         PatternAST.NodeType.IF,
                         PatternAST.NodeType.WHILE}:
      for c in children:
        if c is None:
          raise PatternAST.MalformedASTException("None children!")

        if not c.is_cmd():
          raise PatternAST.MalformedASTException("%s must be a " \
                                                 "command!" % str(c))

      if self.ast_type in {PatternAST.NodeType.SEQ, PatternAST.NodeType.IF}:
        if len_c != 2:
          err = "Node must have 2 children, %d given!" % len_c
          raise PatternAST.MalformedASTException(err)
      elif self.ast_type == PatternAST.NodeType.WHILE:
        if len_c != 1:
          err = "Node must have 1 children, %d given!" % len_c
          raise PatternAST.MalformedASTException(err)

    elif self.ast_type in {PatternAST.NodeType.METHOD_DECL}:
      for c in children:
        if c is None:
          raise PatternAST.MalformedASTException("None children!")

      if children[0].ast_type != PatternAST.NodeType.VAR_DECL_LIST:
        err = "No param list for method declaration!"
        raise PatternAST.MalformedASTException(err)
      if not children[1].is_cmd():
        raise PatternAST.MalformedASTException("%s must be a " \
                                               "command!" % str(c))

    elif self.ast_type in {PatternAST.NodeType.VAR_DECL_LIST}:
      for c in children:
        if c is None:
          raise PatternAST.MalformedASTException("None children!")

        if c.ast_type != PatternAST.NodeType.DECL:
          err = "%s is not var a declaration!" % str(c)
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

    elif self.ast_type in {PatternAST.NodeType.DECL}:
      if len_c != 2:
        err = "Node must have 2 children, %d given!" % len_c
        raise PatternAST.MalformedASTException(err)
      elif children[0].ast_type != PatternAST.NodeType.CONST:
        err = "Node %s must be a const!" % str(c)
        raise PatternAST.MalformedASTException(err)
      elif children[1].ast_type != PatternAST.NodeType.VAR:
        err = "Node %s must be a var!" % str(c)
        raise PatternAST.MalformedASTException(err)

    elif (self.ast_type == PatternAST.NodeType.SKIP or
          self.ast_type == PatternAST.NodeType.RETURN):
      if len_c != 0:
        err = "Node must have 0 children, %d given!" % len_c
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

  def _print(self, out_stream, indent, inline_decl = False):
    if (self.ast_type in {PatternAST.NodeType.SKIP}):
      out_stream.write("%s// skip\n" % (indent))
    elif (self.ast_type in {PatternAST.NodeType.RETURN}):
      out_stream.write("%s%s" % (indent, "return;\n"))
    elif (self.ast_type in {PatternAST.NodeType.VAR,
                            PatternAST.NodeType.CONST}):
      out_stream.write("%s%s" % (indent, self._get_data("name").strip()))
    elif (self.ast_type == PatternAST.NodeType.METHOD):
      out_stream.write("%s%s(" % (indent, self._get_data("method_name")))

      first = True
      for c in self.children:
        if not first:
          c._print(out_stream, ", ")
        else:
          c._print(out_stream, "")
        first = False
      out_stream.write(");\n")

    elif (self.ast_type in {PatternAST.NodeType.DECL}):
      out_stream.write("%s" % (indent))
      self.children[0]._print(out_stream, "")
      out_stream.write(" ")
      self.children[1]._print(out_stream, "")
      if not inline_decl:
        out_stream.write(";\n")
    elif (self.ast_type == PatternAST.NodeType.ASSIGN):
      self.children[0]._print(out_stream, indent)
      out_stream.write(" = ")
      self.children[1]._print(out_stream, "")
    elif (self.ast_type == PatternAST.NodeType.SEQ):
      self.children[0]._print(out_stream, indent)
      self.children[1]._print(out_stream, indent)
    elif (self.ast_type == PatternAST.NodeType.IF):
      out_stream.write("%sif (%s) {\n" % (indent, PatternAST.HAVOC_COND))
      self.children[0]._print(out_stream, indent + PatternAST.INDENT)
      out_stream.write("%selse {\n" % (indent))
      self.children[1]._print(out_stream, indent + PatternAST.INDENT)
      out_stream.write("%s}\n" % indent)
    elif (self.ast_type == PatternAST.NodeType.WHILE):
      out_stream.write("%swhile (%s) {\n" % (indent, PatternAST.HAVOC_COND))
      self.children[0]._print(out_stream, indent + PatternAST.INDENT)
      out_stream.write("%s}\n" % indent)
    elif (self.ast_type == PatternAST.NodeType.METHOD_DECL):
      out_stream.write("%svoid %s (" % (indent, PatternAST.PATTERN_NAME))
      self.children[0]._print(out_stream, indent)
      out_stream.write(") {\n")
      self.children[1]._print(out_stream, indent + PatternAST.INDENT)
      out_stream.write("%s}\n" % indent)
    elif (self.ast_type == PatternAST.NodeType.VAR_DECL_LIST):
      first = True
      for c in self.children:
        if not first:
          out_stream.write(", ")
        c._print(out_stream, indent, True)
        first = False
    else:
      assert False

  def __repr__(self):
    output = StringIO.StringIO()
    self._print(output, "")
    return output.getvalue()

