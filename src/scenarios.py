#-------------------------------------------------------------------------------
# Name:        scenarios.py
# Purpose:     Scenario management of the Pipe Replacement Tool
#
# Author:      GK
#
# Created:     25/05/2024
# Copyright:   (c) NTUA 2024
# Licence:     All rights reserved
#-------------------------------------------------------------------------------
import sqlite3
import shutil
import os
from datetime import datetime
import PySimpleGUI as sg
from src.utils import copy_shapefile
from src import globals


scenarios_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scenarios")

SCENARIO_STATUS = {
    1: "Initialised",
    2: "Analysed",
    3: "Prioritised",
    4: "Optimised",
    5: "Completed", # Organised
}

class Scenario:
    def __init__(self, short_name, description, network_file, damage_file, active=0, status=1, timestamp=None, scenario_id=None):
        self.scenario_id = scenario_id
        self.short_name = short_name
        self.description = description
        self.network_file = network_file
        self.damage_file = damage_file
        self.active = active
        self.status = status
        self.timestamp = timestamp if timestamp else datetime.now().strftime('%Y-%m-%d %H:%M:%S')





    @staticmethod
    def create(prt):
        """ Display the new scenario form, validate the provided input data, save
            the new scenario with Scenario.save() and activate the new scenario."""

        layout = [
            [sg.Text("Scenario name")],
            [sg.Input(key='-NAME-')],
            [sg.Text("Scenario description")],
            [sg.Multiline(key='-DESCRIPTION-', size=(50, 5))],
            [sg.Text("Network shapefile")],
            [sg.Input(key='-NETWORK-', enable_events=True), sg.FileBrowse(file_types=(("Shapefiles", "*.shp"),))],
            [sg.Text("Damage shapefile")],
            [sg.Input(key='-DAMAGE-', enable_events=True), sg.FileBrowse(file_types=(("Shapefiles", "*.shp"),))],
            [sg.Column([[sg.Button("Create Scenario"), sg.Button("Cancel")]], justification="center")],
        ]

        new_scenario_window = sg.Window("Create Scenario", layout, finalize=True, modal=True)

        while True:
            event, values = new_scenario_window.read()

            if event in (sg.WINDOW_CLOSED, 'Cancel'):
                break
            elif event == 'Create Scenario':
                # Validate the input data
                name = values['-NAME-'].strip()
                description = values['-DESCRIPTION-'].strip()
                network_file = values['-NETWORK-'].strip()
                damage_file = values['-DAMAGE-'].strip()

                if not name:
                    sg.popup('Error', 'Scenario name is required.')
                elif not network_file:
                    sg.popup('Error', 'Network shapefile is required.')
                elif not damage_file:
                    sg.popup('Error', 'Damage shapefile is required.')
                else:
                    # Save the new scenario
                    new_scenario = Scenario(name, description, network_file, damage_file, 1)
                    new_scenario.save()

                    # Activate the new scenario
                    Scenario.set_active(new_scenario.scenario_id)

                    break

        new_scenario_window.close()



    def delete(self):
        """ Delete the current scenario from the database and its associated directory.
            If the scenario to be deleted is active, another scenario is set as active.
        """

        if self.scenario_id is not None:
            conn = Scenario.get_db_connection()
            cursor = conn.cursor()

            # Check if the scenario to be deleted is active
            cursor.execute('SELECT active FROM scenarios WHERE ID = ?', (self.scenario_id,))
            is_active = cursor.fetchone()[0] == 1

            # Delete the scenario
            delete_query = 'DELETE FROM scenarios WHERE ID = ?'
            cursor.execute(delete_query, (self.scenario_id,))

            conn.commit()

            if is_active:
                # Set another scenario as active if the deleted one was active
                cursor.execute('SELECT ID FROM scenarios ORDER BY timestamp DESC LIMIT 1')
                new_active_id = cursor.fetchone()
                if new_active_id:
                    Scenario.set_active(new_active_id[0])
            conn.close()

            # Delete the scenario directory
            scenario_directory = os.path.join(scenarios_directory, str(self.scenario_id))
            if os.path.exists(scenario_directory):
                shutil.rmtree(scenario_directory)


    @staticmethod
    def get_active():
        """ Retrieve the active scenario from the database.
            Returns an instance of Scenario if an active record is found, otherwise None.
        """
        conn = Scenario.get_db_connection()
        cursor = conn.cursor()
        select_query = 'SELECT * FROM scenarios WHERE active = 1'
        cursor.execute(select_query)
        record = cursor.fetchone()
        conn.close()
        if record:
            return Scenario(
                scenario_id=record[0],        # ID
                short_name=record[1],         # short_name
                description=record[2],        # description
                network_file=record[3],       # network_file
                damage_file=record[4],        # damage_file
                active=record[5],             # active
                status=record[6],             # status
                timestamp=record[7]           # timestamp
            )
        return None


    @staticmethod
    def get_all():
        """ Retrieve all scenarios from the database.
            Returns a list of Scenario instances.
        """
        conn = Scenario.get_db_connection()
        cursor = conn.cursor()
        select_query = 'SELECT * FROM scenarios'
        cursor.execute(select_query)
        records = cursor.fetchall()
        conn.close()
        return [
            Scenario(
                scenario_id=record[0],        # ID
                short_name=record[1],         # short_name
                description=record[2],        # description
                network_file=record[3],       # network_file
                damage_file=record[4],        # damage_file
                active=record[5],             # active
                status=record[6],             # status
                timestamp=record[7]           # timestamp
            ) for record in records
        ]


    @staticmethod
    def get_by_id(scenario_id):
        """ Retrieve a scenario by its ID from the database.
            Returns an instance of Scenario if a matching record is found, otherwise None.
        """
        conn = Scenario.get_db_connection()
        cursor = conn.cursor()
        select_query = 'SELECT * FROM scenarios WHERE ID = ?'
        cursor.execute(select_query, (scenario_id,))
        record = cursor.fetchone()
        conn.close()
        if record:
            return Scenario(
                scenario_id=record[0],        # ID
                short_name=record[1],         # short_name
                description=record[2],        # description
                network_file=record[3],       # network_file
                damage_file=record[4],        # damage_file
                active=record[5],             # active
                status=record[6],             # status
                timestamp=record[7]           # timestamp
            )
        return None


    @staticmethod
    def get_db_connection():

        # Ensure the scenarios directory exists
        if not os.path.exists(scenarios_directory):
            os.makedirs(scenarios_directory)

        # Construct the path to the SQLite database file
        database_path = os.path.join(scenarios_directory, 'prt.db')

        # Create a new SQLite database (or connect to an existing one)
        return sqlite3.connect(database_path)



    @staticmethod
    def list():
        """
        Display a list of scenarios in a table, allowing the user to sort, view descriptions,
        and select a scenario. If no scenarios are available, prompt the user to create one.

        Return the ID of the selected scenario, or None if no scenario is selected.
        """
        scenarios = Scenario.get_all()
        if not scenarios:
            sg.popup('No scenarios available', 'There are no scenarios yet. Please create one first.')
            return None

        data = [[sc.scenario_id, sc.short_name, sc.description, sc.active, SCENARIO_STATUS[sc.status], sc.timestamp] for sc in scenarios]
        headings = ['ID', 'Title', 'Active', 'Status', 'Timestamp']  # Omitted 'Description'

        # Remove the 'Description' column from the data for the table
        table_data = [[row[0], row[1], row[3], row[4], row[5]] for row in data]

        # Track sort direction
        sort_direction = [False] * len(headings)

        # Sort by active scenario first and then by timestamp in descending order
        table_data.sort(key=lambda x: (x[2] == 1, x[4]), reverse=True)

        layout = [
            [sg.Text('Sort by:'), *[sg.Button(heading, key=f'-HEADING-{i}-') for i, heading in enumerate(headings)]],
            [sg.Table(values=table_data, headings=headings, display_row_numbers=False, auto_size_columns=True,
                      num_rows=min(25, len(table_data)), enable_events=True, key='-TABLE-', justification='center', select_mode=sg.TABLE_SELECT_MODE_BROWSE),
             sg.Multiline(size=(40, 15), key='-DESCRIPTION-', disabled=True, autoscroll=True)],
            [sg.Button('Open'), sg.Button('Close')]
        ]

        window = sg.Window('Scenarios Table', layout, finalize=True, modal=True)

        # Select the first row by default and update the description
        window['-TABLE-'].update(select_rows=[0])
        if table_data:
            description = data[[row[0] for row in data].index(table_data[0][0])][2]
            window['-DESCRIPTION-'].update(description)

        selected_id = None

        while True:
            event, values = window.read()
            if event in (sg.WINDOW_CLOSED, 'Close'):
                break
            elif event == 'Open':
                selected_rows = values['-TABLE-']
                if selected_rows:
                    selected_id = table_data[selected_rows[0]][0]
                    Scenario.set_active(selected_id)
                    break
                else:
                    sg.popup('Select the scenario to open by clicking on a row.')
            elif event == '-TABLE-':
                selected_rows = values['-TABLE-']
                if selected_rows:
                    selected_row_index = selected_rows[0]
                    original_index = data.index([row for row in data if row[0] == table_data[selected_row_index][0]][0])
                    description = data[original_index][2]  # Get the description from the original data
                    window['-DESCRIPTION-'].update(description)
            elif event.startswith('-HEADING-'):
                col_num = int(event.split('-')[2])
                sort_direction[col_num] = not sort_direction[col_num]
                table_data = sorted(table_data, key=lambda x: x[col_num], reverse=sort_direction[col_num])
                window['-TABLE-'].update(values=table_data)
                # Re-select the first row after sorting
                window['-TABLE-'].update(select_rows=[0])
                if table_data:
                    description = data[[row[0] for row in data].index(table_data[0][0])][2]
                    window['-DESCRIPTION-'].update(description)

        window.close()

        return selected_id



    def save(self):
        """
        Save the current scenario to the database. If the scenario is new, it will be inserted
        as a new record. If the scenario already exists, the existing record will be updated.

        If this is the only scenario in the database, it will be set as the active scenario.

        Additionally, this method creates a subfolder named after the scenario ID. If a folder
        with the same name already exists, it will be deleted and recreated.

        Returns:
            None
        """
        if self.active not in [0, 1]:
            raise ValueError("The 'active' attribute must be either 0 or 1.")
        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Check if this is the only scenario in the database
        cursor.execute('SELECT COUNT(*) FROM scenarios')
        count = cursor.fetchone()[0]

        if self.scenario_id is None:
            # Insert a new record
            insert_query = '''
            INSERT INTO scenarios (short_name, description, network_file, damage_file, active, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            '''
            cursor.execute(insert_query, (self.short_name, self.description, self.network_file, self.damage_file, self.active, self.status, self.timestamp))
            self.scenario_id = cursor.lastrowid
        else:
            # Update an existing record
            update_query = '''
            UPDATE scenarios
            SET short_name = ?, description = ?, network_file = ?, damage_file = ?, active = ?, status = ?, timestamp = ?
            WHERE ID = ?
            '''
            cursor.execute(update_query, (self.short_name, self.description, self.network_file, self.damage_file, self.active, self.status, self.timestamp, self.scenario_id))

        conn.commit()
        conn.close()

        if count == 0:
            # Set this scenario as active if it's the only one
            Scenario.set_active(self.scenario_id)

        # Create a subfolder with the scenario ID (delete if exists, then recreate)
        scenario_directory = os.path.join(scenarios_directory, str(self.scenario_id))
        if os.path.exists(scenario_directory):
            shutil.rmtree(scenario_directory)
        os.makedirs(scenario_directory)

        # Save the shapefiles under the newly created directory
        if self.network_file:
            self.network_file = copy_shapefile('network', self.network_file, scenario_directory)
        if self.damage_file:
            self.damage_file = copy_shapefile('damage', self.damage_file, scenario_directory)



    def save_as(self, new_short_name=None, new_description=None):
        """
            This function allows the user to save the current scenario as a new scenario with a different name and description.

            Args:
                new_short_name (str, optional): The new short name for the scenario. Defaults to None.
                new_description (str, optional): The new description for the scenario. Defaults to None.

            Returns:
                Scenario object: The newly created scenario object, or None if the user cancels the operation.
        """
        layout = [
            [sg.Text("New Scenario Name")],
            [sg.Input(key='-NEW_NAME-', default_text='')],
            [sg.Text("New Scenario Description")],
            [sg.Multiline(key='-NEW_DESCRIPTION-', default_text='', size=(50, 5))],
            [sg.Column([[sg.Button("Save Scenario"), sg.Button("Cancel")]], justification="center")],
        ]

        window = sg.Window("Save Scenario As", layout, modal=True)

        new_scenario = None

        while True:
            event, values = window.read()
            if event in (sg.WIN_CLOSED, "Cancel"):
                break
            elif event == "Save Scenario":
                new_short_name = values['-NEW_NAME-']
                new_description = values['-NEW_DESCRIPTION-'].strip()
                if not new_short_name:
                    sg.popup("Scenario name is required.", title="Input Error")
                else:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    new_scenario = Scenario(new_short_name, new_description, self.network_file, self.damage_file, self.active, self.status, timestamp)

                    conn = Scenario.get_db_connection()
                    cursor = conn.cursor()

                    # Insert a new record
                    insert_query = '''
                    INSERT INTO scenarios (short_name, description, network_file, damage_file, active, status, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    '''
                    cursor.execute(insert_query, (new_scenario.short_name, new_scenario.description, new_scenario.network_file, new_scenario.damage_file, new_scenario.active, new_scenario.status, new_scenario.timestamp))
                    new_scenario.scenario_id = cursor.lastrowid

                    # Check if this is the only scenario in the database
                    cursor.execute('SELECT COUNT(*) FROM scenarios')
                    count = cursor.fetchone()[0]

                    if count == 1:
                        # Set this scenario as active if it's the only one
                        Scenario.set_active(new_scenario.scenario_id)

                    # Create a subfolder with the new scenario ID (delete if exists, then recreate)
                    old_scenario_directory = os.path.join(scenarios_directory, str(self.scenario_id))
                    new_scenario_directory = os.path.join(scenarios_directory, str(new_scenario.scenario_id))
                    if os.path.exists(new_scenario_directory):
                        shutil.rmtree(new_scenario_directory)
                    os.makedirs(new_scenario_directory)

                    # Copy all content from the old scenario directory to the new one
                    if os.path.exists(old_scenario_directory):
                        for item in os.listdir(old_scenario_directory):
                            s = os.path.join(old_scenario_directory, item)
                            d = os.path.join(new_scenario_directory, item)
                            if os.path.isdir(s):
                                shutil.copytree(s, d, False, None)
                            else:
                                shutil.copy2(s, d)

                    conn.commit()
                    conn.close()

                    Scenario.set_active(new_scenario.scenario_id)

                    break

        window.close()
        return new_scenario



    @staticmethod
    def set_active(scenario_id):
        """ Set the specified scenario as active and deactivate all other scenarios.

            Arguments:
            scenario _id (int): The ID of the scenario to be set as active.

            Returns: None
        """
        if not scenario_id:
            return None

        conn = Scenario.get_db_connection()
        cursor = conn.cursor()

        # Set the specified scenario as active
        cursor.execute('UPDATE scenarios SET active = 1 WHERE ID = ?', (scenario_id,))

        # Set all other scenarios to inactive
        cursor.execute('UPDATE scenarios SET active = 0 WHERE ID != ?', (scenario_id,))

        conn.commit()
        conn.close()

        scen = Scenario.get_by_id(scenario_id)

        globals.prt.projects_folder = os.path.join(scenarios_directory, str(scenario_id))

        globals.prt.const_pipe_materials = {"Asbestos Cement": 50, "Steel": 40, "PVC": 30, "HDPE": 12, "Cast iron": 40}

        globals.prt.step1_completed = False
        globals.prt.step2_completed = False

        globals.prt.project_name = scen.short_name
        globals.prt.network_shapefile = os.path.join(scenarios_directory, str(scenario_id), "network", scen.network_file)
        globals.prt.damage_shapefile = os.path.join(scenarios_directory, str(scenario_id), "network", scen.damage_file)
        globals.prt.df_metrics = None
        globals.prt.edges = None
        globals.prt.unique_pipe_materials_names = None
        globals.prt.pipe_materials = {}
        globals.prt.path_fishnet = None
        globals.prt.sorted_fishnet_df = None
        globals.prt.results_pipe_clusters = None
        globals.prt.fishnet_index = None
        globals.prt.select_square_size = None
        globals.prt.weight_avg_combined_metric = None
        globals.prt.weight_failures = None

        globals.prt.step1_result_shapefile = None
        globals.prt.step2_output_path = None



