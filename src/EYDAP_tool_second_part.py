### Second Part: Lisa Analysis
## Functions 

def read_shapefiles(pipe_shapefile_path, failures_shapefile_path):
  pipe_gdf = gpd.read_file(pipe_shapefile_path).set_crs('EPSG:2100')
  failures_gdf = gpd.read_file(failures_shapefile_path).set_crs('EPSG:2100')
  return pipe_gdf, failures_gdf


def create_fishnet(square_size, pipe_gdf):

  total_bounds = pipe_gdf.total_bounds
  minX, minY, maxX, maxY = total_bounds
  x, y = (minX, minY)
  geom_array = []

  while y <= maxY:
      while x <= maxX:
          geom = geometry.Polygon([(x, y), (x, y + square_size), (x + square_size, y + square_size), (x + square_size, y), (x, y)])
          geom_array.append(geom)
          x += square_size
      x = minX
      y += square_size

  fishnet = gpd.GeoDataFrame(geom_array, columns=['geometry']).set_crs('EPSG:2100')
  return fishnet


def spatial_autocorrelation_analysis(lower_bound_cell, upper_bound_cell, weight_avg_combined_metric, weight_failures, output_path):
  results = []

  pipe_gdf, failures_gdf = read_shapefiles(pipe_shapefile_path, failures_shapefile_path)

  for square_size in range(lower_bound_cell, upper_bound_cell+100, 100):
      fishnet = create_fishnet(square_size, pipe_gdf)

      # Perform spatial join to count failures per feature of the fishnet
      fishnet_failures = fishnet.join(
          gpd.sjoin(failures_gdf, fishnet).groupby("index_right").size().rename("failures"),
          how="left",
      )

      fishnet_failures = fishnet_failures.dropna()

      # Perform spatial join with pipe_gdf to calculate the average Combined Metric per fishnet square
      pipe_metrics = gpd.sjoin(pipe_gdf, fishnet_failures, how='inner', predicate='intersects')
      avg_metrics_per_square = pipe_metrics.groupby("index_right")['cm'].mean()

      # Add the average Combined Metric to the fishnet_failures GeoDataFrame
      fishnet_failures['avg_combined_metric'] = fishnet_failures.index.map(avg_metrics_per_square)

      # Standardize the 'failures' column from 0 to 1
      min_failures = fishnet_failures['failures'].min()
      max_failures = fishnet_failures['failures'].max()
      fishnet_failures['failures_standardized'] = (fishnet_failures['failures'] - min_failures) / (max_failures - min_failures)

      # Add the weighted average column
      fishnet_failures['weighted_avg'] = (
          fishnet_failures['avg_combined_metric'] * weight_avg_combined_metric +
          fishnet_failures['failures_standardized'] * weight_failures
      ) / (weight_avg_combined_metric + weight_failures)

      # Store fishnet_failures as an instance variable
      # fishnet_failures = fishnet_failures

      # Create static choropleth maps (Equal intervals, Quantiles, Natural Breaks)
      # Ensure that the create_choropleth_maps method can handle the new column
      create_choropleth_maps(fishnet_failures, square_size, output_path)

      # Calculate global Moran's I and store results
      y = fishnet_failures['weighted_avg']
      w = lps.weights.Queen.from_dataframe(fishnet_failures, use_index = False)
      w.transform = 'r'
      moran = Moran(y, w)
      results.append((square_size, moran.I, moran.p_sim, moran.z_sim))

  # Print results
  best_square_size = find_best_square_size(results)
  print_results(results, best_square_size, output_path)

  return results, best_square_size


