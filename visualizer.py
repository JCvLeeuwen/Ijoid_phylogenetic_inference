# visualize beast phylogenetic trees

import dendropy
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
import os
import numpy as np
import re

rcParams['font.family'] = 'sans-serif'
rcParams['font.size'] = 9

# language names
language_names = {
    "DE": "Defaka",
    "NK": "Nkoroo", "IB": "Ibani", "KI": "Kirike (Okrika)", "KA": "Kalabari", "BL": "Bile",
    "NE": "Nembe", "AK": "Akassa (Akaha)",
    "OR": "Oruma", "AT": "Okordia (Akita)", "BI": "Biseni",
    "BU": "Bumo", "OP": "Oporoma", "OY": "Oyakiri", "ET": "East Tarakiri", 
    "EO": "East Olodiama", "BA": "Basan", "KL": "Koluama", "AP": "Apoi",
    "FU": "Furupagha", "AR": "Arogbo",
    "ID_LANG": "Iduwini", "OG": "Ogulagha", "GM": "Gbaramatu", "EG": "Egbema", 
    "WO": "West Olodiama", "OB": "Ogbe Ijo", "OT": "Oboro Town", "OE": "Operemo", 
    "ME": "Mein", "KU": "Kunbo", "KB": "Kabou", "WT": "West Tarakiri", 
    "ON": "Ogboin", "IK": "Ikibiri",
    "EK": "Ekpetiama", "KO": "Kolokuma", "GB": "Gbarain"
}

# tip colors
tip_colors = {
    "DE": "#ADD8E6",
    "NK": "#FF00FF", "IB": "#FF00FF", "KI": "#FF00FF", "KA": "#FF00FF", "BL": "#FF00FF",
    "NE": "#FFA500", "AK": "#FFA500",
    "OR": "#0000FF", "AT": "#0000FF", "BI": "#0000FF",
    "BU": "#228B22", "OP": "#228B22", "OY": "#228B22", "ET": "#228B22", 
    "EO": "#228B22", "BA": "#228B22", "KL": "#228B22", "AP": "#228B22",
    "FU": "#40E0D0", "AR": "#40E0D0",
    "ID_LANG": "#800080", "OG": "#800080", "GM": "#800080", "EG": "#800080", 
    "WO": "#800080", "OB": "#800080", "OT": "#800080", "OE": "#800080", 
    "ME": "#800080", "KU": "#800080", "KB": "#800080", "WT": "#800080", 
    "ON": "#800080", "IK": "#800080",
    "EK": "#FF0000", "KO": "#FF0000", "GB": "#FF0000"
}

# legend colors
color_groups = {
    "Defaka": "#ADD8E6",
    "Eastern Ijo (KOIN)": "#FF00FF",
    "Eastern Ijo (Nembe-Akassa)": "#FFA500",
    "Inland Ijo": "#0000FF",
    "Izon - South-Central": "#228B22",
    "Izon - Southwestern": "#40E0D0",
    "Izon - Northwestern": "#800080",
    "Izon - Northeastern": "#FF0000"
}

