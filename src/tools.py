import networkx as nx
import pandas as pd
import math
import numpy as np
import geopandas as gpd
from shapely import geometry
import libpysal as lps
from esda.moran import Moran, Moran_Local
from splot.esda import lisa_cluster
from kneed import KneeLocator
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from copy import deepcopy
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from typing import List, Union, TypedDict, Tuple
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.optimize import minimize
import pickle
import types
import os
import momepy
import contextily as ctx
import matplotlib.colors as mcolors


def process_shapefile(
    shp_path, weight_closeness, weight_betweenness, weight_bridge, output_path
):
    # Load the shapefile as geodataframe and convert to EPSG 2100
    gdf = gpd.read_file(shp_path)
    gdf = gdf.to_crs(epsg=2100)

    # Convert the GeoDataFrame into a graph
    G = momepy.gdf_to_nx(gdf, approach="primal")

    # Extract nodes and edges
    nodes, edges = momepy.nx_to_gdf(G)

    # Find bridges in the graph
    bridges = list(nx.bridges(G))

    # Function to check if an edge is a bridge
    def is_bridge(edge_row):
        start_coord = edge_row["geometry"].coords[0]
        end_coord = edge_row["geometry"].coords[-1]
        return any(
            [(start_coord, end_coord) in bridges, (end_coord, start_coord) in bridges]
        )

    # Create a list of nodes
    list_of_nodes = list(G.nodes(data=True))

    # Calculate centralities for nodes
    closeness_centrality = nx.closeness_centrality(G)
    betweenness_centrality = nx.betweenness_centrality(G)

    # Create a mapping from node ID to centrality values
    closeness_centrality_mapping = {}
    betweenness_centrality_mapping = {}

    for (x, y), attrs in list_of_nodes:
        node_id = attrs["nodeID"]
        coords = (x, y)
        closeness_centrality_mapping[node_id] = closeness_centrality[coords]
        betweenness_centrality_mapping[node_id] = betweenness_centrality[coords]

    # Add the two metrics as columns in the edges data frame
    edges["cc"] = (
        edges["node_start"].map(closeness_centrality_mapping)
        + edges["node_end"].map(closeness_centrality_mapping)
    ) / 2
    edges["bc"] = (
        edges["node_start"].map(betweenness_centrality_mapping)
        + edges["node_end"].map(betweenness_centrality_mapping)
    ) / 2

    # Normalize the 'closeness_centrality' and 'betweenness_centrality' columns
    edges["cc_norm"] = (edges["cc"] - edges["cc"].min()) / (
        edges["cc"].max() - edges["cc"].min()
    )
    edges["bc_norm"] = (edges["bc"] - edges["bc"].min()) / (
        edges["bc"].max() - edges["bc"].min()
    )

    # Add a 'is_bridge' column to the edges DataFrame
    edges["is_bridge"] = 0  # Initialize all values as 0

    for index, row in edges.iterrows():
        # Assign 1 if the edge is a bridge, otherwise 0
        edges.at[index, "is_bridge"] = 1 if is_bridge(row) else 0

    # Calculate the composite metric
    edges["cm"] = (
        (edges["cc_norm"] * weight_closeness)
        + (edges["bc_norm"] * weight_betweenness)
        + (edges["is_bridge"] * weight_bridge)
    )

    # Create a new DataFrame df_metrics as a copy of edges
    df_metrics = edges.copy(deep=True)

    # Create df_metrics to show to user
    df_metrics = df_metrics[
        [
            "ID",
            "LABEL",
            "D",
            "MATERIAL",
            "USER_L",
            "STRTN_ID",
            "STOPN_ID",
            "cc_norm",
            "bc_norm",
            "is_bridge",
            "cm",
        ]
    ]

    # Round the columns 'cc_norm', 'bc_norm', and 'cm' in df_metrics
    df_metrics["cc_norm"] = df_metrics["cc_norm"].round(
        3
    )  # Replace 2 with your desired number of decimal places
    df_metrics["bc_norm"] = df_metrics["bc_norm"].round(3)
    df_metrics["cm"] = df_metrics["cm"].round(3)

    # Rename columns in df_metrics
    rename_dict = {
        "D": "DIAMETER (mm)",
        "USER_L": "LENGTH (m)",
        "STRTN_ID": "STARTING NODE",
        "STOPN_ID": "STOPPING NODE",
        "cc_norm": "CLOSENESS CENTRALITY",
        "bc_norm": "BETWEENNESS CENTRALITY",
        "is_bridge": "BRIDGE",
        "cm": "COMPOSITE METRIC",
    }
    df_metrics = df_metrics.rename(columns=rename_dict)

    df_metrics.to_csv(output_path + "df_metrics.csv")

    return gdf, G, nodes, edges, df_metrics


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
        if plot_metric == "closeness":
            metric_data = edges["cc_norm"]
            metric_title = "Closeness Centrality"
            fig, ax = plt.subplots(figsize=(figsize, figsize))
            edges.plot(
                ax=ax, linewidth=3, edgecolor=edges["cc_norm"].apply(lambda x: cmap(x))
            )
            ctx.add_basemap(ax, crs=edges.crs.to_string(), source=prov)
            ax.set_title("Closeness Centrality Map")

            # Create a colorbar with the colormap
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=1))
            sm._A = []  # Dummy array for the scalar mappable
            cbar = fig.colorbar(
                sm, ax=ax, orientation="horizontal", fraction=0.02, pad=0.04
            )
            cbar.set_label("Normalized Closeness Centrality")

            ax.axis("off")
            if plot:
                plt.show()
            else:
                plt.savefig(output_path + "cc_map.png")

        elif plot_metric == "betweenness":
            metric_data = edges["bc_norm"]
            metric_title = "Betweenness Centrality"
            # Plot for Betweenness Centrality
            fig, ax = plt.subplots(figsize=(figsize, figsize))
            edges.plot(
                ax=ax, linewidth=3, edgecolor=edges["bc_norm"].apply(lambda x: cmap(x))
            )
            ctx.add_basemap(ax, crs=edges.crs.to_string(), source=prov)
            ax.set_title("Betweenness Centrality Map")

            # Create a colorbar with the colormap
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=1))
            sm._A = []  # Dummy array for the scalar mappable
            cbar = fig.colorbar(
                sm, ax=ax, orientation="horizontal", fraction=0.02, pad=0.04
            )
            cbar.set_label("Normalized Betweenness Centrality")

            ax.axis("off")
            if plot:
                plt.show()
            else:
                plt.savefig(output_path + "bc_map.png")

        elif plot_metric == "bridge":
            metric_data = edges["is_bridge"]
            metric_title = "Bridge Identification"
            # Plot the bridge metric
            fig, ax = plt.subplots(figsize=(figsize, figsize))

            # Plot the edges
            edges_color = edges["is_bridge"].apply(
                lambda x: "red" if x == 1 else "green"
            )
            edges.plot(ax=ax, linewidth=3, edgecolor=edges_color)

            # Add a basemap
            ctx.add_basemap(ax, crs=edges.crs.to_string(), source=prov)

            # Set title
            ax.set_title("Bridge Identification Map")

            # Create a colorbar
            cmap = mcolors.ListedColormap(["green", "red"])
            bounds = [0, 0.5, 1]
            norm = mcolors.BoundaryNorm(bounds, cmap.N)
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
            sm._A = []  # Dummy array for the scalar mappable
            cbar = fig.colorbar(
                sm,
                ax=ax,
                boundaries=bounds,
                ticks=[0.25, 0.75],
                orientation="horizontal",
                fraction=0.02,
                pad=0.04,
            )
            cbar.set_ticklabels(["Non-Bridge", "Bridge"])

            # Turn off axis
            ax.axis("off")

            if plot:
                plt.show()
            else:
                plt.savefig(output_path + "bridge_map.png")

        elif plot_metric == "composite":
            # Plot the composite metric
            # Define the colormap
            cmap = plt.cm.RdYlGn.reversed()
            fig, ax = plt.subplots(figsize=(figsize, figsize))
            edges.plot(
                ax=ax, linewidth=3, edgecolor=edges["cm"].apply(lambda x: cmap(x))
            )
            ctx.add_basemap(ax, crs=edges.crs.to_string(), source=prov)
            ax.set_title("Composite Metric Map")

            # Create a colorbar with the colormap
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=1))
            sm._A = []  # Dummy array for the scalar mappable
            cbar = fig.colorbar(
                sm, ax=ax, orientation="horizontal", fraction=0.02, pad=0.04
            )
            cbar.set_label("Composite Metric")

            ax.axis("off")

            if plot:
                plt.show()
            else:
                plt.savefig(output_path + "cm_map.png")


