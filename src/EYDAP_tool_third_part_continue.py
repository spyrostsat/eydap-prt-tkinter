#-------------------------------------------------PART 3 (continue)-------------------------------------------------------------
from kneed import KneeLocator

# Define the optimization problem
class MyProblem(ElementwiseProblem):

    def __init__(self):
        super().__init__(n_var=len(pipe_table_trep.index),
                         n_obj=2,
                         xl=xl,
                         xu=xu)

    def _evaluate(self, x, out, *args, **kwargs):

        lcc_n = lcc_tot_net(x, pipe_table_trep, p_span)
        f1 = lcc_n - LLCCn

        inv_series = investment_series(x, pipe_table_trep, p_span)
        #f2 = inv_series[0].std()


        # Calculate the second derivative (approximated by differences of differences)
        first_diff = np.diff(inv_series[0])
        second_diff = np.diff(first_diff)

        # Regularization term: sum of squares of the second derivative
        regularization_term = np.sum(second_diff**2)
        f2 = regularization_term  # Smaller values indicate a smoother series with less curvature

        out["F"] = [f1, f2]

def manipulate_opt_results(X, F, pipe_table_trep, pipes_gdf_cell):
    # Simulate a Pareto front for demonstration
    f1_values = F[:,0]
    f2_values = F[:,1]

    kn = KneeLocator(f1_values, f2_values, curve='convex', direction='decreasing')

    # Get the index of the knee point
    ind_opt = next((i for i, val in enumerate(f1_values) if val == kn.knee), None)

    # Get the optimal X values
    X_opt = X[ind_opt,:]
    
    # Return a shapefile which contains t* and t_opt
    pipes_gdf_cell['t_star'] = pipe_table_trep['t_rep']
    pipes_gdf_cell['t_opt'] = X_opt
    pipes_gdf_cell_merged = pd.merge(pipes_gdf_cell, edges[[ 'LABEL', 'geometry']], on='LABEL', how='left')
    pipes_gdf_cell_merged = gpd.GeoDataFrame(pipes_gdf_cell_merged, geometry='geometry')
    pipes_gdf_cell_merged = pipes_gdf_cell_merged.set_crs('EPSG:2100')
    
    return pipes_gdf_cell_merged


## USAGE 

# number of pipes in this cell
number_of_pipes = pipe_table_trep.count()[0]

# define 3 hyperparameters for optimization 
pop_size = int(round((7.17*number_of_pipes - 1.67),-1)) # linear equation going through (10,70) and (70,500)
n_gen = int(round((1.33*number_of_pipes + 6.67),-1)) # linear equation going through (70,100) and (10,20)
n_offsprings = int(max(round((pop_size/5),-1),5))

problem = MyProblem()

algorithm = NSGA2(
    pop_size= pop_size, 
    n_offsprings= n_offsprings,
    sampling=IntegerRandomSampling(),
    crossover=SBX(prob=0.9, eta=15, repair=RoundingRepair()),
    mutation=PM(eta=20, repair=RoundingRepair()),
    eliminate_duplicates=True
)

res = minimize(problem,
               algorithm,
               seed=1,
               termination=('n_gen', n_gen), # p.x. 5 
               save_history=True,
               verbose=True)


X = res.X
F = res.F

# Run function for making final geodataframe
pipes_gdf_cell_merged = manipulate_opt_results(X, F, pipe_table_trep, pipes_gdf_cell)

# Save the shape file into Cell_optimization_results/Cell_Priority_# 
pipes_gdf_cell_merged.to_file(f'Cell_optimization_results/Cell_Priority_{row_number_to_keep}' +'/Priority_' +str(row_number_to_keep) +'_cell_optimal_replacement.shp')