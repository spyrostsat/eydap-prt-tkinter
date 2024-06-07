## Import packages
import networkx as nx
import pandas as pd
import math
import numpy as np
import geopandas as gpd
from shapely import geometry
import libpysal as lps
from esda.moran import Moran, Moran_Local
from splot.esda import lisa_cluster
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from copy import deepcopy
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.optimize import minimize
import pickle
import types
import os
import momepy
import contextily as ctx
import matplotlib.colors as mcolors


## First function 

def process_shapefile(shp_path, weight_closeness, weight_betweenness, weight_bridge, output_path):
    # Load the shapefile as geodataframe and convert to EPSG 2100
    gdf = gpd.read_file(shp_path)
    gdf = gdf.to_crs(epsg=2100)

    # Convert the GeoDataFrame into a graph
    G = momepy.gdf_to_nx(gdf, approach='primal')

    # Extract nodes and edges
    nodes, edges = momepy.nx_to_gdf(G)

    # Find bridges in the graph
    bridges = list(nx.bridges(G))

    # Function to check if an edge is a bridge
    def is_bridge(edge_row):
        start_coord = (edge_row['geometry'].coords[0])
        end_coord = (edge_row['geometry'].coords[-1])
        return any([(start_coord, end_coord) in bridges, (end_coord, start_coord) in bridges])

    # Create a list of nodes
    list_of_nodes = list(G.nodes(data=True))

    # Calculate centralities for nodes
    closeness_centrality = nx.closeness_centrality(G)
    betweenness_centrality = nx.betweenness_centrality(G)

    # Create a mapping from node ID to centrality values
    closeness_centrality_mapping = {}
    betweenness_centrality_mapping = {}

    for (x, y), attrs in list_of_nodes:
        node_id = attrs['nodeID']
        coords = (x, y)
        closeness_centrality_mapping[node_id] = closeness_centrality[coords]
        betweenness_centrality_mapping[node_id] = betweenness_centrality[coords]

    # Add the two metrics as columns in the edges data frame
    edges['cc'] = (edges['node_start'].map(closeness_centrality_mapping) + edges['node_end'].map(closeness_centrality_mapping)) / 2
    edges['bc'] = (edges['node_start'].map(betweenness_centrality_mapping) + edges['node_end'].map(betweenness_centrality_mapping)) / 2

    # Normalize the 'closeness_centrality' and 'betweenness_centrality' columns
    edges['cc_norm'] = (edges['cc'] - edges['cc'].min()) / (edges['cc'].max() - edges['cc'].min())
    edges['bc_norm'] = (edges['bc'] - edges['bc'].min()) / (edges['bc'].max() - edges['bc'].min())

    # Add a 'is_bridge' column to the edges DataFrame
    edges['is_bridge'] = 0  # Initialize all values as 0

    for index, row in edges.iterrows():
      # Assign 1 if the edge is a bridge, otherwise 0
      edges.at[index, 'is_bridge'] = 1 if is_bridge(row) else 0

    # Calculate the composite metric
    edges['cm'] = ((edges['cc_norm'] * weight_closeness) +
                   (edges['bc_norm'] * weight_betweenness) +
                   (edges['is_bridge'] * weight_bridge))

    # Create a new DataFrame df_metrics as a copy of edges
    df_metrics = edges.copy(deep=True)

    # Create df_metrics to show to user
    df_metrics = df_metrics[['ID','LABEL','D','MATERIAL','USER_L','STRTN_ID','STOPN_ID','cc_norm','bc_norm','is_bridge','cm']]

    # Round the columns 'cc_norm', 'bc_norm', and 'cm' in df_metrics
    df_metrics['cc_norm'] = df_metrics['cc_norm'].round(3)  # Replace 2 with your desired number of decimal places
    df_metrics['bc_norm'] = df_metrics['bc_norm'].round(3)
    df_metrics['cm'] = df_metrics['cm'].round(3)

    # Rename columns in df_metrics
    rename_dict = {
        'D'      : 'DIAMETER (mm)',
        'USER_L' : 'LENGTH (m)',
        'STRTN_ID': 'STARTING NODE',
        'STOPN_ID': 'STOPPING NODE',
        'cc_norm': 'CLOSENESS CENTRALITY',
        'bc_norm': 'BETWEENNESS CENTRALITY',
        'is_bridge': 'BRIDGE',
        'cm': 'COMPOSITE METRIC',

        }
    df_metrics = df_metrics.rename(columns=rename_dict)

    df_metrics.to_csv(output_path + 'df_metrics.csv')

    return gdf, G, nodes, edges, df_metrics

# First Function Usage:

# Load WDN shapefile in the correct format
shp_path = r'Pipes_WG_export.shp'

# Define weights and process shapefile
weight_closeness = 1/3
weight_betweenness = 1/3
weight_bridge = 1/3

# Path to save the 'df_metrics' DataFrame, making it visible to the user.
output_path = ''

# Process shapefile and save df_metrics
gdf, G, nodes, edges, df_metrics = process_shapefile(shp_path, weight_closeness, weight_betweenness, weight_bridge, output_path)


## Second Function 

