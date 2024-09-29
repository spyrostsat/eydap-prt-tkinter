SRC_CRS = "EPSG:2100"
TARGET_CRS = "EPSG:4326"

MENU_SPACES = "       "

MATERIAL_COLORS = {
	'Asbestos Cement': "#FF0000",
	'PVC': "#00FF00",
	'Steel': "#0000FF",
	'HDPE': "#FFFF00",
	'Cast iron': "#00FFFF",
}

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
		"name": "Damages",
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
		"name": "Betweeness metric",
		"step": 1,
		"leaf": True,
		"active": False
	},
    {
		"name": "Closeness metric",
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
		"name": "Risk assessment (Combined metrics/damages)",
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