def create_choropleth_maps(fishnet_failures, square_size, output_path):
  # fig, ax = plt.subplots(figsize=(12, 10))
  # fishnet_failures.plot(column='weighted_avg', scheme='equal_interval', k=10, cmap='RdYlGn_r', legend=True, ax=ax,
  #                   legend_kwds={'loc':'center left', 'bbox_to_anchor':(1,0.5), 'fmt':"{:.2f}", 'interval':True})
  # fishnet_failures.boundary.plot(ax=ax)
  # plt.title(f'Average criticality metric per fishnet cell (size = {square_size} m x {square_size} m), Equal intervals', fontsize = 18)
  # plt.axis('off')
  # plt.tight_layout()
  # plt.savefig(output_path + '_' + str(square_size) + '_' +'equal_intervals_coropleth_map.png')

  # Create a static choropleth map of the failure number per grid cell of the fishnet (Quantiles)
  fig, ax = plt.subplots(figsize=(12, 10))
  fishnet_failures.plot(column='weighted_avg', scheme='quantiles', k=10, cmap='RdYlGn_r', legend=True, ax=ax,
                    legend_kwds={'loc':'center left', 'bbox_to_anchor':(1,0.5), 'fmt':"{:.2f}", 'interval':True})
  fishnet_failures.boundary.plot(ax=ax)
  plt.title(f'Average criticality metric per fishnet cell (size = {square_size} m x {square_size} m), Quantiles', fontsize = 18)
  plt.axis('off')
  plt.tight_layout()
  plt.savefig(output_path + str(square_size) + '_' +'coropleth_map.png')

  # # Create a static choropleth map of the failure number per grid cell of the fishnet (Natural Breaks)
  # fig, ax = plt.subplots(figsize=(12, 10))
  # fishnet_failures.plot(column='weighted_avg', scheme='natural_breaks', k=10, cmap='RdYlGn_r', legend=True, ax=ax,
  #                   legend_kwds={'loc':'center left', 'bbox_to_anchor':(1,0.5), 'fmt':"{:.2f}", 'interval':True})
  # fishnet_failures.boundary.plot(ax=ax)
  # plt.title(f'Average criticality metric per fishnet cell (size = {square_size} m x {square_size} m), Natural Breaks', fontsize = 18)
  # plt.axis('off')
  # plt.tight_layout()
  # plt.savefig(output_path + '_' + str(square_size) + '_' +'natural_breaks_coropleth_map.png')


def print_results(results, best_square_size, output_path):
      # Print results here as in your original code
      # Writing the results to a text file

      output_file_path = output_path + 'square_size_comparison_results.txt'

      with open(output_file_path, 'w') as file:
          for size, moran_i, p_value, z_score in results:
              file.write(f"Square Size: {size} m\n")
              file.write(f"Moran's I value: {round(moran_i,4)}\n")
              file.write(f"Moran's I p-value: {round(p_value,4)}\n")
              file.write(f"Moran's I z-score: {round(z_score,4)}\n")
              file.write("\n")
          file.write(f"The optimal square size is: {best_square_size} m\n")
      # Extract data for plotting
      square_sizes, moran_values, p_values, z_scores = zip(*results)

      # Create a plot with multiple y-axes
      fig, ax1 = plt.subplots(figsize=(10, 6))

      # Plot Moran's I on the left y-axis
      ax1.plot(square_sizes, moran_values, 'b-', label="Moran's I", marker='o')
      ax1.set_xlabel("Square Size (m)", fontsize=12)
      ax1.set_ylabel("Moran's I", color='b', fontsize=12)
      ax1.tick_params(axis='y', labelcolor='b')

      # Create right y-axes for p-value and z-score
      ax2 = ax1.twinx()
      ax2.plot(square_sizes, p_values, 'r-', label="p-value", marker='s')
      ax2.set_ylabel("p-value", color='r', fontsize=12)
      ax2.tick_params(axis='y', labelcolor='r')

      ax3 = ax1.twinx()
      ax3.spines['right'].set_position(('outward', 60))
      ax3.plot(square_sizes, z_scores, 'g-', label="z-score", marker='^')
      ax3.set_ylabel("z-score", color='g', fontsize=12)
      ax3.tick_params(axis='y', labelcolor='g')

      # Add grid lines with different colors
      ax1.grid(True, alpha=0.7, color='b')  # Moran's I grid in blue
      ax2.grid(True, linestyle='--', alpha=0.7, color='r')  # p-value grid in red
      ax3.grid(True, linestyle='--', alpha=0.7, color='g')  # z-score grid in green

      # Add labels for each y-axis
      ax1.set_title("Moran's I, p-value, and z-score vs. Square Size", fontsize=16)
      ax1.set_xlabel("Square Size (m)", fontsize=12)

      # Show the legend
      lines, labels = ax1.get_legend_handles_labels()
      lines2, labels2 = ax2.get_legend_handles_labels()
      lines3, labels3 = ax3.get_legend_handles_labels()
      ax1.legend(lines + lines2 + lines3, labels + labels2 + labels3, loc='upper left')

      plt.tight_layout()
      plt.savefig(output_path + 'square_size_comparison_diagram.png')


