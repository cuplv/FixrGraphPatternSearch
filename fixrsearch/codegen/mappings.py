from fixrsearch.codegen.acdfg_repr import (
  AcdfgRepr,
  Node, MethodNode, DataNode, MiscNode, Edge
)

import logging

class Mappings():
  IN_A = "A"
  IN_B = "B"
  NODES = "nodes"
  EDGES = "edges"

  def __init__(self, acdfg_a=None, acdfg_b=None,
               iso_from_a_to_b = None):
    self._id_maps = {}
    self._isos = []
    self._just_a = []
    self._just_b = []

    self._is_iso_a = None
    self._is_iso_b = None

    if (acdfg_a is None or acdfg_b is None or iso_from_a_to_b is None):
      return

    assert isinstance(acdfg_a, AcdfgRepr)
    assert isinstance(acdfg_b, AcdfgRepr)

    for (acdfg, in_something) in zip([acdfg_a, acdfg_b],
                                     [Mappings.IN_A, Mappings.IN_B]):
      self._id_maps[in_something] = {}
      self._id_maps[in_something][Mappings.NODES] = {}
      self._id_maps[in_something][Mappings.EDGES] = {}

      self._fill_map(acdfg, in_something)

    self._compute_assocs(acdfg_a, acdfg_b, iso_from_a_to_b)

  def init_from_others(self, a_to_b_mapping, c_iso_to_b_mapping):
    """ specific constructor, requires that c is isomorphic
    to b (i.e., no unmapped nodes or edges)

    Build a mapping from a to c.
    """
    assert c_iso_to_b_mapping.is_iso()

    # copy the _id_maps
    self._id_maps = {}
    for (mapping, in_something) in zip([a_to_b_mapping._id_maps[Mappings.IN_A],
                                        c_iso_to_b_mapping._id_maps[Mappings.IN_A]],
                                       [Mappings.IN_A, Mappings.IN_B]):

      self._id_maps[in_something] = {}
      self._id_maps[in_something][Mappings.NODES] = mapping[Mappings.NODES].copy()
      self._id_maps[in_something][Mappings.EDGES] = mapping[Mappings.EDGES].copy()

    # map from b elem to c
    b_to_c = {}
    b_to_c[Mappings.NODES] = {}
    b_to_c[Mappings.EDGES] = {}
    for (c_elem, b_elem) in c_iso_to_b_mapping._isos:
      if self._is_node(c_elem):
        assert self._is_node(b_elem)
        b_to_c[Mappings.NODES][b_elem.id] = c_elem
      else:
        assert not self._is_node(b_elem)
        b_to_c[Mappings.EDGES][b_elem.id] = c_elem

    # set just a - copy a
    self._just_a = list(a_to_b_mapping._just_a)

    # set isos
    self._isos = []
    for (a_elem, b_elem) in a_to_b_mapping._isos:
      if self._is_node(b_elem):
        c_elem = b_to_c[Mappings.NODES][b_elem.id]
      else:
        c_elem = b_to_c[Mappings.EDGES][b_elem.id]
      self._isos.append( (a_elem, c_elem) )

    # set just b
    self._just_b = []
    for b_elem in a_to_b_mapping._just_b:
      if self._is_node(b_elem):
        c_elem = b_to_c[Mappings.NODES][b_elem.id]
      else:
        c_elem = b_to_c[Mappings.EDGES][b_elem.id]

      self._just_b.append( c_elem )

  def _is_node(self, elem):
    return (isinstance(elem, Node) or
            isinstance(elem, MethodNode) or
            isinstance(elem, DataNode) or
            isinstance(elem, MiscNode))

  def is_iso(self):
    return len(self._just_a) == 0 and len(self._just_b) == 0

  def get_lines(self, acdfg_a, node_lines_a,
                acdfg_b, node_lines_b):
    def get_node_lines(lines_a, lines_b, elem_a, elem_b):
      line_a = lines_a.get_line(elem_a)
      line_b = lines_b.get_line(elem_b)
      if (line_a is None or line_b is None):
        return None
      else:
        return (line_a, line_b)

    def get_edges_lines(lines_a, lines_b, edge_a, edge_b):
      edge_lines_a = lines_a.get_line(edge_a)
      edge_lines_b = lines_b.get_line(edge_b)

      if edge_lines_a is None or edge_lines_b is None:
        return None
      else:
        (line_a, line_b)

    assert isinstance(acdfg_a, AcdfgRepr)
    assert isinstance(acdfg_b, AcdfgRepr)

    lines_a = LineNum(node_lines_a)
    lines_b = LineNum(node_lines_b)

    # eq, missing in 1, to be removed in 1
    nodes_res = ([],[],[])
    edges_res = ([],[],[])

    for (elem_a, elem_b) in self._isos:
      if self._is_node(elem_a):
        assert self._is_node(elem_b)
        res = get_node_lines(lines_a, lines_b, elem_a, elem_b)
        if not res is None:
          nodes_res[0].append(res)
      else:
        assert not self._is_node(elem_a)
        assert not self._is_node(elem_b)

        res = get_edges_lines(lines_a, lines_b, elem_a, elem_b)
        if not res is None:
          edges_res[0].append(res)


    def insert_list(elem, lines, nodes_list, edges_list):
      if (self._is_node(elem)):
        assert self._is_node(elem)
        elem_line = lines.get_line(elem)
        if not elem_line is None:
          nodes_list.append(elem_line)
      else:
        assert not self._is_node(elem)
        res = lines.get_line(elem)
        if res is not None:
          edges_list.append(res)

    for elem_b in self._just_b:
      insert_list(elem_b, lines_b, nodes_res[1], edges_res[1])

    for elem_a in self._just_a:
      insert_list(elem_a, lines_a, nodes_res[2], edges_res[2])

    return (nodes_res, edges_res)


  def _fill_map(self, acdfg, in_something):
    assert isinstance(acdfg, AcdfgRepr)

    nodes_map = self._id_maps[in_something][Mappings.NODES]
    for node in acdfg._nodes:
      nodes_map[node.id] = node

    edges_map = self._id_maps[in_something][Mappings.EDGES]
    for edge in acdfg._edges:
      edges_map[edge.id] = edge

  def _all_obj(self, acdfg, common_ids):
    assert isinstance(acdfg, AcdfgRepr)

    all_obj = []

    for node in acdfg._nodes:
      if not node.id in common_ids[Mappings.NODES]:
        all_obj.append(node)
    for edge in acdfg._edges:
      if not edge.id in common_ids[Mappings.EDGES]:
        all_obj.append(edge)

    return all_obj

  def _compute_assocs(self, acdfg_a, acdfg_b, iso_from_a_to_b):
    self._isos = []

    common_ids_a = {}
    common_ids_b = {}

    for (id_pairs_list, what) in zip([iso_from_a_to_b.nodesMap,
                                      iso_from_a_to_b.edgesMap],
                                     [Mappings.NODES,
                                      Mappings.EDGES]):
      common_ids_a[what] = set()
      common_ids_b[what] = set()

      for id_pairs in id_pairs_list:
        id_a = id_pairs.id_1
        id_b = id_pairs.id_2

        common_ids_a[what].add(id_a)
        common_ids_b[what].add(id_b)

        if (id_a in self._id_maps[Mappings.IN_A][what]):
          elem_a = self._id_maps[Mappings.IN_A][what][id_a]
          if (id_b in self._id_maps[Mappings.IN_B][what]):
            elem_b = self._id_maps[Mappings.IN_B][what][id_b]

            self._isos.append((elem_a, elem_b))

          else:
            logging.debug("mappings: cannot find %s " \
                          "with id %d in acdfg a" % (what, id_b))
        else:
          logging.debug("mappings: cannot find %s " \
                        "with id %d in acdfg a" % (what, id_a))

    self._just_a = self._all_obj(acdfg_a, common_ids_a)
    self._just_b = self._all_obj(acdfg_b, common_ids_b)


  def is_iso_a(self, elem):
    if self._is_iso_a is None:
      self._is_iso_a = set()
      for (a,b) in self._isos:
        self._is_iso_a.add(a)

    return elem in self._is_iso_a

  def is_iso_b(self, elem):
    if self._is_iso_b is None:
      self._is_iso_b = set()
      for (a,b) in self._isos:
        self._is_iso_b.add(b)

    return elem in self._is_iso_b

class LineNum():
  def __init__(self, node_lines):
    self._id2line = {}
    for line_num in node_lines:
      self._id2line[line_num.id] = line_num.line

  def get_line(self, elem):
    if (isinstance(elem, Node) or
        isinstance(elem, MethodNode) or
        isinstance(elem, DataNode) or
        isinstance(elem, MiscNode)):
      if (elem.id in self._id2line):
        return self._id2line[elem.id]
      else:
        return None
    else:
      line_from = self.get_line(elem.from_node)
      line_to = self.get_line(elem.to_node)
      if (line_to is None or line_from is None):
        return None
      else:
        return (line_from, line_to)

  def get_copy(self):
    return self._id2line.copy();

