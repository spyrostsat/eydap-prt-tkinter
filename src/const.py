SRC_CRS = "EPSG:2100"
TARGET_CRS = "EPSG:4326"

WIN_WAIT_BEFORE_CLOSE = 700  # After the calculations of a popup window finish, the window will close after this time in ms

LEFT_RIGHT_FRAME_TITLE_DIV = 1.9
LEFT_RIGHT_FRAME_CONTENT_DIV = 2

IMAGES_DIV = 1.3
IMAGES_DIV_2 = 1.7

LEFT_MENU_ROW_HEIGHT = 35

RESET_MAP_PADX = 50
RESET_MAP_PADY = 10
RESET_MAP_ANCHOR = "w"
RESET_MAP_TEXT = "Reset map"

MENU_SPACES = "       "

MATERIAL_COLORS = {
	'Asbestos Cement': "#FF0000",
	'PVC': "#00FF00",
	'Steel': "#0000FF",
	'HDPE': "#FFFF00",
	'Cast iron': "#00FFFF",
}

CLOSENESS_TOOLTIP = 'Closeness centrality metric expresses the average length from a pipe to all nodes in the network. This metric practically indicates how "centrally located" the pipeline is in the network, based on distance. Closeness Centrality metric prioritises the replacement of pipelines that are important in terms of their location, such as centrally located pipelines in the network.'
BETWEENESS_TOOLTIP = 'Betweenness centrality metric expresses "how often" shortest paths connecting any two nodes in the network pass through a node. This metric practically indicates that the removal of a pipeline is very likely to lead to a longer duration of water distribution time in the network. It expresses "how important a pipeline is in the network at the sharing level". Betweenness Centrality metric prioritises the replacement of pipelines that are important in terms of water distribution, such as primary pipelines.'
BRIDGES_TOOLTIP = 'Bridges metric expresses whether the pipeline is a "bridge" of the network or not. It practically indicates that if the pipeline is removed, then parts of the network are completely cut off. Bridge metric identifies the pipelines that can lead to the interruption of water supply to consumer segments.'
COMPOSITE_TOOLTIP = 'The above selected weights of the individual topological metrics are normalized and aggregated into a "Composite Metric". The Composite metric practically takes into account all the above "policies" of prioritising pipe replacement. Equally weights across the 3 metrics are suggested.'
COMBINED_METRIC_FAILURES_TOOLTIP = 'The final index is calculated by combining the composite metric with the failure index. The weights are normalized. For example, if only the failure index should be considered with no contribution from topological metrics, the slider should be set to 1. Conversely, if only the topological metric is to be considered, the slider should be set to 0. It is recommended to assign equal weights to both the composite metric and the failures index.'
CELL_LOWER_BOUND_TOOLTIP = 'The minimum cell size of the rectangular grid that will be created for the definition of critical areas. The size of the grid cell is a parameter to be optimised.'
CELL_UPPER_BOUND_TOOLTIP = 'The maximum cell size of the rectangular grid that will be created for the definition of critical areas. The size of the grid cell is a parameter to be optimised.'
LIFESPAN_TOOLTIP = 'The lifespan of the contract in years'
RELAXATION_TOOLTIP = 'Time window around the time 𝑡∗ within which the replacement of each pipeline is allowed to take place'
CELL_INDEX_TOOLTIP = 'The cell index (i.e., priority number) that corresponds to the previously created grid cells and is visible under the “criticality map for selected cell size”'
DECISION_SUPPORT_TOOLTIP = 'Pipe replacement in selected cell based on replacement times (Proceed with time option) or based on individual pipes (Proceed with pipe IDs) for the analysis of individual contracts.'
PIPE_GROUPING_TOOLTIP = 'Selected optimised cell to visualise results (shapefile) of pipe replacement clusters.'

INIT_MENU_OPTIONS = [
	{
		"name": "Setting the topology",
		"step": 0,
		"leaf": False,
		"active": False
	},
 	{
		"name": "Pipe network",
		"step": 0,
		"leaf": True,
		"active": True
	},
  	{
		"name": "Failures",
		"step": 0,
		"leaf": True,
		"active": True
	},
   	{
		"name": "Risk assessment (topological metrics)",
		"step": 1,
		"leaf": False,
		"active": True
	},
    {
		"name": "Closeness metric",
		"step": 1,
		"leaf": True,
		"active": False
	},
    {
		"name": "Betweeness metric",
		"step": 1,
		"leaf": True,
		"active": False
	},
    {
		"name": "Bridges metric",
		"step": 1,
		"leaf": True,
		"active": False
	},
    {
		"name": "Composite metric",
		"step": 1,
		"leaf": True,
		"active": False
	},
    {
		"name": "Risk assessment (Combined metrics/failures)",
		"step": 2,
		"leaf": False,
		"active": False
	},
    {
		"name": "Criticality maps per cell size",
		"step": 2,
		"leaf": True,
		"active": False
	},
    {
		"name": "LISA results",
		"step": 2,
		"leaf": True,
		"active": False
	},
    {
		"name": "Risk assessment (Optimal / Selected cell size)",
		"step": 3,
		"leaf": False,
		"active": False
	},
    {
		"name": "Criticality map for selected cell size",
		"step": 3,
		"leaf": True,
		"active": False
	},
    {
		"name": "LCC optimization",
		"step": 4,
		"leaf": False,
		"active": False
	},
    {
		"name": "Optimized cells",
		"step": 4,
		"leaf": True,
		"active": False
	},
    {
		"name": "Decision support tool for pipe replacement",
		"step": 5,
		"leaf": False,
		"active": False
	},
    {
		"name": "Pipe grouping",
		"step": 5,
		"leaf": True,
		"active": False
	},
]