def find_best_square_size(results):
    # Define p-value thresholds
    p_value_thresholds = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]  # Add more thresholds if needed

    for threshold in p_value_thresholds:
        best_square_size = None
        max_moran_i = None

        for size, moran_i, p_value, z_score in results:
            if p_value < threshold:
                if max_moran_i is None or moran_i > max_moran_i:
                    max_moran_i = moran_i
                    best_square_size = size

        if best_square_size is not None:
            print(f"Best Square Size: {best_square_size} m for p-value threshold: {threshold}")
            print(f"Max Moran's I: {max_moran_i}")
            return best_square_size

    print("No suitable square size found within the defined p-value thresholds.")
    return None


def optimal_fishnet(select_square_size, output_path):

    pipe_gdf, failures_gdf = read_shapefiles(pipe_shapefile_path, failures_shapefile_path)

    # Perform the analysis and store results for the optimal square size
    total_bounds = pipe_gdf.total_bounds
    minX, minY, maxX, maxY = total_bounds
    x, y = (minX, minY)
    geom_array = []
    # Create a fishnet
    x, y = (minX, minY)
    geom_array = []

    # Polygon Size
    square_size = select_square_size
    while y <= maxY:
        while x <= maxX:
            geom = geometry.Polygon([(x,y), (x, y+square_size), (x+square_size, y+square_size), (x+square_size, y), (x, y)])
            geom_array.append(geom)
            x += square_size
        x = minX
        y += square_size

    fishnet = gpd.GeoDataFrame(geom_array, columns=['geometry']).set_crs('EPSG:2100')
    # fishnet.to_file(output_path + str(select_square_size) + '_fishnet_grid.shp') ### dont need to show

    # Perform spatial join to count failures per feature of the fishnet
    fishnet_failures = fishnet.join(
        gpd.sjoin(failures_gdf, fishnet, how='inner', predicate='intersects').groupby("index_right").size().rename("failures"),
        how="left",
    )

    fishnet_failures = fishnet_failures.dropna()

    # Perform spatial join with pipe_gdf to calculate the average Combined Metric per fishnet square
    pipe_metrics = gpd.sjoin(pipe_gdf, fishnet_failures, how='inner', predicate='intersects')
    avg_metrics_per_square = pipe_metrics.groupby("index_right")['cm'].mean()

    # Add the average Combined Metric to the fishnet_failures GeoDataFrame
    fishnet_failures['avg_combined_metric'] = fishnet_failures.index.map(avg_metrics_per_square)

    # Standardize the 'failures' column from 0 to 1
    min_failures = fishnet_failures['failures'].min()
    max_failures = fishnet_failures['failures'].max()
    fishnet_failures['failures_standardized'] = (fishnet_failures['failures'] - min_failures) / (max_failures - min_failures)

    # Add the weighted average column
    fishnet_failures['weighted_avg'] = (
        fishnet_failures['avg_combined_metric'] * weight_avg_combined_metric +
        fishnet_failures['failures_standardized'] * weight_failures
    ) / (weight_avg_combined_metric + weight_failures)

    fishnet_failures = fishnet_failures.dropna()

    # fishnet_failures.to_file(output_path + str(select_square_size)+ '_fishnet_grid_failures.shp') ### dont need to show

    ## Measures of spatial autocorrelation: spatial similarity and attribute similarity

    # Spatial similarity, measured by spatial weights, shows the relative strength of a relationship between pairs of locations

    # Here we compute spatial weights using the Queen contiguity (8 directions)
    w = lps.weights.Queen.from_dataframe(fishnet_failures, use_index = False)
    w.transform = 'r'

    # Attribute similarity, measured by spatial lags, is a summary of the similarity (or dissimilarity) of observations for a variable at different locations
    # The spatial lag takes the average value in each weighted neighborhood
    fishnet_failures['weighted_fail'] = lps.weights.lag_spatial(w, fishnet_failures['weighted_avg'])

    # Global spatial autocorrelation with Moran’s I statistics
    # Moran’s I is a way to measure spatial autocorrelation.
    # In simple terms, it’s a way to quantify how closely values are clustered together in a 2-D space

    # Moran’s I Test uses the following null and alternative hypotheses:
    # Null Hypothesis: The data is randomly dispersed.
    # Alternative Hypothesis: The data is not randomly dispersed, i.e., it is either clustered or dispersed in noticeable patterns.

    # The value of Moran’s I can range from -1 to 1 where:

    # -1: The variable of interest is perfectly dispersed
    # 0: The variable of interest is randomly dispersed
    # 1: The variable of interest is perfectly clustered together
    # The corresponding p-value can be used to determine whether the data is randomly dispersed or not.

    # If the p-value is less than a certain significance level (i.e., α = 0.05),
    # then we can reject the null hypothesis and conclude that the data is
    # spatially clustered together in such a way that it is unlikely to have occurred by chance alone.

    y = fishnet_failures['weighted_avg']
    moran = Moran(y, w)
    print(f"Moran's I value: {moran.I}\np-value: {moran.p_sim}\nZ-score: {moran.z_sim}")

    return fishnet_failures, pipe_gdf


