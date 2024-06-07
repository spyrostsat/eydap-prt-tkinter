import PySimpleGUI as sg
from src.utils import *
import os
import sys
from src.tools import *
import ctypes
import platform
import warnings
from typing import List
from src.scenarios import Scenario


warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
if platform.system() == "Windows":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)


class PipeReplacementTool:

    def __init__(self):
        self.active_scen = Scenario.get_active()
        self.layout = [
            [
                sg.Menu(
                    [
                        [
                            "Scenarios",
                            ["New", "Open...", "Save As...", "Delete", "---", "Exit"],
                        ],
                        [
                            "Help",
                            ["About", "Contact Us"],
                        ]
                    ]
                ),
                [ sg.Text("Welcome to the Pipe Replacement Tool", font=("Arial", 18, "bold"))],
                [ sg.Text("%s"%self.active_scen.short_name if self.active_scen else "No active scenario", key="-ACTIVE_SCENARIO-", font=("Arial", 12, "bold"))],
                # Lets load EYDAP logo]
                [sg.Column([[sg.Image(filename="icon.png")]], justification="center")],
                [sg.Column([[
                    sg.Button("Step 1", disabled=True, key="-STEP1-"),
                    sg.Button("Step 2", disabled=True, key="-STEP2-"),
                    sg.Button("Step 3", disabled=True, key="-STEP3-"),
                    sg.Button("Step 4", disabled=True, key="-STEP4-"),
                    ]], justification="center")],

            ]
        ]

        self.window = sg.Window(
            "EYDAP :: Pipe Replacement Tool",
            self.layout,
            resizable=False,
            finalize=True,
            icon="icon.ico",
            size=(sg.Window.get_screen_size())  # Open the window in maximized mode
        )

        self.step1_completed = False
        self.step2_completed = False

        self.projects_folder = os.path.join(os.path.expanduser("~"), "Pipe Replacement Tool Projects")
        self.const_pipe_materials = {"Asbestos Cement": 50, "Steel": 40, "PVC": 30, "HDPE": 12, "Cast iron": 40}

        self.project_name = None
        self.network_shapefile = None
        self.damage_shapefile = None
        self.df_metrics = None
        self.edges = None
        self.unique_pipe_materials_names = None
        self.pipe_materials = {}
        self.path_fishnet = None
        self.sorted_fishnet_df = None
        self.results_pipe_clusters = None
        self.fishnet_index = None
        self.select_square_size = None
        self.weight_avg_combined_metric = None
        self.weight_failures = None
        self.step2_output_path = None

        self.step1_result_shapefile = None




    def update_active_scenario_display(self):
        """ Update the active scenario display in the GUI. """
        active_scenario = Scenario.get_active()
        self.window["-ACTIVE_SCENARIO-"].update(active_scenario.short_name if active_scenario else "No active scenario")



    def run(self):

        if self.active_scen:
            Scenario.set_active(self.active_scen.scenario_id)
            if self.active_scen.status == 1:  # Initialised
                self.window["-STEP1-"].update(disabled=False)

        sg.set_options(icon="icon.ico")
        while True:
            event, values = self.window.read()
            if event == sg.WINDOW_CLOSED:
                break

            if event == "New":
                Scenario.create(self)
                self.update_active_scenario_display()

            if event == "Open...":
                Scenario.list()
                self.update_active_scenario_display()

            if event == "Save As...":
                scen = Scenario.get_active()
                if scen:
                    new_scen = scen.save_as()
                    if new_scen:
                        self.update_active_scenario_display()

            if event == "Delete":
                scen = Scenario.get_active()
                if scen:
                    short_name = scen.short_name
                    if sg.popup_yes_no(f"Are you sure you want to delete the scenario '{short_name}'?") == "Yes":
                        scen.delete()
                        self.update_active_scenario_display()

            if event == "About":
                sg.popup("Pipe Replacement Tool", "Version 1.0", "Developed by NTUA - UWMH", "2024")

            if event == "Contact Us":
                sg.popup("For any questions or issues, please contact us at:", "email: pdimas@mail.ntua.gr")


            if self.network_shapefile and self.damage_shapefile:
                self.window["-STEP1-"].update(disabled=False)

                if self.step1_completed:  # workaround to keep the step 1 button disabled
                    self.window["-STEP1-"].update(disabled=True)

            if event == "-STEP1-":
                self.step1()

            if event == "-STEP2-":
                self.step2()

            if event == "-STEP3-":
                self.step3()

            if event == "-STEP4-":
                self.step4()

            if event == "Exit":
                break

        self.window.close()
        sys.exit()  # Ensure the script exits

    def step1(self):
        layout = [
            [
                sg.Push(),
                sg.Text("Closeness Centrality Weight:"),
                sg.Slider(
                    range=(0, 1),
                    resolution=0.01,
                    orientation="h",
                    key="-Closeness Weight-",
                    enable_events=True,
                    default_value=0.33,
                ),
            ],
            [
                sg.Push(),
                sg.Text("Betweenness Centrality Weight:"),
                sg.Slider(
                    range=(0, 1),
                    resolution=0.01,
                    orientation="h",
                    key="-Betweenness Weight-",
                    enable_events=True,
                    default_value=0.33,
                    expand_x=True,
                ),
            ],
            [
                sg.Push(),
                sg.Text("Bridge Weight:"),
                sg.Slider(
                    range=(0, 1),
                    resolution=0.01,
                    orientation="h",
                    key="-Bridge Weight-",
                    enable_events=True,
                    default_value=0.34,
                ),
            ],
            [
                sg.Column(
                    [
                        [sg.Button("Calculate", key="-CALCULATE-")],
                    ],
                    justification="center",
                )
            ],
            [sg.Text("Calculating ...", key="-CALC Message-", visible=False)],
            [sg.Button("Proceed to Step 2", key="-PROCEED-", visible=False)],
        ]

        step1_window = sg.Window("Step 1", layout)

        while True:
            event, values = step1_window.read()
            if event == sg.WINDOW_CLOSED:
                break
            if event == "-PROCEED-":
                step1_window.close()
                break
            if event == "-CALCULATE-":
                closeness_weight = values["-Closeness Weight-"]
                betweenness_weight = values["-Betweenness Weight-"]
                bridge_weight = values["-Bridge Weight-"]
                total = closeness_weight + betweenness_weight + bridge_weight

                if not (0.99 <= total <= 1.01):
                    sg.popup_error("The sum of all sliders must be 1. Please adjust the sliders.")
                else:
                    step1_window["-CALC Message-"].update(visible=True)
                    step1_window.refresh()
                    step1_window.perform_long_operation(
                        lambda: self.step1_calculations(
                            closeness_weight,
                            betweenness_weight,
                            bridge_weight,
                            self.projects_folder,
                        ),
                        "-STEP1 CALCULATIONS-",
                    )

            if event == "-STEP1 CALCULATIONS-":
                gdf, G, nodes, edges, df_metrics, output_path = values["-STEP1 CALCULATIONS-"]
                step1_window["-CALCULATE-"].update(visible=False)
                step1_window["-CALC Message-"].update(visible=False)
                step1_window["-PROCEED-"].update(visible=True)
                step1_window.refresh()
                self.step1_completed = True
                self.df_metrics = df_metrics
                self.unique_pipe_materials_names = df_metrics["MATERIAL"].unique()

                for material_name in self.unique_pipe_materials_names:
                    self.pipe_materials[material_name] = self.const_pipe_materials.get(material_name)

                self.step1_result_shapefile = output_path

                # Update the main window to enable the next step
                self.window["-STEP1-"].update(disabled=True)
                self.window["-STEP2-"].update(disabled=False)

    def step1_calculations(self, closeness_weight, betweenness_weight, bridge_weight, output_path):
        gdf, G, nodes, edges, df_metrics = process_shapefile(
            self.network_shapefile,
            closeness_weight,
            betweenness_weight,
            bridge_weight,
            output_path,
        )
        self.edges = edges
        plot_metrics(
            gdf,
            G,
            nodes,
            edges,
            ["closeness", "betweenness", "bridge", "composite"],
            8,
            False,
            output_path,
        )
        output_path = os.path.join(
            self.projects_folder,
            "shp_with_metrics",
            "Pipes_WG_export_with_metrics.shp",
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        save_edge_gdf_shapefile(
            edges,
            output_path,
        )
        return gdf, G, nodes, edges, df_metrics, output_path

    def step2(self):
        layout = [
            [
                sg.Push(),
                sg.Text("Weighted Average combined metric:"),
                sg.Slider(
                    range=(0, 1),
                    resolution=0.01,
                    orientation="h",
                    key="-Weighted Average-",
                    enable_events=True,
                    default_value=0.5,
                ),
            ],
            [
                sg.Push(),
                sg.Text("Failures Weight:"),
                sg.Slider(
                    range=(0, 1),
                    resolution=0.01,
                    orientation="h",
                    key="-Failures Weight-",
                    enable_events=True,
                    default_value=0.5,
                ),
            ],
            [
                sg.Push(),
                sg.Text("Cell Lower Bound:"),
                sg.Slider(
                    range=(100, 1000),
                    resolution=100,
                    orientation="h",
                    key="-Cell Lower Bound-",
                    enable_events=True,
                    default_value=200,
                ),
            ],
            [
                sg.Push(),
                sg.Text("Cell Upper Bound:"),
                sg.Slider(
                    range=(200, 1000),
                    resolution=100,
                    orientation="h",
                    key="-Cell Upper Bound-",
                    enable_events=True,
                    default_value=1000,
                ),
            ],
            [
                sg.Column(
                    [
                        [sg.Button("Calculate", key="-CALCULATE-")],
                    ],
                    justification="center",
                )
            ],
            [sg.Text("Calculating ...", key="-CALC Message-", visible=False)],
            [sg.Text("", key="-Best Square Size-", visible=False)],
            [
                sg.Push(),
                sg.Text(
                    "Select custom square size",
                    key="-Custom Square Size Label-",
                    visible=False,
                ),
                sg.Slider(
                    range=(100, 1000),
                    resolution=100,
                    orientation="h",
                    key="-Custom Square Size-",
                    enable_events=True,
                    default_value=1000,
                    visible=False,
                ),
            ],
            [sg.Button("Continue Calculations", key="-CONTINUE-", visible=False)],
            [sg.Button("Proceed to Step 3", key="-PROCEED-", visible=False)],
        ]

        step2_window = sg.Window("Step 2", layout)

        while True:
            event, values = step2_window.read()

            if event == sg.WINDOW_CLOSED:
                break

            if event == "-PROCEED-":
                step2_window.close()
                break

            if event == "-CALCULATE-":
                weight_avg_combined_metric = values["-Weighted Average-"]
                failures_weight = values["-Failures Weight-"]
                cell_lower_bound = int(values["-Cell Lower Bound-"])
                cell_upper_bound = int(values["-Cell Upper Bound-"])
                total = weight_avg_combined_metric + failures_weight

                if total != 1:
                    sg.popup_error("The sum of all sliders must be 1. Please adjust the sliders.")
                else:
                    bounds = (cell_lower_bound, cell_upper_bound)
                    step2_window["-CALC Message-"].update(visible=True)
                    step2_window.refresh()

                    os.makedirs(
                        os.path.join(
                            self.projects_folder,
                            "Fishnet_Grids",
                        ),
                        exist_ok=True,
                    )
                    output_path = os.path.join(
                        self.projects_folder,
                        "Fishnet_Grids",
                        "",
                    )

                    step2_window.perform_long_operation(
                        lambda: self.step2_spatial_autocorrelation_analysis(
                            weight_avg_combined_metric, failures_weight, cell_lower_bound, cell_upper_bound, output_path
                        ),
                        "-STEP2 SPATIAL AUTOCORRELATION-",
                    )

            if event == "-STEP2 SPATIAL AUTOCORRELATION-":
                results, best_square_size = values["-STEP2 SPATIAL AUTOCORRELATION-"]

                step2_window["-CALC Message-"].update(visible=False)

                # Passing the local variables to the class variables
                # to use them in the next steps
                self.weight_avg_combined_metric = weight_avg_combined_metric
                self.weight_failures = failures_weight
                self.step2_output_path = output_path

                # Ask the user if they want to keep the best square size or input a custom one
                step2_window["-CALCULATE-"].update(visible=False)
                step2_window["-Best Square Size-"].update(f"Best square size: {best_square_size}", visible=True)
                step2_window["-Custom Square Size Label-"].update(visible=True)
                step2_window["-Custom Square Size-"].update(best_square_size, range=bounds, visible=True)
                step2_window["-CONTINUE-"].update(visible=True)

                self.select_square_size = best_square_size

            if event == "-CONTINUE-":
                self.select_square_size = values["-Custom Square Size-"]
                step2_window.perform_long_operation(
                    lambda: self.step2_local_spatial_autocorrelation(
                        weight_avg_combined_metric, failures_weight, self.select_square_size, output_path
                    ),
                    "-STEP2 LOCAL SPATIAL AUTOCORRELATION-",
                )

            if event == "-STEP2 LOCAL SPATIAL AUTOCORRELATION-":
                sorted_fishnet_df, results_pipe_clusters, fishnet_index = values[
                    "-STEP2 LOCAL SPATIAL AUTOCORRELATION-"
                ]

                self.sorted_fishnet_df = sorted_fishnet_df
                self.results_pipe_clusters = results_pipe_clusters
                self.fishnet_index = fishnet_index

                self.path_fishnet = os.path.join(
                    self.projects_folder,
                    "Fishnet_Grids",
                    f"{self.select_square_size}_fishnets_sorted.shp",
                )

                step2_window["-CONTINUE-"].update(visible=False)
                step2_window["-PROCEED-"].update(visible=True)
                step2_window.refresh()
                self.step2_completed = True

                # Update the main window to enable the next step
                self.window["-STEP1-"].update(disabled=True)
                self.window["-STEP2-"].update(disabled=True)
                self.window["-STEP3-"].update(disabled=False)
                self.window["-STEP4-"].update(
                    disabled=False
                )  # enable step 4 together with step 3 because optimization takes too long

    def step2_spatial_autocorrelation_analysis(
        self, weight_avg_combined_metric, weight_failures, cell_lower_bound, cell_upper_bound, output_path
    ):
        results, best_square_size = spatial_autocorrelation_analysis(
            pipe_shapefile_path=self.step1_result_shapefile,
            failures_shapefile_path=self.damage_shapefile,
            lower_bound_cell=cell_lower_bound,
            upper_bound_cell=cell_upper_bound,
            weight_avg_combined_metric=weight_avg_combined_metric,
            weight_failures=weight_failures,
            output_path=output_path,
        )
        return results, best_square_size

    def step2_local_spatial_autocorrelation(
        self, weight_avg_combined_metric, weight_failures, select_square_size, output_path
    ):
        sorted_fishnet_df, results_pipe_clusters, fishnet_index = local_spatial_autocorrelation(
            pipe_shapefile_path=self.step1_result_shapefile,
            failures_shapefile_path=self.damage_shapefile,
            weight_avg_combined_metric=weight_avg_combined_metric,
            weight_failures=weight_failures,
            select_square_size=select_square_size,
            output_path=output_path,
        )
        return sorted_fishnet_df, results_pipe_clusters, fishnet_index

    def step3(self):
        self.results_pipe_clusters = optimize_pipe_clusters(
            self.results_pipe_clusters, self.df_metrics, self.sorted_fishnet_df
        )

        os.makedirs(
            os.path.join(
                self.projects_folder,
                "Cell_optimization_results",
            ),
            exist_ok=True,
        )

        layout = []
        layout.append(
            [sg.Text("Insert pipe materials and their lifespan", font=("Arial", 12, "bold"), justification="center")]
        )
        for material_name in self.unique_pipe_materials_names:
            layout.append(
                [
                    sg.Push(),
                    sg.Text(f"{material_name}: ", key=f"-{material_name} Label-"),
                    sg.Input(
                        key=f"-{material_name}-",
                        default_text=str(self.pipe_materials[material_name])
                        if self.pipe_materials[material_name]
                        else "",
                    ),
                ]
            )

        layout.append(
            [
                sg.Push(),
                sg.Text("Insert lifespan of contract work:"),
                sg.Slider(
                    range=(5, 15),
                    resolution=1,
                    orientation="h",
                    key="-Lifespan Contract Work-",
                    enable_events=True,
                    default_value=10,
                ),
            ]
        )

        layout.append(
            [
                sg.Push(),
                sg.Text("Allowable time span relaxation:"),
                sg.Slider(
                    range=(2, 5),
                    resolution=1,
                    orientation="h",
                    key="-Lifespan-",
                    enable_events=True,
                    default_value=3,
                ),
            ]
        )

        layout.append([sg.Text("Select cell"), sg.Input(key="-Cell Index-")])
        layout.append(
            [sg.Button("Make calculations for the cell", key="-Calculate Cell-")],
        )

        layout.append([sg.Text("", key="-Calculation Message-")])

        step3_window = sg.Window("Step 3", layout)

        while True:
            event, values = step3_window.read()
            if event == sg.WINDOW_CLOSED:
                self.window["-STEP1-"].update(disabled=True)
                self.window["-STEP2-"].update(disabled=True)
                self.window["-STEP3-"].update(disabled=False)
                self.window["-STEP4-"].update(disabled=False)
                break

            if event == "-Calculate Cell-":
                step3_window["-Calculate Cell-"].update(disabled=True)
                step3_window["-Calculation Message-"].update("Calculating ...")

                try:
                    p_span = int(values["-Lifespan Contract Work-"])
                    a_rel = int(values["-Lifespan-"])
                    row_number_to_keep = int(values["-Cell Index-"])
                    valid_input = True
                except Exception:
                    sg.popup("Please insert all required fields and try again")
                    step3_window["-Calculation Message-"].update("")
                    valid_input = False

                if valid_input:
                    message, is_valid = check_items_in_key(
                        self.results_pipe_clusters, self.fishnet_index, row_number_to_keep
                    )

                    if not is_valid:
                        sg.popup(message)

                    else:
                        # Input is valid, we proceed with the calculations
                        os.makedirs(
                            os.path.join(
                                self.projects_folder,
                                "Cell_optimization_results",
                                f"Cell_Priority_{row_number_to_keep}",
                            ),
                            exist_ok=True,
                        )

                        # Run functions
                        pipes_gdf_cell = process_pipes_cell_data(
                            self.step1_result_shapefile,
                            self.path_fishnet,
                            self.fishnet_index,
                            row_number_to_keep,
                            self.results_pipe_clusters,
                            self.pipe_materials,
                        )

                        pipe_table_trep, LLCCn, ann_budg, xl, xu = calculate_investment_timeseries(
                            pipes_gdf_cell, p_span, 50, a_rel
                        )

                        # Run optimization
                        # number of pipes in this cell
                        number_of_pipes = pipe_table_trep.count()[0]

                        # define 3 hyperparameters for optimization
                        pop_size = int(
                            round((7.17 * number_of_pipes - 1.67), -1)
                        )  # linear equation going through (10,70) and (70,500)
                        n_gen = int(
                            round((1.33 * number_of_pipes + 6.67), -1)
                        )  # linear equation going through (70,100) and (10,20)
                        n_offsprings = int(max(round((pop_size / 5), -1), 5))

                        problem = MyProblem(pipe_table_trep, p_span, LLCCn, xl, xu)

                        algorithm = NSGA2(
                            pop_size=pop_size,
                            n_offsprings=n_offsprings,
                            sampling=IntegerRandomSampling(),
                            crossover=SBX(prob=0.9, eta=15, repair=RoundingRepair()),
                            mutation=PM(eta=20, repair=RoundingRepair()),
                            eliminate_duplicates=True,
                        )
                        sg.Print("", do_not_reroute_stdout=False)

                        print("Optimization started. This may take a while.")

                        step3_window.perform_long_operation(
                            lambda: self.step3_minimize(problem, algorithm, n_gen), "-OPTIMIZATION-"
                        )

            if event == "-OPTIMIZATION-":
                res = values["-OPTIMIZATION-"]

                print("Optimization finished. You can close this window and proceed to the next step.")
                X = res.X
                F = res.F

                # Run function for making final geodataframe
                pipes_gdf_cell_merged = manipulate_opt_results(self.edges, X, F, pipe_table_trep, pipes_gdf_cell)

                pre_path = os.path.join(
                    self.projects_folder,
                    "Cell_optimization_results",
                    f"Cell_Priority_{row_number_to_keep}",
                )
                # Save the shape file into Cell_optimization_results/Cell_Priority_#
                pipes_gdf_cell_merged.to_file(pre_path + f"/Priority_{row_number_to_keep}_cell_optimal_replacement.shp")
                step3_window["-Calculation Message-"].update(
                    f"Calculation for Cell {row_number_to_keep} is finished.\nContinue with another cell or close the window and proceed to step 4."
                )

                step3_window["-Calculate Cell-"].update(disabled=False)

    def step3_minimize(self, problem, algorithm, n_gen):
        return minimize(
            problem, algorithm, seed=1, termination=('n_gen', n_gen), save_history=True, verbose=True,
        )

    def step4(self):
        layout = [
            [sg.Text("Select Cell Priority shapefile")],
            [
                sg.Input(key="-Cell Priority-"),
                sg.FileBrowse(
                    file_types=(("Shapefiles", "*.shp"),),
                ),
            ],
            [sg.Button("Proceed with shapefile", key="-Proceed-")],
        ]

        step4_window = sg.Window("Step 4", layout)

        while True:
            event, values = step4_window.read()

            if event == sg.WINDOW_CLOSED:
                break

            if event == "-Proceed-":
                step4_window["-Proceed-"].update(visible=False)
                step4_window["Browse"].update(visible=False)

                file_path = values["-Cell Priority-"]

                if file_path and os.path.exists(file_path):
                    step4_window["-Cell Priority-"].update(disabled=True)

                    new_elements = [
                        [
                            sg.Button("Proceed with time", key="-ProceedTime-"),
                            sg.Button("Proceed with pipe IDs", key="-ProceedPipes-"),
                        ]
                    ]

                    step4_window.extend_layout(step4_window, new_elements)
                    step4_window.refresh()

            if event == "-ProceedTime-" or event == "-ProceedPipes-":
                step4_window["-ProceedTime-"].update(visible=False)
                step4_window["-ProceedPipes-"].update(visible=False)

            if event == "-ProceedTime-":
                proceedTime = True

                new_elements = [
                    [sg.Push(), sg.Text("Start Time:"), sg.Input(key="-Low Time-")],
                    [sg.Push(), sg.Text("End Time:"), sg.Input(key="-Up Time-")],
                ]

            if event == "-ProceedPipes-":
                proceedTime = False
                pipe_ids: List[int] = gpd.read_file(file_path)["ID"].to_list()

                checkboxes = [[sg.Checkbox(f"Pipe ID: {pipe_id}", key=f"Pipe {pipe_id}")] for pipe_id in pipe_ids]

                new_elements = [
                    [
                        sg.Column(
                            checkboxes,
                            scrollable=True,
                            vertical_scroll_only=True,
                            size=(200, 400),
                            justification="center",
                        )
                    ]
                ]

            if event == "-ProceedTime-" or event == "-ProceedPipes-":
                new_elements.append(
                    [sg.Push(), sg.Text("Contract Work Min Distance (m):"), sg.Input(key="-Min Distance-")]
                )
                new_elements.append(
                    [
                        sg.Push(),
                        sg.Text("Output shapefile name"),
                        sg.Input(default_text="custom_selection_replacement_v2", key="-Shape File Name-"),
                    ]
                )
                new_elements.append([sg.Column([[sg.Button("Calculate", key="-CALCULATE-")]], justification="center")])
                new_elements.append([sg.Text("File is saved successfully!", key="-Success Message-", visible=False)])
                step4_window.extend_layout(step4_window, new_elements)
                step4_window.refresh()

            if event == "-CALCULATE-":
                step4_window["-CALCULATE-"].update(disabled=True)
                step4_window["-Success Message-"].update(visible=False)
                step4_window.refresh()

                if not values["-Min Distance-"]:
                    sg.popup("Please insert a minimum distance and try again.")
                    step4_window["-CALCULATE-"].update(disabled=False)
                    continue

                min_contract_distance = float(values["-Min Distance-"])
                row_number_to_keep = file_path.split("/")[-2].split("_")[-1]

                if proceedTime:
                    if not values["-Low Time-"] or not values["-Up Time-"]:
                        sg.popup("Please insert both start and end time and try again.")
                        step4_window["-CALCULATE-"].update(disabled=False)
                        continue

                    low_time = float(values["-Low Time-"])
                    up_time = float(values["-Up Time-"])
                    filter_list = [low_time, up_time]

                else:
                    # Read the selected pipe IDs
                    selected_pipe_ids = [
                        int(key.split(" ")[-1]) for key, value in values.items() if (value and key.startswith("Pipe "))
                    ]

                    if not selected_pipe_ids:
                        sg.popup("Please select at least one pipe and try again.")
                        step4_window["-CALCULATE-"].update(disabled=False)
                        continue
                    filter_list = selected_pipe_ids

                red_subgraph, red_edges_df = create_subgraph_from_threshold(file_path, proceedTime, filter_list)
                (
                    red_edges_df,
                    results_df,
                    overall_weighted_average_cost,
                    total_length_under,
                    accept_condition,
                    perc,
                    total_length_all,
                ) = analyze_graph(red_subgraph, red_edges_df, min_contract_distance, 0.9)

                shp_name = values["-Shape File Name-"]
                shp_file_path = os.path.join(
                    self.projects_folder,
                    "Cell_optimization_results",
                    f"Cell_Priority_{row_number_to_keep}",
                    f"{shp_name}.shp",
                )
                red_edges_df.to_file(shp_file_path)

                text_filename = os.path.join(
                    self.projects_folder,
                    "Cell_optimization_results",
                    f"Cell_Priority_{row_number_to_keep}",
                    f"{shp_name}.txt",
                )
                export_df_and_sentence_to_file(
                    red_edges_df,
                    results_df,
                    total_length_under,
                    row_number_to_keep,
                    shp_name,
                    overall_weighted_average_cost,
                    accept_condition,
                    perc,
                    total_length_all,
                    min_contract_distance,
                    text_filename,
                )
                step4_window["-CALCULATE-"].update(disabled=False)
                step4_window["-Success Message-"].update(visible=True)
                step4_window.refresh()

    def create_new_project(self):
        layout = [
            [sg.Text("New Project Name:")],
            [sg.Input()],
            [sg.Text("Select network shapefile")],
            [sg.Input(), sg.FileBrowse(file_types=(("Shapefiles", "*.shp"),))],
            [sg.Text("Select damage shapefile")],
            [sg.Input(), sg.FileBrowse(file_types=(("Shapefiles", "*.shp"),))],
            [sg.Column([[sg.Button("Create Project")]], justification="center")],
        ]

        new_project_window = sg.Window("Create Project", layout, finalize=True)

        while True:
            event, values = new_project_window.read()
            if event == sg.WINDOW_CLOSED:
                break
            if event == "Create Project":
                project_name = values[0]
                self.project_name = project_name
                network_shapefile_path = values[1]
                damage_shapefile_path = values[2]

                if is_valid_project_name(project_name):
                    new_project_window.close()

                    os.makedirs(self.project_folder, exist_ok=True)

                    self.network_shapefile = copy_shapefile("network", network_shapefile_path, self.project_folder)
                    self.damage_shapefile = copy_shapefile("damage", damage_shapefile_path, self.project_folder)

                else:
                    sg.popup("Invalid project name. Please try again.")
