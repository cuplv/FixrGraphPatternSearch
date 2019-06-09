from fixrgraph.annotator.protobuf.proto_acdfg_pb2 import Acdfg as AcdfgProto
from fixrgraph.annotator.protobuf.proto_search_pb2 import SearchResults
from enum import Enum

class Node(object):
  def __init__(self, node_id):
    super(Node, self).__init__()
    self.id = node_id

    def __eq__(self, other):
      return (type(self) == type(other) and
              self.id == other.id)

class MethodNode(Node):
  def __init__(self, node_id,
               assignee, invokee,
               name,
               arguments):
    super(MethodNode, self).__init__(node_id)

    self.assignee = assignee
    self.invokee = invokee
    self.name = name
    self.arguments = [l for l in arguments]

  def __eq__(self, other):
    eq = (type(self) == type(other) and
          self.id == other. id and
          self.assignee == other.assignee and
          self.invokee == other.invokee and
          self.name == other.name)
    if not eq:
      return False
    elif len(self.arguments) != len(other.arguments):
      return False
    else:
      for a,b in zip(self.arguments, other.arguments):
        if not (a == b):
          return False
    return True

class DataNode(Node):
  class DataType(Enum):
    VAR = 0
    CONST = 1

  def __init__(self, node_id, name, node_type, data_type):
    super(DataNode, self).__init__(node_id)
    self.name = name
    self.node_type = node_type
    self.data_type = data_type

  def __eq__(self, other):
    return (type(self) == type(other) and
            self.id == other.id and
            self.name == other.name and
            self.node_type == other.node_type and
            self.data_type == other.data_type)


class MiscNode(Node):
  def __init__(self, node_id):
    super(MiscNode, self).__init__(node_id)

class Edge(object):
  class Type(Enum):
    CONTROL = 0
    DEF_EDGE = 1
    USE = 2
    TRANS = 4
    EXCEPTIONAL = 5

  def __init__(self, edge_id, from_node, to_node, edge_type):
    super(Edge, self).__init__()
    self.id = edge_id
    self.from_node = from_node
    self.to_node = to_node
    self.edge_type = edge_type

  def __eq__(self, other):
    return (type(self) == type(other) and
            self.id == other.id and
            self.edge_type == other.edge_type and
            self.from_node == other.from_node and
            self.to_node == other.to_node)