def local_spatial_autocorrelation(select_square_size, output_path):

    fishnet_failures, pipe_gdf = optimal_fishnet(select_square_size, output_path)

    # Perform the local spatial autocorrelation analysis
    y = fishnet_failures['weighted_avg']
    w = lps.weights.Queen.from_dataframe(fishnet_failures, use_index = False)
    w.transform = 'r'
    # Local spatial autocorrelation with Local Indicators of Spatial Association (LISA) statistics
    # While the global spatial autocorrelation can prove the existence of clusters,
    # or a positive spatial autocorrelation between the listing price and their neighborhoods,
    # it does not show where the clusters are.
    # That is when the local spatial autocorrelation resulted from Local Indicators of Spatial
    # Association (LISA) statistics comes into play.
   
    # In general, local Moran’s I values are interpreted as follows:

    # Negative: nearby cases are dissimilar or dispersed e.g. High-Low or Low-High
    # Neutral: nearby cases have no particular relationship or random, absence of pattern
    # Positive: nearby cases are similar or clustered e.g. High-High or Low-Low
    # The LISA uses local Moran's I values to identify the clusters in localized map regions and categorize the clusters into five types:

    # High-High (HH): the area having high values of the variable is surrounded by neighbors that also have high values
    # Low-Low (LL): the area having low values of the variable is surrounded by neighbors that also have low values
    # Low-High (LH): the area having low values of the variable is surrounded by neighbors that have high values
    # High-Low (HL): the area having high values of the variable is surrounded by neighbors that have low values
    # Not Significant (NS)

    # High-High and Low-Low represent positive spatial autocorrelation, while High-Low and Low-High represent negative spatial correlation.

    # Create a LISA cluster map
    moran_local = Moran_Local(y, w)

    fig, ax = plt.subplots(figsize=(12,10))
    lisa_cluster(moran_local, fishnet_failures, p=1,  ax=ax, legend=True,
                  legend_kwds={'loc':'center left', 'bbox_to_anchor':(1,0.5), 'fmt':"{:.0f}"})
    fishnet_failures.boundary.plot(ax=ax)
    plt.title('LISA Cluster Map for average criticality metric per fishnet cell', fontsize = 18)
    plt.tight_layout()
    plt.savefig(output_path + str(select_square_size) + '_' +'final_lisa_cluster_map.png')

    # Create a data frame containing the number of failures and the local moran statistics
    fishnet_failures['fishnet_index'] = fishnet_failures.index
    fishnet_grid_stats_fails = pd.DataFrame(fishnet_failures)
    fishnet_grid_stats_fails["Local Moran's I (LISA)"] = moran_local._statistic

    # Define a function to get the LISA cluster label
    def get_lisa_cluster_label(val):
        if val == 1:
            return "HH"
        elif val == 2:
            return "LH"
        elif val == 3:
            return "LL"
        elif val == 4:
            return "HL"
        else:
            return "NS"

    # Calculate LISA cluster labels for significant clusters
    cluster_labels = [get_lisa_cluster_label(val) for val in moran_local.q]

    # Add a new column with cluster labels for significant clusters (or "NS" for non-significant clusters)
    fishnet_grid_stats_fails['Cluster_Label'] = cluster_labels

    # Sort the cells according to the cluster label and weighted metric
    sorted_fishnet_df = fishnet_grid_stats_fails.sort_values(by=['Cluster_Label', 'weighted_avg'], ascending=[True, False])

    # Spatially join the fishnet grid cells and pipes
    # First, add an explicit 'fishnet_index' column to the fishnet_failures GeoDataFrame
    fishnet_failures['fishnet_index'] = fishnet_failures.index

    # Now perform the spatial join using this new 'fishnet_index' column
    spatial_join = gpd.sjoin(fishnet_failures, pipe_gdf, predicate='intersects')

    # Group the results by 'fishnet_index'
    grouped = spatial_join.groupby('fishnet_index')

    # Create a dictionary to store the results
    results_pipe_clusters = {}

    # Iterate through each group (fishnet cell) and collect the associated pipe labels
    for fishnet_index, group_data in grouped:
        pipe_labels = group_data['LABEL'].tolist()
        results_pipe_clusters[fishnet_index] = pipe_labels

    # final details 
    sorted_fishnet_df['failures'] = sorted_fishnet_df['failures'].round(0)
    sorted_fishnet_df['avg_combined_metric'] = sorted_fishnet_df['avg_combined_metric'].round(3)
    sorted_fishnet_df['weighted_avg'] = sorted_fishnet_df['weighted_avg'].round(3)
    sorted_fishnet_df['failures_standardized'] = sorted_fishnet_df['failures_standardized'].round(3)
    sorted_fishnet_df["Local Moran's I (LISA)"] = sorted_fishnet_df["Local Moran's I (LISA)"].round(3)
    sorted_fishnet_df = sorted_fishnet_df.drop(['weighted_fail','fishnet_index'],axis=1)
    sorted_fishnet_df = sorted_fishnet_df.rename(columns={'avg_combined_metric':'top_metric','failures_standardized':'stand_fail','weighted_avg':'metric_com','Cluster_Label':'Label',"Local Moran's I (LISA)":'localmoran'})


    # Now, the 'results_pipe_clusters' dictionary contains the pipe labels for each fishnet cell with the fishnet index as the key
    sorted_fishnet_gdf = gpd.GeoDataFrame(sorted_fishnet_df).set_crs('EPSG:2100')
    sorted_fishnet_gdf.to_file(output_path + str(select_square_size) + '_fishnets_sorted.shp')

    return sorted_fishnet_df, results_pipe_clusters

