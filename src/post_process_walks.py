import json
import ast
import sys, os
from copy import deepcopy
from collections import defaultdict

symmetric_predicates={"biolink:correlated_with", "biolink:related_to", "biolink:coexpressed_with",
                      "biolink:interacts_with", "biolink:directly_physically_interacts_with",
                      "biolink:genetically_interacts_with","biolink:correlated_with",
                      "biolink:physically_interacts_with", "biolink:orthologous_to", "biolink:homologous_to",
                      "biolink:temporally_related_to", "biolink:overlaps", "biolink:colocalizes_with",
                      "biolink:positively_correlated_with", "biolink:associated_with", "biolink:coexists_with",
                      "biolink:negatively_correlated_with", "biolink:similar_to"}

remap_predicates = { "biolink:homologous_to": "biolink:orthologous_to",
                     "biolink:physically_interacts_with": "biolink:interacts_with",
                     "biolink:directly_physically_interacts_with": "biolink:interacts_with"}

remap_categories = { "'biolink:SmallMolecule'": "'biolink:ChemicalEntity'",
                     "'biolink:ComplexMolecularMixture'": "'biolink:ChemicalEntity'",
                     "'biolink:MolecularMixture'": "'biolink:ChemicalEntity'",
                     "'biolink:ChemicalMixture'": "'biolink:ChemicalEntity'",
                     "'biolink:Protein'": "'biolink:Gene'",
                     "'biolink:Protein', 'biolink:Gene'": "'biolink:Gene'",
                     "'biolink:Gene', 'biolink:Protein'": "'biolink:Gene'"}


def read_categories(indir):
    num_to_cat = {}
    with open(os.path.join(indir, "category_map")) as inf:
        for line in inf:
            x = line.strip().split('\t')
            num = int(x[1])
            cat_set = x[0].split('{')[1].split('}')[0]
            num_to_cat[num] = cat_set
    return num_to_cat

def read_pqs(indir):
    num_to_pq = {}
    with open(os.path.join(indir, "pq_to_num")) as inf:
        for line in inf:
            x = line.strip().split('\t')
            num = int(x[1])
            pq = json.loads(x[0])
            num_to_pq[num] = pq
    return num_to_pq

def collapse_results(results):
    """After we have remapped categories and predicates, we will have some redundant metapaths. This function
    merges them.  This will also create redundant direct edges, which me must also merge."""
    newresults = defaultdict(list)
    for result in results:
        pathkey = json.dumps(result["metapath"],sort_keys=True)
        newresults[pathkey].append(result)
    newnewresults = []
    for pathkey, pathresults in newresults.items():
        newresult = {"metapath": pathresults[0]["metapath"], "direct_edges": [] }
        merged_edges = defaultdict(int)
        for pr in pathresults:
            for de in pr["direct_edges"]:
                edgekey = json.dumps(de["edge"], sort_keys=True)
                merged_edges[edgekey] += de["count"]
        newresult["direct_edges"] = [ {"count": count, "edge": json.loads(edge) } for edge, count in merged_edges.items() ]
        newresult["total_count"] = sum(merged_edges.values())
        newnewresults.append(newresult)
    return newnewresults

def go(indir):
    categories = read_categories(indir)
    pqs = read_pqs(indir)
    with open(os.path.join(indir, "meta_walks_final.json"), 'r') as inf:
        paths = json.load(inf)
    results = []
    for path, direct_edges in paths.items():
        x = {"metapath": [], "direct_edges": []}
        pathtuple = ast.literal_eval(path)
        for i in range(0, len(pathtuple)-1, 2):
            cat = categories[pathtuple[i]]
            if cat in remap_categories:
                cat = remap_categories[cat]
            x["metapath"].append( cat )
            pqnum = pathtuple[i+1]
            if pqnum > 0:
                pq = deepcopy(pqs[pqnum])
            else:
                pqnum = -pqnum
                pq = deepcopy(pqs[pqnum])
                #If it's symmetric, let's go left to right.
                if pq["predicate"] not in symmetric_predicates:
                    pq["reverse"] = True
            if pq["predicate"] in remap_predicates:
                pq["predicate"] = remap_predicates[pq["predicate"]]
            x["metapath"].append( pq )
        cat = categories[pathtuple[len(pathtuple)-1]]
        if cat in remap_categories:
            cat = remap_categories[cat]
        x["metapath"].append( cat )
        for direct_edge, count in direct_edges.items():
            y = {"count": count, "edge": []}
            edges_tuple = ast.literal_eval(direct_edge)
            for pqnum in edges_tuple:
                if pqnum > 0:
                    pq = deepcopy( pqs[pqnum] )
                else:
                    pqnum = -pqnum
                    pq = deepcopy( pqs[pqnum] )
                    if pq["predicate"] not in symmetric_predicates:
                        pq["reverse"] = True
                y["edge"].append(pq)
            x["direct_edges"].append(y)
        results.append(x)
    results = collapse_results(results)
    results.sort(key=lambda x: x["total_count"], reverse=True)
    with open(os.path.join(indir, "processed_metapaths.json"), 'w') as outf:
        json.dump(results, outf, indent=2)

if __name__ == "__main__":
    indir = sys.argv[1]
    go(indir)