# ##############################################################################


# ############# Create the database ############################################
conn = Scenario.get_db_connection()
cursor = conn.cursor()

# Define the schema for the scenarios table
create_table_query = '''
CREATE TABLE IF NOT EXISTS scenarios (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    short_name TEXT NOT NULL,
    description TEXT,
    network_file TEXT NOT NULL,
    damage_file TEXT NOT NULL,
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    status INTEGER NOT NULL CHECK (status IN (1, 2, 3, 4, 5)),
    timestamp TEXT NOT NULL
)
'''

# Execute the query to create the table (if it does not exist)
cursor.execute(create_table_query)


# ##############################################################################

# Example call to open the new scenario form
##Scenario.create()

### Call the function to display the scenarios table
##selected_scenario_id = list_scenarios()
##print(f'Selected Scenario ID: {selected_scenario_id}')

# Insert a sample record for the baseline scenario
##Scenario('Baseline', 'This is the baseline scenario.', 1).save()

# ############# Test scenario DB operations ####################################
# Create a new scenario
##new_scenario = Scenario('What-If Scenario', 'This is a what-if scenario.', 1, 'In Progress')
##new_scenario.save()
##print(f'Scenario created with ID: {new_scenario.scenario_id}')
##
### Retrieve a scenario by ID
##retrieved_scenario = Scenario.get_by_id(new_scenario.scenario_id)
##print(f'Retrieved Scenario: {retrieved_scenario.short_name}, Active: {retrieved_scenario.active}')
##
### Update a scenario
##retrieved_scenario.description = 'Updated description.'
##retrieved_scenario.save()
##print('Scenario updated.')
##
### Retrieve all scenarios
##all_scenarios = Scenario.get_all()
##print(f'All Scenarios: {[scenario.short_name for scenario in all_scenarios]}')
##
### Delete a scenario
##retrieved_scenario.delete()
##print('Scenario deleted.')
##
##selected_scenario = Scenario.get_active()
##if selected_scenario:
##    print(f'Selected Scenario: {selected_scenario.short_name}, Active: {selected_scenario.active}')
##else:
##    print('No active scenario found.')
# ##############################################################################