class AcdfgRepr(object):
  def _add_node(self, node):
    self._nodes.append(node)
    if not isinstance(node, DataNode):
      self._control.append(node)
    else:
      self._data.append(node)
    self._id2node[node.id] = node

  def __init__(self, acdfgProto):
    self._nodes = []
    self._control = []
    self._data = []
    self._edges = []
    self._id2node = {}

    for node_prot in acdfgProto.data_node:
      if node_prot.data_type == AcdfgProto.DataNode.DATA_VAR:
        node_type = DataNode.DataType.VAR
      else:
        node_type = DataNode.DataType.CONST

      node_repr = DataNode(node_prot.id,
                           node_prot.name,
                           node_prot.type,
                           node_type)
      self._add_node(node_repr)

    for node_prot in acdfgProto.misc_node:
      self._add_node(MiscNode(node_prot.id))

    for node_prot in acdfgProto.method_node:
      assignee = None
      invokee = None
      if node_prot.HasField("assignee"):
        assignee = self._id2node[node_prot.assignee]
      if node_prot.HasField("invokee"):
        invokee = self._id2node[node_prot.invokee]

      children = []
      for n in node_prot.argument:
        child = self._id2node[n]
        assert not child is None
        children.append(child)

      node_repr = MethodNode(node_prot.id, assignee, invokee,
                             node_prot.name, children)
      self._add_node(node_repr)

    for (l,t) in [(acdfgProto.control_edge, Edge.Type.CONTROL),
                  (acdfgProto.def_edge, Edge.Type.DEF_EDGE),
                  (acdfgProto.use_edge, Edge.Type.USE),
                  (acdfgProto.trans_edge, Edge.Type.TRANS),
                  (acdfgProto.exceptional_edge, Edge.Type.EXCEPTIONAL)]:
      for e in l:
        new_edge = Edge(e.id,
                        self._id2node[getattr(e,'from')],
                        self._id2node[e.to], t)
        self._edges.append(new_edge)

  def escape(self, s):
    s.replace("\"", "\\\'")

  def get_node_label(self, node):
      if isinstance(node, DataNode):
        return "  shape=ellipse,color=red,style=dashed,label=\"DataNode #" \
          "%s: %s  %s\"" % (str(node.id), node.data_type, self.escape(node.name))
      elif isinstance(node, MethodNode):
        label = "  shape=box, style=filled, color=lightgray, label=\"%s[" % node.name ;

        if not node.invokee is None:
          label += "#%s" % str(node.invokee.id)
        label += "])"

        args = ["#%s" % l.id for l in node.arguments]
        label += ",".join(args)
        label += ")\""
        return label
      else:
        return "label=\"#%s\"" % str(node.id)

  def _get_dot_edge_style(self, edge):
    style = {
      Edge.Type.CONTROL : "[color=black, penwidth=3]",
      Edge.Type.DEF_EDGE : "[color=blue, penwidth=2]",
      Edge.Type.USE : "[color=green, penwidth=2]",
      Edge.Type.TRANS : "[color=black, penwidth=3]",
      Edge.Type.EXCEPTIONAL : "[color=red, penwidth=3]",
    }
    return style[edge.edge_type]

  def find_control_roots(self):
    """ Get all the control nodes without incoming edges """
    roots = set()
    for n in self._control:
      roots.add(n)

    for e in self._edges:
      # must be a control node
      if e.to_node in roots and e.from_node in self._control:
        roots.remove(e.to_node)
    return roots

  def print_dot(self, out_stream, filter_set = {Edge.Type.TRANS,
                                                Edge.Type.EXCEPTIONAL}):
    """ Print the dot representation of the acdfg """

    out_stream.write("digraph isoX {\n")
    out_stream.write(" node[shape=box,style=\"filled,rounded\",penwidth=2.0,"\
                     "fontsize=13,]; \n " \
                     "  edge[arrowhead=onormal,penwidth=2.0,]; \n")

    for node in self._nodes:
      str_node = self.get_node_label(node)
      out_node = "\"n_%s\" [%s];\n" % (str(node.id), str_node)
      out_stream.write(out_node)

    for edge in self._edges:
      if edge.edge_type in filter_set:
        continue

      edge_dot_style = self._get_dot_edge_style(edge)
      out_edge = "\"n_%s\" -> \"n_%s\"%s ;\n" % (str(edge.from_node.id),
                                                 str(edge.to_node.id),
                                                 edge_dot_style)
      out_stream.write(out_edge)

    out_stream.write(" }\n")


  def get_slice_edges(self, nodes_to_keep):
    """ Finds the control (and not transitive) edges that
    be part of the slice.

    These are the edges that we want to show.
    """

    fwd = {}
    bwd = {}
    for n in self._nodes:
      fwd[n] = set()
      bwd[n] = set()
    for e in self._edges:
      if e.edge_type == Edge.Type.CONTROL:
        fwd[e.from_node].add(e.to_node)
        bwd[e.to_node].add(e.from_node)

    to_proc = []
    for n in self._nodes:
      found = False # different nodes, no hash, use eq
      for n2 in nodes_to_keep:
        if n == n2:
          found = True
          break
      if not found:
        to_proc.append(n)

    while len(to_proc) > 0:
      node = to_proc.pop()

      # remove self loops on nodes that we
      # do not want
      if node in fwd[node]:
        fwd[node].remove(node)
      if node in bwd[node]:
        bwd[node].remove(node)

      # Add edge to skip node
      for other1 in bwd[node]:
        if not other1 == node:
          for other2 in fwd[node]:
            if not other2 == node:
              fwd[other1].add(other2)
              bwd[other2].add(other1)
        if node in fwd[other1]:
          fwd[other1].remove(node)

      for other2 in fwd[node]:
        if node in bwd[other2]:
          bwd[other2].remove(node)

      del fwd[node]
      del bwd[node]

    edges = set()
    for node1, successors in fwd.iteritems():
      for s in successors:
        edges.add((node1.id, s.id))

    return edges
