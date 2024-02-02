import itertools
import os
import sys
import json
import jsonlines
import random
from collections import defaultdict
from datetime import datetime as dt
from bmt import Toolkit


class TypeHandler:
    def __init__(self):
        self.type_to_descendants = self.create_type_to_descendants()
        self.deeptypescache={}
    def create_type_to_descendants(self):
        # Create a dictionary from type to all of its descendants
        tk = Toolkit()
        type_to_descendants = {}
        for t in tk.get_descendants('biolink:NamedThing', formatted=True):
            try:
                type_to_descendants[t] = tk.get_descendants(t, formatted=True)
            except:
                print("Error with type: " + t)
                pass
        return type_to_descendants

    def get_deepest_types(self, typelist):
        """Given a list of types, examine self.type_to_descendants and return a list of the types
        from typelist that do not have a descendant in the list"""
        # Let's have a cache because we see the same lists over and over and hitting BMT is slow
        fs = frozenset(typelist)
        if fs in self.deeptypescache:
            return self.deeptypescache[fs]
        deepest_types = []
        for t in typelist:
            if t not in self.type_to_descendants:
                # This covers mixins
                # deepest_types.append(t)
                continue
            descendants = self.type_to_descendants[t]
            # 1 because the descendants include the type itself
            if len(set(typelist).intersection(descendants)) == 1:
                deepest_types.append(t)
        deepest_types = frozenset(deepest_types)
        self.deeptypescache[fs] = deepest_types
        return deepest_types

def load_nodes(inf):
    node_ids = {}
    node_categories = {}
    handler = TypeHandler()
    cat_map = {}
    with jsonlines.open(inf, 'r') as inf:
        for node in inf:
            node_num = len(node_ids)
            node_ids[node["id"]] = node_num
            categories = handler.get_deepest_types(node["category"])
            if categories not in cat_map:
                cat_map[categories] = len(cat_map)
            node_categories[node_num] = cat_map[categories]
    return node_ids, node_categories, cat_map

def create_pq(record):
    # Given an edge json record, create a string that represents the predicate and qualifiers
    # it needs to be created such that the order is specified - even if the input qualifiers are in a different
    # order, the string should be the same.
    pq = {"predicate":record['predicate']}
    # If the qualifiers are in the record, use them.  Otherwise, look for the _qualifier fields
    if "qualifiers" in record:
        for qualifier in record["qualifiers"]:
            pq[qualifier["qualifier_type_id"]] = qualifier["qualifier_value"]
    else:
        for propname, propval in record.items():
            if propname.endswith("_qualifier"):
                pq[propname] = propval
    # THis has to be json instead of orjson because we need to sort the keys
    return json.dumps(pq, sort_keys=True)

def load_edges(inf, node_ids):
    neighbors = [[] for i in range(len(node_ids))]
    pq_to_num = {}
    onehops = defaultdict(set)
    n_edges = 0
    start = dt.now()
    with jsonlines.open(inf, 'r') as inf:
        for edge in inf:
            try:
                subject_id = node_ids[edge["subject"]]
                object_id  = node_ids[edge["object"]]
                pq = create_pq(edge)
                if pq not in pq_to_num:
                    pq_to_num[pq] = len(pq_to_num) + 1
                pq_num = pq_to_num[pq]
                neighbors[subject_id].append( (pq_num, object_id)   )
                neighbors[object_id].append(  (-pq_num, subject_id) )
                pair = (subject_id, object_id)
                onehops[pair].add(pq_num)
            except:
                print(f"Error on edge: {edge}")
            n_edges += 1
            if n_edges % 10000000 == 0:
                print(f"Loaded {n_edges} edges")
    end = dt.now()
    print("Load time:", end - start)
    return neighbors, pq_to_num, onehops

def generate_walk(num_nodes, neighborlist, node_ints, cumcount, walklen):
    while True:
        next_node = random.choices(node_ints, cum_weights=cumcount, k=1)[0]
        #if len(neighborlist[next_node]) == 0:
        #    continue
        walk = [next_node]
        used_nodes = set()
        used_nodes.add(next_node)
        for i in range(walklen):
            pq_num, next_node = random.choice(neighborlist[next_node])
            walk.append(pq_num)
            walk.append(next_node)
            used_nodes.add(next_node)
        if len(used_nodes) == walklen + 1:
            return walk

def convert_to_meta_walk(walk, nodes_to_cats):
    meta_walk = []
    for i in range(0, len(walk)-1, 2):
        meta_walk.append( nodes_to_cats[walk[i]] )
        meta_walk.append( walk[i+1] )
    meta_walk.append( nodes_to_cats[walk[-1]] )
    return tuple(meta_walk)

def write_walks(meta_walks, outfname = "meta_walks.json"):
    with open(outfname, 'w') as outf:
        outf.write("{\n")
        first = True
        for mw, direct_edges in meta_walks.items():
            if first:
                first = False
            else:
                outf.write("},\n")
            outf.write(f'  "{str(mw)}": {{')
            des = []
            for de, count in direct_edges.items():
                des.append(f'"{str(tuple(de))}": {count}' )
            outf.write(", ".join(des))
        outf.write("}\n}\n")

def random_walks(nodes_to_ints, nodes_to_cats, neighborlist, onehops, nwalks, walklen, odir):
    node_ints = [i for i in range(len(neighborlist))]
    edges_per_node = [ len(x) for x in neighborlist ]
    cumulative_count = itertools.accumulate(edges_per_node)
    num_nodes = len(nodes_to_ints)
    meta_walks = defaultdict(lambda: defaultdict(int))
    start = dt.now()
    for i in range(nwalks):
        walk = generate_walk(num_nodes, neighborlist, node_ints, cumulative_count, walklen)
        meta_walk = convert_to_meta_walk(walk, nodes_to_cats)
        if ( walk[0], walk[-1] ) in onehops:
            direct_edges = frozenset(onehops[(walk[0], walk[-1])] )
        elif ( walk[-1], walk[0] ) in onehops:
            direct_edges = onehops[(walk[-1], walk[0])]
            direct_edges = frozenset([ -x for x in direct_edges ])
        else:
            direct_edges = frozenset()
        meta_walks[meta_walk][direct_edges] += 1
        if i % 100000000 == 0:
            write_walks(meta_walks, outfname="meta_walks.json")
            end = dt.now()
            delta = end - start
            print(f"Generated {i} walks in {delta.total_seconds()} seconds. {i/delta.total_seconds()} walks per second")
    write_walks(meta_walks, outfname = os.path.join(odir,"meta_walks_final.json"))

def write_ids(thing_to_ids, odir, filename):
    ofn = os.path.join(odir, filename)
    with open(ofn, 'w') as outf:
        for thing, id in thing_to_ids.items():
            outf.write(f"{thing}\t{id}\n")

def go(nfilename, efilename, odir, nwalks, walklength=2):
    node_ids, node_categories, category_map = load_nodes(nfilename)
    neighbors, pq_to_num, one_hops = load_edges(efilename, node_ids)
    write_ids(node_ids, odir, "nodes_to_nums")
    write_ids(node_categories, odir, "nodes_to_cats")
    write_ids(pq_to_num, odir, "pq_to_num")
    write_ids(category_map, odir, "category_map")
    random_walks(node_ids, node_categories, neighbors, one_hops, nwalks, walklength, odir)

if __name__ == "__main__":
    nodefilename = sys.argv[1]
    edgefilename = sys.argv[2]
    outdir = sys.argv[3]
    numwalks = int(sys.argv[4])
    walklen = int(sys.argv[5])
    go(nodefilename, edgefilename, outdir, numwalks, walklen)