def save_edge_gdf_shapefile(gdf, output_path):
    if gdf is not None:
        gdf.to_file(output_path, driver="ESRI Shapefile")
        print(f"Edge GeoDataFrame saved to {output_path}")
    else:
        print("No data to save. Run the analysis first to generate data.")


def read_shapefiles(pipe_shapefile_path, failures_shapefile_path):
    pipe_gdf = gpd.read_file(pipe_shapefile_path).set_crs("EPSG:2100")
    failures_gdf = gpd.read_file(failures_shapefile_path).set_crs("EPSG:2100")
    return pipe_gdf, failures_gdf


def create_fishnet(square_size, pipe_gdf):
    total_bounds = pipe_gdf.total_bounds
    minX, minY, maxX, maxY = total_bounds
    x, y = (minX, minY)
    geom_array = []

    while y <= maxY:
        while x <= maxX:
            geom = geometry.Polygon(
                [
                    (x, y),
                    (x, y + square_size),
                    (x + square_size, y + square_size),
                    (x + square_size, y),
                    (x, y),
                ]
            )
            geom_array.append(geom)
            x += square_size
        x = minX
        y += square_size

    fishnet = gpd.GeoDataFrame(geom_array, columns=["geometry"]).set_crs("EPSG:2100")
    return fishnet


