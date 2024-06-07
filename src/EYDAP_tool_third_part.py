#%% Part 3 Optimization - ONLY FUNCTIONS

def optimize_pipe_clusters(results_pipe_clusters, df_metrics, sorted_fishnet_df):
    
    # Convert the clusters to a dictionary with pipes as keys and clusters as values
    pipe_to_clusters = {}
    for key, pipes in results_pipe_clusters.items():
        for pipe in pipes:
            if pipe not in pipe_to_clusters:
                pipe_to_clusters[pipe] = []
            pipe_to_clusters[pipe].append(key)

    def get_highest_priority_cluster(pipe, clusters, metric_com_df):
        # Extract the metric_com values for the clusters
        cluster_priorities = metric_com_df.loc[clusters, 'metric_com']
        # Return the cluster with the highest metric_com
        return cluster_priorities.idxmax()

    # Go through each pipe in df_metrics and determine the highest priority cluster
    for pipe in df_metrics['LABEL']:
        if pipe in pipe_to_clusters:
            # Get all clusters the pipe is part of
            clusters = pipe_to_clusters[pipe]
            if len(clusters) > 1:
                # More than one cluster, so we need to find out which one has the highest priority
                highest_priority_cluster = get_highest_priority_cluster(pipe, clusters, sorted_fishnet_df)
                # Keep the pipe only in the highest priority cluster
                for cluster in clusters:
                    if cluster != highest_priority_cluster:
                        results_pipe_clusters[cluster].remove(pipe)

    # Optionally, return updated results_pipe_clusters if needed
    return results_pipe_clusters


def process_pipes_cell_data(path_pipes, path_fishnet, fishnet_index, row_number_to_keep, results_pipe_clusters, pipe_materials):
    # Read pipes data and set coordinate reference system
    pipes_gdf = gpd.read_file(path_pipes).set_crs('EPSG:2100')

    # Read fishnet data and set coordinate reference system
    fishnet_gdf = gpd.read_file(path_fishnet).set_crs('EPSG:2100')

    # Extract the specific row based on the row number
    cell_index = fishnet_index.iloc[row_number_to_keep - 1]

    # Get the list of pipes contained in the specific cell
    pipes_cell = results_pipe_clusters[cell_index]

    # Create a dataframe containing only the pipes of the specific cell
    pipes_gdf_cell = pipes_gdf[pipes_gdf['LABEL'].isin(pipes_cell)]

    # Reset the index of the dataframe
    pipes_gdf_cell = pipes_gdf_cell.reset_index(drop=True)

    # Fill a new column with the pipe age
    pipes_gdf_cell['Pipe Age'] = pipes_gdf_cell['MATERIAL'].map(pipe_materials)

    # Select specific columns for the dataframe
    pipes_gdf_cell = pipes_gdf_cell[['D', 'LABEL', 'MATERIAL', 'USER_L', 'Pipe Age', 'ID']]

    return pipes_gdf_cell


def calculate_investment_timeseries(pipes_gdf_cell, p_span, perc_inc, a_rel):
    # Calculate replacement time array
    repl_time_array = np.random.randint(1, p_span + 1, size=len(pipes_gdf_cell['ID']))

    # Initialize the pipe table
    pipe_table_trep = deepcopy(pipes_gdf_cell)
    pipe_table_trep['t_rep'] = np.nan
    pipe_table_trep['LCC_min'] = np.nan

    # Process each pipe for optimal replacement age and minimum LCC
    for i in range(len(pipe_table_trep.index)):
        p_id = pipe_table_trep.loc[i, 'ID']
        p_age = pipe_table_trep.loc[pipe_table_trep['ID'] == p_id, 'Pipe Age'].iloc[0]
        p_diam = pipe_table_trep.loc[pipes_gdf_cell['ID'] == p_id, 'D'].iloc[0]
        p_len = pipe_table_trep.loc[pipe_table_trep['ID'] == p_id, 'USER_L'].iloc[0]
        p_CP = (0.0005066289 * p_diam**2 + 0.2041100332 * p_diam + 212.9637728607) * 1000
        p_Cr = 1.3 * (p_diam / 304.8)**0.62 * 800

        t_res = single_opt_age(p_id, p_age, p_diam, p_CP, p_Cr, p_span)
        pipe_table_trep.loc[i, 't_rep'] = t_res[0]
        pipe_table_trep.loc[i, 'LCC_min'] = t_res[1]

    # Calculate least life cycle cost of the network
    pipe_table_trep['LCCmultL'] = pipe_table_trep['USER_L'] / 1000 * pipe_table_trep['LCC_min']
    LLCCn = pipe_table_trep['LCCmultL'].sum()

    # Set up the boundaries for each variable
    x_base = pipe_table_trep['t_rep'].to_numpy()
    xl = x_base - a_rel
    xl[xl <= 0] = 1
    xu = x_base + a_rel
    xu[xu > p_span] = p_span

    # Calculate available yearly budget
    ann_budg = (1 + perc_inc / 100) * LLCCn

    return pipe_table_trep, LLCCn, ann_budg, xl, xu


