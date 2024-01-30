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
    for path, direct_edges in paths.items():
        x = {"metapath": [], "direct_edges": {}}
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

if __name__ == "__main__":
    indir = sys.argv[1]
    go(indir)