def spatial_autocorrelation_analysis(
    pipe_shapefile_path,
    failures_shapefile_path,
    lower_bound_cell,
    upper_bound_cell,
    weight_avg_combined_metric,
    weight_failures,
    output_path,
):
    results = []

    pipe_gdf, failures_gdf = read_shapefiles(
        pipe_shapefile_path, failures_shapefile_path
    )

    for square_size in range(lower_bound_cell, upper_bound_cell + 100, 100):
        fishnet = create_fishnet(square_size, pipe_gdf)

        # Perform spatial join to count failures per feature of the fishnet
        fishnet_failures = fishnet.join(
            gpd.sjoin(failures_gdf, fishnet)
            .groupby("index_right")
            .size()
            .rename("failures"),
            how="left",
        )

        fishnet_failures = fishnet_failures.dropna()

        # Perform spatial join with pipe_gdf to calculate the average Combined Metric per fishnet square
        pipe_metrics = gpd.sjoin(
            pipe_gdf, fishnet_failures, how="inner", predicate="intersects"
        )
        avg_metrics_per_square = pipe_metrics.groupby("index_right")["cm"].mean()

        # Add the average Combined Metric to the fishnet_failures GeoDataFrame
        fishnet_failures["avg_combined_metric"] = fishnet_failures.index.map(
            avg_metrics_per_square
        )

        # Standardize the 'failures' column from 0 to 1
        min_failures = fishnet_failures["failures"].min()
        max_failures = fishnet_failures["failures"].max()
        fishnet_failures["failures_standardized"] = (
            fishnet_failures["failures"] - min_failures
        ) / (max_failures - min_failures)

        # Add the weighted average column
        fishnet_failures["weighted_avg"] = (
            fishnet_failures["avg_combined_metric"] * weight_avg_combined_metric
            + fishnet_failures["failures_standardized"] * weight_failures
        ) / (weight_avg_combined_metric + weight_failures)

        # Store fishnet_failures as an instance variable
        # fishnet_failures = fishnet_failures

        # Create static choropleth maps (Equal intervals, Quantiles, Natural Breaks)
        # Ensure that the create_choropleth_maps method can handle the new column
        create_choropleth_maps(fishnet_failures, square_size, output_path)

        # Calculate global Moran's I and store results
        y = fishnet_failures["weighted_avg"]
        w = lps.weights.Queen.from_dataframe(fishnet_failures, use_index=False)
        w.transform = "r"
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
    fishnet_failures.plot(
        column="weighted_avg",
        scheme="quantiles",
        k=10,
        cmap="RdYlGn_r",
        legend=True,
        ax=ax,
        legend_kwds={
            "loc": "center left",
            "bbox_to_anchor": (1, 0.5),
            "fmt": "{:.2f}",
            "interval": True,
        },
    )
    fishnet_failures.boundary.plot(ax=ax)
    plt.title(
        f"Average criticality metric per fishnet cell (size = {square_size} m x {square_size} m), Quantiles",
        fontsize=18,
    )
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path + str(square_size) + "_" + "coropleth_map.png")

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

    output_file_path = output_path + "square_size_comparison_results.txt"

    with open(output_file_path, "w") as file:
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
    ax1.plot(square_sizes, moran_values, "b-", label="Moran's I", marker="o")
    ax1.set_xlabel("Square Size (m)", fontsize=12)
    ax1.set_ylabel("Moran's I", color="b", fontsize=12)
    ax1.tick_params(axis="y", labelcolor="b")

    # Create right y-axes for p-value and z-score
    ax2 = ax1.twinx()
    ax2.plot(square_sizes, p_values, "r-", label="p-value", marker="s")
    ax2.set_ylabel("p-value", color="r", fontsize=12)
    ax2.tick_params(axis="y", labelcolor="r")

    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("outward", 60))
    ax3.plot(square_sizes, z_scores, "g-", label="z-score", marker="^")
    ax3.set_ylabel("z-score", color="g", fontsize=12)
    ax3.tick_params(axis="y", labelcolor="g")

    # Add grid lines with different colors
    ax1.grid(True, alpha=0.7, color="b")  # Moran's I grid in blue
    ax2.grid(True, linestyle="--", alpha=0.7, color="r")  # p-value grid in red
    ax3.grid(True, linestyle="--", alpha=0.7, color="g")  # z-score grid in green

    # Add labels for each y-axis
    ax1.set_title("Moran's I, p-value, and z-score vs. Square Size", fontsize=16)
    ax1.set_xlabel("Square Size (m)", fontsize=12)

    # Show the legend
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    lines3, labels3 = ax3.get_legend_handles_labels()
    ax1.legend(lines + lines2 + lines3, labels + labels2 + labels3, loc="upper left")

    plt.tight_layout()
    plt.savefig(output_path + "square_size_comparison_diagram.png")