# Create function to find the ideal optimal replacement age of a single pipe
def single_opt_age(pipe_id, pipe_age, pipe_diam, CP, Cr, time_span):
    # pipe_id: the id of the pipe
    # pipe_age: the pipe age at the beginning of the planning period (years)
    # pipe_diam: the pipe diameter (mm)
    # CP:the pipe replacement cost (€/km)
    # Cr: the pipe repair cost (€/failure)

    #create empty data frame containing the necessary columns
    p_df = pd.DataFrame(index=range(1, time_span + 1),
                                    columns=['CI', 'Age', 'Fr',
                                             'SFr/t', 'CR', 'LCC'])
    #fill the columns with the respective values
    for i in range(1, time_span +1):
        p_df.loc[i, 'Age'] = pipe_age + i
        p_df.loc[i, 'CI'] = CP/p_df.loc[i, 'Age']
        p_df.loc[i, 'Fr'] = 0.109 * math.e ** \
                            (-0.0064*pipe_diam) * \
                            p_df.loc[i, 'Age'] ** 1.377
        p_df.loc[i, 'SFr/t'] = p_df['Fr'].loc[:i].sum()/i
        p_df.loc[i, 'CR'] = p_df.loc[i, 'SFr/t'] * Cr
        p_df.loc[i, 'LCC'] = p_df.loc[i, 'CI'] + p_df.loc[i, 'CR']
    t_star = pd.to_numeric(p_df['LCC'], downcast='float').idxmin()
    #return optimal replacement time for single pipe
    return t_star, p_df['LCC'].min()
   
    
# Create function to find the ideal LCC of a single pipe at time t
def single_opt_lcc(pipe_id, pipe_age, pipe_diam, CP, Cr,time_span, t):
    # pipe_id: the id of the pipe
    # pipe_age: the pipe age at the beginning of the planning period (years)
    # pipe_diam: the pipe diameter (mm)
    # CP: the pipe replacement cost (€/km)
    # Cr: the pipe repair cost (€/failure)

    #create empty data frame containing the necessary columns
    p_df = pd.DataFrame(index=range(1, time_span + 1),
                                    columns=['CI', 'Age', 'Fr',
                                             'SFr/t', 'CR', 'LCC'])
    #fill the columns with the respective values
    for i in range(1, time_span +1):
        p_df.loc[i, 'Age'] = pipe_age + i
        p_df.loc[i, 'CI'] = CP/p_df.loc[i, 'Age']
        p_df.loc[i, 'Fr'] = 0.109 * math.e ** \
                            (-0.0064*pipe_diam) * \
                            p_df.loc[i, 'Age'] ** 1.377
        p_df.loc[i, 'SFr/t'] = p_df['Fr'].loc[:i].sum()/i
        p_df.loc[i, 'CR'] = p_df.loc[i, 'SFr/t'] * Cr
        p_df.loc[i, 'LCC'] = p_df.loc[i, 'CI'] + p_df.loc[i, 'CR']

    return p_df.loc[t, 'LCC']        


