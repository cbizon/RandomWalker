import json
import ast
import sys, os

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
            print(x[0])
            pq = json.loads(x[0])
            num_to_pq[num] = pq
    return num_to_pq

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
            x["metapath"].append( categories[pathtuple[i]] )
            pqnum = pathtuple[i+1]
            if pqnum < 0:
                pqnum = -pqnum
                pq = pqs[pqnum]
                pq["reverse"] = True
            x["metapath"].append( pq )
        x["metapath"].append( categories[pathtuple[i]] )
        for direct_edge, count in direct_edges.items():
            y = {"count": count, "edge": []}
            edges_tuple = ast.literal_eval(direct_edge)
            for edge in edges_tuple:
                pqnum = edge[0]
                if pqnum < 0:
                    pqnum = -pqnum
                    pq = pqs[pqnum]
                    pq["reverse"] = True
                else:
                    pq = pqs[pqnum]
                y["edge"].append(pq)
            x["direct_edges"].append(y)
        results.append(x)
    with open(os.path.join(indir, "processed_metapaths.json"), 'w') as outf:
        json.dump(results, outf, indent=2)

if __name__ == "__main__":
    indir = sys.argv[1]
    go(indir)