def plot_metrics(gdf, G, nodes, edges, plot_metrics, figsize, plot, output_path):

    # Check if plot_metrics is a list, if not convert it to a list
    if not isinstance(plot_metrics, list):
        plot_metrics = [plot_metrics]

    # Define the colormap
    cmap = plt.cm.RdYlGn.reversed()

    # Define the tiles server
    prov = ctx.providers.CartoDB.Positron

    # Number of plots
    num_plots = len(plot_metrics)

    for _, plot_metric in enumerate(plot_metrics):

        if plot_metric == 'closeness':
            metric_data = edges['cc_norm']
            metric_title = 'Closeness Centrality'
            fig, ax = plt.subplots(figsize=(figsize, figsize))
            edges.plot(ax=ax, linewidth=3, edgecolor=edges['cc_norm'].apply(lambda x: cmap(x)))
            ctx.add_basemap(ax, crs=edges.crs.to_string(),source=prov)
            ax.set_title('Closeness Centrality Map')

            # Create a colorbar with the colormap
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=1))
            sm._A = []  # Dummy array for the scalar mappable
            cbar = fig.colorbar(sm, ax=ax, orientation='horizontal', fraction=0.02, pad=0.04)
            cbar.set_label('Normalized Closeness Centrality')

            ax.axis('off')
            if plot:
              plt.show()
            else:
              plt.savefig(output_path + 'cc_map.png')


        elif plot_metric == 'betweenness':
            metric_data = edges['bc_norm']
            metric_title = 'Betweenness Centrality'
            # Plot for Betweenness Centrality
            fig, ax = plt.subplots(figsize=(figsize, figsize))
            edges.plot(ax=ax, linewidth=3, edgecolor=edges['bc_norm'].apply(lambda x: cmap(x)))
            ctx.add_basemap(ax, crs=edges.crs.to_string(),source=prov)
            ax.set_title('Betweenness Centrality Map')

            # Create a colorbar with the colormap
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=1))
            sm._A = []  # Dummy array for the scalar mappable
            cbar = fig.colorbar(sm, ax=ax, orientation='horizontal', fraction=0.02, pad=0.04)
            cbar.set_label('Normalized Betweenness Centrality')

            ax.axis('off')
            if plot:
              plt.show()
            else:
              plt.savefig(output_path + 'bc_map.png')

        elif plot_metric == 'bridge':
            metric_data = edges['is_bridge']
            metric_title = 'Bridge Identification'
            # Plot the bridge metric
            fig, ax = plt.subplots(figsize=(figsize, figsize))

            # Plot the edges
            edges_color = edges['is_bridge'].apply(lambda x: 'red' if x == 1 else 'green')
            edges.plot(ax=ax, linewidth=3, edgecolor=edges_color)

            # Add a basemap
            ctx.add_basemap(ax, crs=edges.crs.to_string(),source=prov)

            # Set title
            ax.set_title('Bridge Identification Map')

            # Create a colorbar
            cmap = mcolors.ListedColormap(['green', 'red'])
            bounds = [0, 0.5, 1]
            norm = mcolors.BoundaryNorm(bounds, cmap.N)
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
            sm._A = []  # Dummy array for the scalar mappable
            cbar = fig.colorbar(sm, ax=ax, boundaries=bounds, ticks=[0.25, 0.75], orientation='horizontal', fraction=0.02, pad=0.04)
            cbar.set_ticklabels(['Non-Bridge', 'Bridge'])

            # Turn off axis
            ax.axis('off')

            if plot:
              plt.show()
            else:
              plt.savefig(output_path + 'bridge_map.png')

        elif plot_metric == 'composite':
            # Plot the composite metric
            # Define the colormap
            cmap = plt.cm.RdYlGn.reversed()
            fig, ax = plt.subplots(figsize=(figsize, figsize))
            edges.plot(ax=ax, linewidth=3, edgecolor=edges['cm'].apply(lambda x: cmap(x)))
            ctx.add_basemap(ax, crs=edges.crs.to_string(),source=prov)
            ax.set_title('Composite Metric Map')

            # Create a colorbar with the colormap
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=1))
            sm._A = []  # Dummy array for the scalar mappable
            cbar = fig.colorbar(sm, ax=ax, orientation='horizontal', fraction=0.02, pad=0.04)
            cbar.set_label('Composite Metric')

            ax.axis('off')

            if plot:
              plt.show()
            else:
              plt.savefig(output_path + 'cm_map.png')

# Second Function Usage:

# Specify the metrics to plot
plot_metric = ['closeness', 'betweenness', 'bridge', 'composite']  # Choose a list adding any of 'closeness', 'betweenness', 'bridge', or 'composite'

# True for plotting, False for saving the png's
plot_or_save = False

# Output path for saving the png's
output_path = ''

# Call the function with your parameters
plot_metrics(gdf, G, nodes, edges, plot_metric, 8, plot_or_save, output_path)

## Third Function

# Save the geodataframe as shapefile
def save_edge_gdf_shapefile(gdf, output_path):
    if gdf is not None:
        gdf.to_file(output_path, driver='ESRI Shapefile')
        print(f'Edge GeoDataFrame saved to {output_path}')
    else:
        print('No data to save. Run the analysis first to generate data.')

output_path = ''

save_edge_gdf_shapefile(edges, output_path + 'Pipes_WG_export_with_metrics.shp')