def find_best_square_size(results):
    # Define p-value thresholds
    p_value_thresholds = [
        0.05,
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
        0.35,
        0.40,
        0.45,
        0.50,
    ]  # Add more thresholds if needed

    for threshold in p_value_thresholds:
        best_square_size = None
        max_moran_i = None

        for size, moran_i, p_value, z_score in results:
            if p_value < threshold:
                if max_moran_i is None or moran_i > max_moran_i:
                    max_moran_i = moran_i
                    best_square_size = size

        if best_square_size is not None:
            print(
                f"Best Square Size: {best_square_size} m for p-value threshold: {threshold}"
            )
            print(f"Max Moran's I: {max_moran_i}")
            return best_square_size

    print("No suitable square size found within the defined p-value thresholds.")
    return None


def optimal_fishnet(
    pipe_shapefile_path,
    failures_shapefile_path,
    weight_avg_combined_metric,
    weight_failures,
    select_square_size,
    output_path,
):
    pipe_gdf, failures_gdf = read_shapefiles(
        pipe_shapefile_path, failures_shapefile_path
    )

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
            geom = geometry.Polygon(
                [
                    (x, y),
                    (x, y + square_size),
                    (x + square_size, y + square_size),
                    (x + square_size, y),
                    (x, y),
                ]
            )
            geom_array.append(geom)
            x += square_size
        x = minX
        y += square_size

    fishnet = gpd.GeoDataFrame(geom_array, columns=["geometry"]).set_crs("EPSG:2100")
    # fishnet.to_file(output_path + str(select_square_size) + '_fishnet_grid.shp') ### dont need to show

    # Perform spatial join to count failures per feature of the fishnet
    fishnet_failures = fishnet.join(
        gpd.sjoin(failures_gdf, fishnet, how="inner", predicate="intersects")
        .groupby("index_right")
        .size()
        .rename("failures"),
        how="left",
    )

    fishnet_failures = fishnet_failures.dropna()

    # Perform spatial join with pipe_gdf to calculate the average Combined Metric per fishnet square
    pipe_metrics = gpd.sjoin(
        pipe_gdf, fishnet_failures, how="inner", predicate="intersects"
    )
    avg_metrics_per_square = pipe_metrics.groupby("index_right")["cm"].mean()

    # Add the average Combined Metric to the fishnet_failures GeoDataFrame
    fishnet_failures["avg_combined_metric"] = fishnet_failures.index.map(
        avg_metrics_per_square
    )

    # Standardize the 'failures' column from 0 to 1
    min_failures = fishnet_failures["failures"].min()
    max_failures = fishnet_failures["failures"].max()
    fishnet_failures["failures_standardized"] = (
        fishnet_failures["failures"] - min_failures
    ) / (max_failures - min_failures)

    # Add the weighted average column
    fishnet_failures["weighted_avg"] = (
        fishnet_failures["avg_combined_metric"] * weight_avg_combined_metric
        + fishnet_failures["failures_standardized"] * weight_failures
    ) / (weight_avg_combined_metric + weight_failures)

    fishnet_failures = fishnet_failures.dropna()

    # fishnet_failures.to_file(output_path + str(select_square_size)+ '_fishnet_grid_failures.shp') ### dont need to show

    ## Measures of spatial autocorrelation: spatial similarity and attribute similarity

    # Spatial similarity, measured by spatial weights, shows the relative strength of a relationship between pairs of locations

    # Here we compute spatial weights using the Queen contiguity (8 directions)
    w = lps.weights.Queen.from_dataframe(fishnet_failures, use_index=False)
    w.transform = "r"

    # Attribute similarity, measured by spatial lags, is a summary of the similarity (or dissimilarity) of observations for a variable at different locations
    # The spatial lag takes the average value in each weighted neighborhood
    fishnet_failures["weighted_fail"] = lps.weights.lag_spatial(
        w, fishnet_failures["weighted_avg"]
    )

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

    y = fishnet_failures["weighted_avg"]
    moran = Moran(y, w)
    print(f"Moran's I value: {moran.I}\np-value: {moran.p_sim}\nZ-score: {moran.z_sim}")

    return fishnet_failures, pipe_gdf