def lcc_tot_net(repl_time_array, pipe_table, time_span):
    t_rep_count = 0
    lcc_tot = 0
    for p_id in pipe_table['ID']:
        t_rep = repl_time_array[t_rep_count]
        p_age = pipe_table.loc[pipe_table['ID'] == p_id, 'Pipe Age'].iloc[0]
        p_diam = pipe_table.loc[pipe_table['ID'] == p_id, 'D'].iloc[0]
        p_len = pipe_table.loc[pipe_table['ID'] == p_id, 'USER_L'].iloc[0]
        # pipe replacement cost based on an inteprolated polyonym of the replacement cost and the connection cost (€/km)
        p_CP = (0.0005066289 * p_diam**2 + 0.2041100332 * p_diam + 212.9637728607) * 1000
        p_Cr = 1.3*(p_diam/304.8)**0.62*800


        p_lcc = single_opt_lcc(p_id, p_age, p_diam, p_CP, p_Cr, time_span, t_rep)*p_len/1000

        lcc_tot = lcc_tot + p_lcc

        t_rep_count =  t_rep_count + 1

    return  lcc_tot    


#Create function to calculate the single pipe life cycle costs data frame when pipe is replaced at time t_rep
def single_opt_age_rep(pipe_id, pipe_age, pipe_diam, CP, Cr, time_span, t_rep):
    #create empty data frame containing the necessary columns
    p_df = pd.DataFrame(index=range(1, time_span + 1),
                                    columns=['CI', 'Age', 'Fr',
                                             'SFr/t', 'CR', 'LCC'])
    #t_rep = single_opt_age(pipe_id, pipe_age, pipe_diam, CP, Cr, time_span)[0]
    #fill the columns with the respective values
    for i in range(1, time_span +1):
        if i <= t_rep:
            p_df.loc[i, 'Age'] = pipe_age + i
            p_df.loc[i, 'CI'] = CP/p_df.loc[i, 'Age']
            p_df.loc[i, 'Fr'] = 0.109 * math.e ** \
                                (-0.0064*pipe_diam) * \
                                p_df.loc[i, 'Age'] ** 1.377
        else:
            p_df.loc[i, 'Age'] = i - t_rep
            p_df.loc[i, 'CI'] = CP/(i - t_rep)
            p_df.loc[i, 'Fr'] = 0.109 * math.e ** \
                                (-0.0064*pipe_diam) * \
                                p_df.loc[i, 'Age'] ** 1.377
        p_df.loc[i, 'SFr/t'] = p_df['Fr'].loc[:i].sum()/i
        p_df.loc[i, 'CR'] = p_df.loc[i, 'SFr/t'] * Cr
        p_df.loc[i, 'LCC'] = p_df.loc[i, 'CI'] + p_df.loc[i, 'CR']
    
    #return cost data frame
    return p_df
    
    
def investment_series(repl_time_array, pipe_table, p_span):
    # repl_time_array: array containing the replacement time for each pipe
    # pipe_table: data frame containing the pipe data
    lcc_table = pd.DataFrame(index=range(1, p_span + 1),
                                    columns=pipe_table['ID'],
                                    data = np.nan)
    t_rep_count = 0
    for p_id in pipe_table['ID']:
        t_rep = repl_time_array[t_rep_count]
        p_age = pipe_table.loc[pipe_table['ID'] == p_id, 'Pipe Age'].iloc[0]
        p_diam = pipe_table.loc[pipe_table['ID'] == p_id, 'D'].iloc[0]
        p_len = pipe_table.loc[pipe_table['ID'] == p_id, 'USER_L'].iloc[0]
        p_CP = (0.0005066289 * p_diam**2 + 0.2041100332 * p_diam + 212.9637728607) * 1000
        p_Cr = 1.3*(p_diam/304.8)**0.62*800

        p_df = single_opt_age_rep(p_id, p_age, p_diam, p_CP, p_Cr, p_span, t_rep)

        lcc_table[p_id] = p_df['LCC'] * (p_len/1000)

        t_rep_count =  t_rep_count + 1

    lcc_series = lcc_table.sum(axis=1)

    return lcc_series, lcc_table
 
    
