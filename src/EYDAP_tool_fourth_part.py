## Part 4: Functions

def create_subgraph_from_threshold(gdf_cell_path, choose_option, filter_list, figsize=(10, 10), line_width=3):
    """
    Creates a subgraph from the edges with 'opt_time' less than or equal to the threshold.

    :param edges: GeoDataFrame representing the edges of the graph.
    :param threshold: The threshold value for 'opt_time' attribute.
    :return: A subgraph consisting of edges where 'opt_time' <= threshold.
    """
    # Convert shp to GeodataFrame
    pipes_gdf_cell_merged = gpd.read_file(gdf_cell_path).set_crs('EPSG:2100')
    
    ## Convert the GeoDataFrame into a graph
    ## Load the shapefile as geodataframe
    graph_cell = momepy.gdf_to_nx(pipes_gdf_cell_merged, approach='primal')

    ## Draw the graph with real coordinates
    # Extract nodes and edges
    nodes, edges = momepy.nx_to_gdf(graph_cell)
    
    # pick 'time' or 'node' type of selection 
    if choose_option:
        # Filter edges based on the threshold
        red_edges_df = edges[(edges['t_opt'] <= filter_list[1]) & (edges['t_opt'] >= filter_list[0])]

        subgraph = momepy.gdf_to_nx(red_edges_df, approach='primal')
    else:
        red_edges_df = edges[edges['ID'].isin(filter_list)]
        subgraph = momepy.gdf_to_nx(red_edges_df, approach='primal')
    
    red_edges_df = red_edges_df.drop(['mm_len','node_start','node_end'],axis=1)
    
    # Plot setup
    # fig, ax = plt.subplots(figsize=figsize)

    # Plotting edges with opt_time < threshold in red
    # red_edges_df.plot(ax=ax, linewidth=line_width, color='red')

    # Adding basemap
    # ctx.add_basemap(ax, crs=edges.crs.to_string(), source=ctx.providers.CartoDB.Positron)

    # Title and axis off
    # ax.set_title("Replacement for selected pipes")
    # ax.axis('off')

    # Show plot
    # plt.plot()

    return subgraph, red_edges_df


def calculate_metrics(subgraph, red_edges_df, i):
    """Calculate the total length and weighted average cost of edges in a subgraph."""
    total_length, total_weighted_cost = 0, 0
    for edge in subgraph.edges(data=True):
        length = edge[2]['USER_L']
        cost = edge[2]['t_opt']
        total_length += length
        total_weighted_cost += cost * length
        
        pipe_name = edge[2]['LABEL']
        red_edges_df.loc[red_edges_df['LABEL'] == pipe_name, 'cluster'] = i

    weighted_average_cost = round(total_weighted_cost / total_length if total_length > 0 else 0,2)
    return red_edges_df, total_length, weighted_average_cost


def analyze_graph(graph, red_edges_df, minimum_length, percent_accept):
    """Analyze the graph to find connected components and calculate metrics."""
    S = [graph.subgraph(c).copy() for c in nx.connected_components(graph)]

    total_length_graph, total_weighted_cost_graph = 0, 0
    for edge in graph.edges(data=True):
        length = edge[2]['USER_L']
        cost = edge[2]['t_opt']
        total_length_graph += length
        total_weighted_cost_graph += cost * length

    overall_weighted_average_cost = round(total_weighted_cost_graph / total_length_graph if total_length_graph > 0 else 0,2)

    results = []
    total_length_all = 0
    
    # create a column in red edges df with clusters
    red_edges_df['group'] = 0 
    i = 1 
    for component in S:
        red_edges_df, total_length, weighted_average_cost = calculate_metrics(component, red_edges_df, i)
        results.append({
            #'Path Edges': list(component.edges),
            'Total Length': total_length,
            'Average Time': weighted_average_cost
        })
        total_length_all += total_length
        i =i+ 1
        # print(i)

    results_df = pd.DataFrame(results)
    results_df['Meets Minimum Length'] = results_df['Total Length'].apply(lambda x: x > minimum_length)

    total_length_under = results_df[results_df['Meets Minimum Length'] == False]['Total Length'].sum()
    accept_condition = (total_length_under / total_length_all) <= percent_accept

    return red_edges_df, results_df, overall_weighted_average_cost, total_length_under, accept_condition, round(1 - total_length_under / total_length_all,3), total_length_all


