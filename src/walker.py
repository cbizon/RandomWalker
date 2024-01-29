import sys
import json
import jsonlines
import random
from collections import defaultdict
from datetime import datetime as dt

def load_nodes(inf):
    node_ids = {}
    node_categories = {}
    with jsonlines.open(inf, 'r') as inf:
        for node in inf:
            node_num = len(node_ids)
            node_ids[node["id"]] = node_num
            node_categories[node_num] = node["category"][0]
    return node_ids, node_categories

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

def generate_walk(num_nodes, neighborlist, walklen):
    while True:
        next_node = random.randint(0, num_nodes-1)
        if len(neighborlist[next_node]) == 0:
            continue
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
        for mw, direct_edges in meta_walks.items():
            outf.write(f'  "{str(mw)}": {{')
            for de, count in direct_edges.items():
                outf.write(f'"{str(tuple(de))}": {count}, ')
            outf.write("},\n")
        outf.write("}\n")

def random_walks(nodes_to_ints, nodes_to_cats, neighborlist, onehops, nwalks, walklen):
    num_nodes = len(nodes_to_ints)
    meta_walks = defaultdict(lambda: defaultdict(int))
    start = dt.now()
    for i in range(nwalks):
        walk = generate_walk(num_nodes, neighborlist, walklen)
        meta_walk = convert_to_meta_walk(walk, nodes_to_cats)
        if ( walk[0], walk[-1] ) in onehops:
            direct_edges = frozenset(onehops[(walk[0], walk[-1])] )
        elif ( walk[-1], walk[0] ) in onehops:
            direct_edges = onehops[(walk[-1], walk[0])]
            direct_edges = frozenset([ -x for x in direct_edges ])
        else:
            direct_edges = frozenset()
        meta_walks[meta_walk][direct_edges] += 1
        if i % 100000 == 0:
            write_walks(meta_walks, outfname="meta_walks.json")
            end = dt.now()
            delta = end - start
            print(f"Generated {i} walks in {delta.total_seconds()} seconds. {i/delta.total_seconds()} walks per second")
    write_walks(meta_walks, outfname = "meta_walks_final.json")

def write_ids(thing_to_ids, filename):
    with open(filename, 'w') as outf:
        for thing, id in thing_to_ids.items():
            outf.write(f"{thing}\t{id}\n")

def go(nfilename, efilename, nwalks, walklength=2):
    node_ids, node_categories = load_nodes(nfilename)
    neighbors, pq_to_num, one_hops = load_edges(efilename, node_ids)
    write_ids(node_ids, "nodes_to_nums")
    write_ids(node_categories, "nodes_to_cats")
    write_ids(pq_to_num, "pq_to_num")
    random_walks(node_ids, node_categories, neighbors, one_hops, nwalks, walklength)

if __name__ == "__main__":
    nodefilename = sys.argv[1]
    edgefilename = sys.argv[2]
    numwalks = int(sys.argv[3])
    go(nodefilename, edgefilename, numwalks)