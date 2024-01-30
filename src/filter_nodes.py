import sys
import jsonlines

def go(edge_file, node_in, node_out):
    keepnodes = set()
    with jsonlines.open(edge_file, 'r') as inf:
        for line in inf:
            keepnodes.add(line["subject"])
            keepnodes.add(line["object"])
    with jsonlines.open(node_in, 'r') as inf, jsonlines.open(node_out, 'w') as outf:
        for line in inf:
            if line["id"] in keepnodes:
                outf.write(line)

if __name__ == "__main__":
    edge_file = sys.argv[1]
    node_in = sys.argv[2]
    node_out = sys.argv[3]
    go(edge_file, node_in, node_out)