def check_items_in_key(dictionary, fishnet_index, row_number_to_keep):
    try:
        # Attempt to obtain cell_index
        cell_index = fishnet_index.iloc[row_number_to_keep - 1]
    except IndexError:
        # If row_number_to_keep is out of bounds
        return f"Η γραμμή {row_number_to_keep} δεν υπάρχει στο shapefile." #ξαναβαλε
    except Exception as e:
        # Handle other potential errors
        return f"Προέκυψε σφάλμα: {e}"

    # Check if the cell_index exists in the dictionary
    if cell_index not in dictionary:
        return f"Το κελί '{cell_index}' δεν υπάρχει." #δεν υπαρχει 
    elif not dictionary[cell_index]:
        return f"Το κελί '{cell_index}' δεν περιέχει αγωγούς καθώς αυτοί έχουν ανατεθεί σε γειτονικά." ###ξαναβαλε
    else:
        number = len(dictionary[cell_index])
        return f"Το κελί '{cell_index}' περιέχει '{number}' αγωγούς." #προχωραμε 
        
        
#%% Part 3: USAGE 

# Define which pipes are contained in each cell of the grid
results_pipe_clusters = optimize_pipe_clusters(results_pipe_clusters, df_metrics, sorted_fishnet_df)

# Read the pipe shapefile which was created in part 1 and exported in the main folder 
path_pipes = r"Pipes_WG_export_with_metrics.shp"

# Read the sorted fishnet shapefile
# Εδω να διαλέγεται το shp που έχει δημιουργηθεί μέσα στο φάκελο Fishnet_Grids 
path_fishnet = str(select_square_size) + '_fishnets_sorted.shp'

# Create a dictionary of the pipe age per material
# Εδώ πρέπει να βρίσκει τα μοναδικά υλικά από το df_metrics και να γυρνάει 
# στο χρήστη μία λίστα με αυτά για να συμπληρώσει την ηλικία τους
unique_pipe_materials = df_metrics['MATERIAL'].unique()
# Αν γίνεται, να περνάνε τα παρακάτω ως default αλλά να υπάρχει η δυνατότητα αλλαγής
pipe_materials = {
    'Asbestos Cement': 50,
    'Steel': 40,
    'PVC': 30,
    'HDPE': 12, 
    'Cast iron':40
}

# Insert lifespan of contract work
# Δημιουργία μπάρας με min=5 και max=15, default=10 
p_span = 10 # years

# allowable time span relaxation
# Δημιουργία μπάρας με min=2 και max=5, default=3
a_rel = 3 # years 


# Create a folder containig the optimization results per cell
#Εδώ να δημιουργείται ένας φάκελος "Cell_optimization_results" μέσα στον Φάκελο Μελέτης 
os.makedirs('Cell_optimization_results', exist_ok=True)

# ----- LOOP -----

# Εδώ ο χρήστης επιλέγει ποιο κελί θέλει να μελετήσει
# Η συνάρτηση check_items_in_key ενημερώνει με μήνυμα στοιχεία για το κελί που διάλεξε καθώς
# και αν δεν υπάρχει το συγκεκριμένο κελί ή δεν έχει μέσα αγωγούς. 
# Στις δύο τελευταίες περιπτώσεις πρέπει να διαλέξει κάποιο άλλο κελί. 
# Εδώ πρέπει να δημιουργείται ένα loop και όταν τελειώνει η μελέτη για το συγκεκριμένο κελί, 
# να μπορεί να επιλέγει το επόμενο που θέλει να μελετήσει
row_number_to_keep = 1 
message = check_items_in_key(results_pipe_clusters, fishnet_index, row_number_to_keep) # έλεγχος αν υπάρχουν αγωγοί σε αυτό το κελί
print(message)

#Εδώ να δημιουργείται ένας φάκελος μέσα στο φάκελο "Cell_optimization_results" που θα ονομάζεται "Cell_Priority_{row_number_to_keep}" 
os.makedirs(f'Cell_optimization_results/Cell_Priority_{row_number_to_keep}', exist_ok=True)


# Run functions
pipes_gdf_cell = process_pipes_cell_data(path_pipes, path_fishnet, fishnet_index, row_number_to_keep, results_pipe_clusters, pipe_materials)

pipe_table_trep, LLCCn, ann_budg, xl, xu = calculate_investment_timeseries(pipes_gdf_cell, p_span, 50, a_rel)