def extract_posteriors(tree_file):
    # extract posterior probabilities
    with open(tree_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # find tree
    tree_match = re.search(r'tree\s+\S+\s*=\s*\[&R\]\s*(.+?);', content, re.DOTALL)
    if not tree_match:
        tree_match = re.search(r'tree\s+\S+\s*=\s*(.+?);', content, re.DOTALL)
    
    if not tree_match:
        return []
    
    newick = tree_match.group(1)
    if newick.endswith(';'):
        newick = newick[:-1]
    
    # extract posteriors
    posteriors = re.findall(r'posterior=([0-9.Ee-]+)', newick)
    if posteriors:
        return [float(x) for x in posteriors]
    return []

def plot_tree(tree_file, output_file, show_colors=True, format='pdf'):
    # plot tree
    posteriors = extract_posteriors(tree_file)
    
    # read tree
    tree = dendropy.Tree.get(
        path=tree_file,
        schema="nexus",
        preserve_underscores=True,
        extract_comment_metadata=True
    )
    
    tree.calc_node_ages()
    
    # replace tip labels
    for taxon in tree.taxon_namespace:
        if taxon.label in language_names:
            taxon.label = language_names[taxon.label]
    
    # get dimensions
    num_tips = len(tree.leaf_nodes())
    max_dist = tree.max_distance_from_root()
    
    # create figure
    fig = plt.figure(figsize=(10, max(8, num_tips * 0.25)))
    ax = plt.subplot(1, 1, 1)
    
    # compute coordinates
    tip_y = {}
    y_pos = 0
    for leaf in tree.leaf_nodes():
        tip_y[leaf] = y_pos
        y_pos += 1
    
    node_coords = {}
    
    def calc_y(node):
        if node.is_leaf():
            return tip_y[node]
        else:
            child_ys = [calc_y(child) for child in node.child_nodes()]
            return np.mean(child_ys)
    
    for node in tree.postorder_node_iter():
        if node.is_leaf():
            node_coords[node] = (node.distance_from_root(), tip_y[node])
        else:
            y = calc_y(node)
            x = node.distance_from_root()
            node_coords[node] = (x, y)
    
    # draw edges
    for node in tree.preorder_node_iter():
        if not node.is_leaf() or node.parent_node:
            if node.parent_node:
                parent_x, parent_y = node_coords[node.parent_node]
                node_x, node_y = node_coords[node]
                ax.plot([parent_x, node_x], [node_y, node_y], 'k-', linewidth=1.2)
                ax.plot([parent_x, parent_x], [parent_y, node_y], 'k-', linewidth=1.2)
    
    # draw tip labels
    for leaf in tree.leaf_nodes():
        x, y = node_coords[leaf]
        taxon_label = leaf.taxon.label
        color = 'black'
        if show_colors:
            for code, name in language_names.items():
                if name == taxon_label and code in tip_colors:
                    color = tip_colors[code]
                    break
        ax.text(x + max_dist * 0.01, y, taxon_label, 
               va='center', ha='left', fontsize=9, 
               color=color, fontstyle='italic')
    
    # add posteriors
    internal_nodes = [node for node in tree.postorder_internal_node_iter()]
    
    for idx, node in enumerate(internal_nodes):
        if idx < len(posteriors):
            posterior = posteriors[idx]
            if posterior >= 0.1:
                x, y = node_coords[node]
                post_text = f"{posterior:.3f}"
                font_size = 7 if posterior >= 0.95 else 6
                ax.text(x, y + 0.3, post_text, 
                       ha='center', va='bottom', 
                       fontsize=font_size,
                       bbox=dict(boxstyle='round,pad=0.3', 
                               facecolor='white', 
                               edgecolor='none',
                               alpha=0.7))
    
    # scale bar
    scale_x = max_dist * 0.1
    scale_y = -1
    ax.plot([0, scale_x], [scale_y, scale_y], 'k-', linewidth=2)
    ax.text(scale_x/2, scale_y - 0.5, f'{scale_x:.2f}', 
           ha='center', va='top', fontsize=8)
    
    # set limits
    ax.set_xlim(-max_dist * 0.05, max_dist * 1.35)
    ax.set_ylim(-2, num_tips)
    ax.axis('off')
    
    # legend
    if show_colors:
        patches = []
        for group, color in color_groups.items():
            patches.append(mpatches.Patch(color=color, label=group))
        ax.legend(handles=patches, loc='upper right', 
                 fontsize=7, frameon=True, framealpha=0.9)
    
    plt.tight_layout()
    
    # save
    if format == 'pdf':
        plt.savefig(output_file, format='pdf', dpi=300, bbox_inches='tight')
    else:
        plt.savefig(output_file, format='png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"saved: {output_file}")

# main
if __name__ == "__main__":
    input_dir = "C:/your/input/dir/trees"
    output_dir = "C:/your/output/dir/visualizations"
    
    os.makedirs(output_dir, exist_ok=True)
    
    tree_files = [
        "so_basic_mcc.tree",
        "so_borrowable_mcc.tree",
        "so_unmatched_mcc.tree",
        "ti_basic_mcc.tree",
        "ti_borrowable_mcc.tree",
        "ti_unmatched_mcc.tree",
        "tr_basic_mcc.tree",
        "tr_borrowable_mcc.tree",
        "tr_unmatched_mcc.tree",
    ]
    
    for tree_file in tree_files:
        tree_path = os.path.join(input_dir, tree_file)
        
        if os.path.exists(tree_path):
            base = tree_file.replace('.tree', '')
            print(f"\nprocessing: {tree_file}")
            
            try:
                # pdf and png
                output_pdf = os.path.join(output_dir, f"{base}_colored.pdf")
                plot_tree(tree_path, output_pdf, show_colors=True, format='pdf')
                
                output_png = os.path.join(output_dir, f"{base}_colored.png")
                plot_tree(tree_path, output_png, show_colors=True, format='png')
                
            except Exception as e:
                print(f"error: {e}")
                import traceback
                traceback.print_exc()
    
    print("\ndone")
    print(f"saved to: {output_dir}")