## Usage (1): Fing best square size of cells 

# Input 
pipe_shapefile_path = r"/Pipes_WG_export_with_metrics.shp" ####### to shp που έχει εξαχθεί από το πρώτο μέρος του κώδικα
failures_shapefile_path = r"/Vlaves_Combined.shp" #### το shp με τις βλάβες που φορτώνει ο χρήστης

weight_avg_combined_metric = 0.5 ##### επιλογή χρήστη
weight_failures = 0.5 ###### επιλογή χρήστη
lower_bound_cell = 200 ###### επιλογή χρήστη
upper_bound_cell = 1000 ##### επιλογή χρήστη 

from datetime import datetime
import pytz

# Define the GMT+2 timezone
gmt_greece = pytz.timezone('Etc/GMT-2')

# Get the current date and time
timestamp = datetime.now(gmt_greece).strftime("%Y%m%d_%H%M%S")

# Εδώ φτιάχνεται ο υποφάκελος μέσα στο φάκελο Μελέτης
output_path = f'/Fishnet_Grids_{timestamp}/'
os.makedirs(output_path, exist_ok=True)

# Output: best_square_size
results, best_square_size = spatial_autocorrelation_analysis(lower_bound_cell, upper_bound_cell, weight_avg_combined_metric, weight_failures, output_path)

## Usage (2): Ολοκλήρωση ανάλυσης βάσει της επιλογής του square size 

# Input - ο χρήστης επιλέγει αν θα κρατήσει το best_square_size από πάνω ή θα ορίσει ένα δικό του. 
select_square_size = best_square_size ### (εδώ να βγαίνει μήνυμα που να τον ρωτάει αν θα κρατάει αυτό ή να βάλει δικό του)

#Output --> σώζεται ένα shp file στο output path 
sorted_fishnet_df, results_pipe_clusters = local_spatial_autocorrelation(select_square_size, output_path) ##same output path with Usage (1)
