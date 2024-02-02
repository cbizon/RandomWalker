import json
import os,sys

cat_abbreviations = {"'biolink:SmallMolecule'": "SM",
                     "'biolink:Gene'": "G",
                     "'biolink:Protein'": "P",
                     "'biolink:Gene', 'biolink:Protein'": "G,P",
                     "'biolink:Pathway'": "PW",
                     "'biolink:Disease'": "D",
                     "'biolink:PhenotypicFeature'": "PF",
                     "'biolink:BiologicalProcess'": "BP",
                     "'biolink:PhysiologicalProcess'": "PP",
                     "'biolink:Cell'": "C",
                        "'biolink:CellularComponent'": "CC",
                        "'biolink:MolecularActivity'": "MA",
                        "'biolink:AnatomicalEntity'": "AE",
                     "'biolink:OrganismTaxon'": "OT",
                     "'biolink:GeneFamily'": "GF",
                     "'biolink:GrossAnatomicalStructure'": "AS",
                     "'biolink:MolecularMixture'": "MM",
                     "'biolink:ComplexMolecularMixture'": "CMM",
                     "'biolink:ChemicalMixture'": "CM",
                     "'biolink:ChemicalEntity'": "CE",
                     "'biolink:BiologicalEntity'": "BE",
                     "'biolink:Polypeptide'": "Po",
                     "'biolink:Procedure'": "Pr",
                     "'biolink:Behavior'": "B",
                     "'biolink:OrganismAttribute'": "OA",
                     "'biolink:ClinicalAttribute'": "CA",
                     "'biolink:InformationContentEntity'": "ICE",
                     "'biolink:Activity'": "A",
                     "'biolink:Drug'": "D",
                     "'biolink:Phenomenon'": "Ph",
                     "'biolink:Device'": "Dv",
                     }

if len(cat_abbreviations.values()) != len(cat_abbreviations):
    print("Your category abbreviations are not unique")
    exit()

def shorten_edge(edge):
    if edge["predicate"] == "biolink:affects":
        if "object_direction_qualifier" in edge:
            e = f"{edge['object_direction_qualifier']}_{edge['object_aspect_qualifier']}"
        elif "object_aspect_qualifier" in edge:
            e = f"affects_{edge['object_aspect_qualifier']}"
        else:
            e = "affects"
    elif edge["predicate"] == "biolink:regulates":
        if "object_direction_qualifier" in edge:
            e = f"regulates_{edge['object_direction_qualifier']}"
        else:
            e = "regulates"
    else:
        e = edge["predicate"].split(":")[1]
    if "reverse" in edge and edge["reverse"] == True:
        return f"<_{e}"
    else:
        return f"{e}_>"

def go(indir):
    with open(os.path.join(indir, "processed_metapaths.json"), 'r') as inf:
        paths = json.load(inf)
    cum_count = 0
    with open(os.path.join(indir, "tabulated_metapaths.tsv"), 'w') as outf:
        outf.write( "MetaPath\ttotal_count\tfraction_no_direct\tMost Common Direct\tFraction MCE\tNum Direct Types\n")
        for path in paths:
            mp = path["metapath"]
            shortpath=[]
            for i in range(0, len(mp)-1, 2):
                shortpath.append(cat_abbreviations[mp[i]])
                shortpath.append(shorten_edge(mp[i+1]))
            shortpath.append(cat_abbreviations[mp[len(mp)-1]])
            total_count = path["total_count"]
            cum_count += total_count
            direct_edges = path["direct_edges"]
            n_no_direct = 0
            edges = []
            for de in direct_edges:
                if len(de["edge"]) == 0:
                    n_no_direct = de["count"]
                edges.append ( (de["count"], de["edge"]) )
            fraction_no_direct = n_no_direct / total_count
            edges.sort(key=lambda x: x[0], reverse=True)
            for next_c,next_e in edges:
                if len(next_e) > 0:
                    break
            short_e = [shorten_edge(e) for e in next_e]
            num_predicates = len(edges)
            outf.write(f"{' '.join(shortpath)}\t{total_count}\t{fraction_no_direct}\t{','.join(short_e)}\t{next_c/total_count}\t{num_predicates}\n")


if __name__ == "__main__":
    indir = sys.argv[1]
    go(indir)