def local_spatial_autocorrelation(
    pipe_shapefile_path,
    failures_shapefile_path,
    weight_avg_combined_metric,
    weight_failures,
    select_square_size,
    output_path,
):
    fishnet_failures, pipe_gdf = optimal_fishnet(
        pipe_shapefile_path=pipe_shapefile_path,
        failures_shapefile_path=failures_shapefile_path,
        weight_avg_combined_metric=weight_avg_combined_metric,
        weight_failures=weight_failures,
        select_square_size=select_square_size,
        output_path=output_path,
    )

    # Perform the local spatial autocorrelation analysis
    y = fishnet_failures["weighted_avg"]
    w = lps.weights.Queen.from_dataframe(fishnet_failures)
    w.transform = "r"
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

    fig, ax = plt.subplots(figsize=(12, 10))
    lisa_cluster(
        moran_local,
        fishnet_failures,
        p=1,
        ax=ax,
        legend=True,
        legend_kwds={"loc": "center left", "bbox_to_anchor": (1, 0.5), "fmt": "{:.0f}"},
    )
    fishnet_failures.boundary.plot(ax=ax)
    plt.title(
        "LISA Cluster Map for average criticality metric per fishnet cell", fontsize=18
    )
    plt.tight_layout()
    plt.savefig(
        output_path + str(select_square_size) + "_" + "final_lisa_cluster_map.png"
    )

    # Create a data frame containing the number of failures and the local moran statistics
    fishnet_failures["fishnet_index"] = fishnet_failures.index
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
    fishnet_grid_stats_fails["Cluster_Label"] = cluster_labels

    # Sort the cells according to the cluster label and weighted metric
    sorted_fishnet_df = fishnet_grid_stats_fails.sort_values(
        by=["Cluster_Label", "weighted_avg"], ascending=[True, False]
    )

    # Spatially join the fishnet grid cells and pipes
    # First, add an explicit 'fishnet_index' column to the fishnet_failures GeoDataFrame
    fishnet_failures["fishnet_index"] = fishnet_failures.index

    # Now perform the spatial join using this new 'fishnet_index' column
    spatial_join = gpd.sjoin(fishnet_failures, pipe_gdf, predicate="intersects")

    # Group the results by 'fishnet_index'
    grouped = spatial_join.groupby("fishnet_index")

    # Create a dictionary to store the results
    results_pipe_clusters = {}

    # Iterate through each group (fishnet cell) and collect the associated pipe labels
    for fishnet_index, group_data in grouped:
        pipe_labels = group_data["LABEL"].tolist()
        results_pipe_clusters[fishnet_index] = pipe_labels

    # final details
    fishnet_index = sorted_fishnet_df["fishnet_index"]  # <-- Nees allages

    sorted_fishnet_df["failures"] = sorted_fishnet_df["failures"].round(0)
    sorted_fishnet_df["avg_combined_metric"] = sorted_fishnet_df[
        "avg_combined_metric"
    ].round(3)
    sorted_fishnet_df["weighted_avg"] = sorted_fishnet_df["weighted_avg"].round(3)
    sorted_fishnet_df["failures_standardized"] = sorted_fishnet_df[
        "failures_standardized"
    ].round(3)
    sorted_fishnet_df["Local Moran's I (LISA)"] = sorted_fishnet_df[
        "Local Moran's I (LISA)"
    ].round(3)
    sorted_fishnet_df = sorted_fishnet_df.drop(
        ["weighted_fail", "fishnet_index"], axis=1
    )
    sorted_fishnet_df = sorted_fishnet_df.rename(
        columns={
            "avg_combined_metric": "top_metric",
            "failures_standardized": "stand_fail",
            "weighted_avg": "metric_com",
            "Cluster_Label": "Label",
            "Local Moran's I (LISA)": "localmoran",
        }
    )
    sorted_fishnet_df = sorted_fishnet_df.reset_index()
    sorted_fishnet_df.rename(columns={"index": "cell_index"}, inplace=True)
    sorted_fishnet_df = sorted_fishnet_df.reset_index()
    sorted_fishnet_df.rename(columns={"index": "Priority"}, inplace=True)
    sorted_fishnet_df["Priority"] += 1
    sorted_fishnet_df.set_index("cell_index", inplace=True)

    # Now, the 'results_pipe_clusters' dictionary contains the pipe labels for each fishnet cell with the fishnet index as the key
    sorted_fishnet_gdf = gpd.GeoDataFrame(sorted_fishnet_df).set_crs("EPSG:2100")
    sorted_fishnet_gdf.to_file(
        output_path + str(select_square_size) + "_fishnets_sorted.shp"
    )

    return sorted_fishnet_df, results_pipe_clusters, fishnet_index


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
 
    
def check_items_in_key(dictionary, fishnet_index, row_number_to_keep) -> Tuple[str, bool]:
    try:
        # Attempt to obtain cell_index
        cell_index = fishnet_index.iloc[row_number_to_keep - 1]
    except IndexError:
        # If row_number_to_keep is out of bounds
        return f"Η γραμμή {row_number_to_keep} δεν υπάρχει στο shapefile.", False #ξαναβαλε
    except Exception as e:
        # Handle other potential errors
        return f"Προέκυψε σφάλμα: {e}", False

    # Check if the cell_index exists in the dictionary
    if cell_index not in dictionary:
        return f"Το κελί '{cell_index}' δεν υπάρχει.", False #δεν υπαρχει 
    elif not dictionary[cell_index]:
        return f"Το κελί '{cell_index}' δεν περιέχει αγωγούς καθώς αυτοί έχουν ανατεθεί σε γειτονικά.", False ###ξαναβαλε
    else:
        number = len(dictionary[cell_index])
        return f"Το κελί '{cell_index}' περιέχει '{number}' αγωγούς.", True #προχωραμε 
        

def manipulate_opt_results(edges, X, F, pipe_table_trep, pipes_gdf_cell):
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


# Define the optimization problem
class MyProblem(ElementwiseProblem):
    def __init__(self, pipe_table_trep, p_span, LLCCn, xl, xu):
        super().__init__(n_var=len(pipe_table_trep.index), n_obj=2, xl=xl, xu=xu)
        self.pipe_table_trep = pipe_table_trep
        self.p_span = p_span
        self.LLCCn = LLCCn
        self.xl = xl
        self.xu = xu


    def _evaluate(self, x, out, *args, **kwargs):

        lcc_n = lcc_tot_net(x, self.pipe_table_trep, self.p_span)
        f1 = lcc_n - self.LLCCn

        inv_series = investment_series(x, self.pipe_table_trep, self.p_span)
        #f2 = inv_series[0].std()


        # Calculate the second derivative (approximated by differences of differences)
        first_diff = np.diff(inv_series[0])
        second_diff = np.diff(first_diff)

        # Regularization term: sum of squares of the second derivative
        regularization_term = np.sum(second_diff**2)
        f2 = regularization_term  # Smaller values indicate a smoother series with less curvature

        out["F"] = [f1, f2]


# PART 4 functions


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
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(output_string)