def export_df_and_sentence_to_file(red_edges_df, results_df, total_length_under, row_number_to_keep, shp_name, overall_weighted_average_cost, accept_condition, perc, total_length_all, distance, filename):
      
    # Convert the DataFrame to string
    
    results_df.index.name = 'group'
    results_df.index = range(1, len(results_df) + 1)
    results_df.index.name = 'group'
    results_df = results_df.rename(columns={"Meets Minimum Length": f"Over {distance} m"})
    df_string = results_df.to_string(justify='justify-all')

    # Specific sentence to add
    sentence_1 = f'Έχετε επιλέξει {red_edges_df.shape[0]} αγωγούς από το shapefile του κελιού.'
    
    sentence_2 = f'Οι αγωγοί έχουν χωριστεί σε {results_df.shape[0]} ομάδες (groups) όπου δημιουργούν συνεχή τμήματα. Παρακάτω φαίνονται τα χαρακτηριστικά τους:'
    
    sentence_3 = f'Από τα {total_length_all} m των επιλεγμένων αγωγών, συνολικά {total_length_all-total_length_under} m αγωγών βρίσκονται σε συνέχη κομμάτια άνω των {distance} m.'
    
    sentence_4 = f'Αυτό αντιστοιχεί στο {perc*100} % των επιλεγμένων αγωγών.'
    
    # Concatenate DataFrame string with the specific sentence
    output_string = sentence_1 +'\n\n'+ sentence_2 +'\n\n'+ df_string + '\n\n' + sentence_3 + '\n\n' + sentence_4
    
    # Write the concatenated string to a text file
    with open(filename, 'w') as file:
        file.write(output_string)

        
#%% PART 4 USAGE 

# το shapefile που δημιουργείται στο βήμα 3 από το optimization
gdf_cell_path = f'Cell_optimization_results/Cell_Priority_{row_number_to_keep}' +'/Priority_' +str(row_number_to_keep) +'_cell_optimal_replacement.shp'


#----LOOP---- για να παράγονται shapefiles (με τα συνοδευομενα τους txts) μέσα στον ίδιο φάκελο σύμφωνα με 
# τις διαφορετικές επιλογές χρήστη (π.χ. άλλους χρόνους, διαφορετικά checkboxes etc)

# επιλογή χρήστη, πάει με χρόνους ή πάει με τα checkboxes?
# μεταβλητή απόφασης, True αν πάει με χρονους, False αν πάει με checkboxes 
choose_option = True 

if choose_option:
    # Αν πάει με χρόνους τότε
    low_time = 1 # ακέραιος από 1 μέχρι p_span 
    up_time = 3 # ακέραιος από 1 μέχρι p_span 
    filter_list = [low_time, up_time] # μοναδική συνθήκη το low_time να είναι μικρότερο-ίσο από το up_time 
else:
    # Αν πάει με checkboxes τότε να του βγάζει το dataframe 'pipes_gdf_cell' το οποίο είναι output από τη συνάρτηση process_pipes_cell_data του part 3
    filter_list = [1577, 1707, 1313, 1376, 1358, 1734]

# input χρήστη "Ελάχιστο μήκος εργολαβίας". άδειο κελί κ να γράφει όποια τιμή θέλει. Απλά να είναι σε μέτρα η μονάδα μέτρησης. 
distance = 100 

# use functions 
red_subgraph, red_edges_df = create_subgraph_from_threshold(gdf_cell_path, choose_option, filter_list)

red_edges_df, results_df, overall_weighted_average_cost, total_length_under, accept_condition, perc, total_length_all = analyze_graph(red_subgraph, red_edges_df, distance, 0.9)

# Για το export του shapefile, να διαλέγει όνομα ο χρήστης
shp_name = 'custom_selection_replacement_v2'
red_edges_df.to_file(f'Cell_optimization_results/Cell_Priority_{row_number_to_keep}//{shp_name}.shp')

# also export a text file containing useful info to the user. same file name and some folder to save 
text_filename = f'Cell_optimization_results/Cell_Priority_{row_number_to_keep}/{shp_name}.txt'
export_df_and_sentence_to_file(red_edges_df, results_df, total_length_under, row_number_to_keep, shp_name, overall_weighted_average_cost, accept_condition, perc, total_length_all, distance, text_filename)

