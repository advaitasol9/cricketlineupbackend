from firebase_functions import https_fn
from firebase_admin import initialize_app
from pulp import LpProblem, LpMaximize, LpVariable, lpSum
import json

# Initialize Firebase app
initialize_app()

@https_fn.on_request()
def on_request_example(req: https_fn.Request) -> https_fn.Response:
    return https_fn.Response("Hello world!")

@https_fn.on_request()
def generate_lineup(req: https_fn.Request) -> https_fn.Response:
    # Set CORS headers for the preflight request
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', status=204, headers=headers)

    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*'
    }
    
    if req.method != 'POST':
        return https_fn.Response("This endpoint only supports POST requests.", status=405, headers=headers)

    try:
        data = req.get_json()
        players = data.get('players', [])
        lockedPlayers = set(data.get('lockedPlayers', []))  # Now expects player IDs
        favoritePlayers = set(data.get('favoritePlayers', []))  # Now expects player IDs

        if not players or type(players) is not list:
            return https_fn.Response("Invalid players data provided.", status=400, headers=headers)
    except Exception as e:
        return https_fn.Response(f"Error parsing request body: {str(e)}", status=400, headers=headers)

    prob = LpProblem("CricketLineupOptimizer", LpMaximize)
    player_vars = [LpVariable(f"player_{i}", cat='Binary') for i, _ in enumerate(players)]
    player_index = {i: p for i, p in enumerate(players)}

    # Adjust power rate for favorite players based on player ID
    for i, p in player_index.items():
        if p["player_id"] in favoritePlayers:
            player_index[i]["power_rate"] *= 1.2  # Increase by 20%

    total_points = lpSum(player_vars[i] * player_index[i]["power_rate"] for i in range(len(players)))
    prob += total_points

    salary_cap = 100
    prob += lpSum(player_vars[i] * player_index[i]["salary"] for i in range(len(players))) <= salary_cap

    # Constraints for teams, positions, and locked players
    teams = set(p["team_abbr"] for p in players)
    for team in teams:
        prob += lpSum(player_vars[i] for i in range(len(players)) if player_index[i]["team_abbr"] == team) <= 7

    prob += lpSum(player_vars[i] for i in range(len(players)) if player_index[i]["position"] == "BAT") >= 3
    prob += lpSum(player_vars[i] for i in range(len(players)) if player_index[i]["position"] == "BOW") >= 3
    prob += lpSum(player_vars[i] for i in range(len(players)) if player_index[i]["position"] == "WK") >= 1
    prob += lpSum(player_vars[i] for i in range(len(players)) if player_index[i]["position"] == "AR") >= 1

    # Ensure locked players are always included based on player ID
    for i, p in player_index.items():
        if p["player_id"] in lockedPlayers:
            prob += player_vars[i] == 1  # Locked player must be in the lineup

    prob.solve()

    # Filter selected players based on their variables
    selected_players_indices = [i for i in range(len(player_vars)) if player_vars[i].varValue > 0]
    selected_players = [player_index[i] for i in selected_players_indices]

    # Convert the list of player objects to a JSON string for the response
    return https_fn.Response(json.dumps(selected_players), mimetype='application/json', headers=headers)

@https_fn.on_request()
def generate_lineups(request: https_fn.Request) -> https_fn.Response:
    # Handle preflight request for CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', status=204, headers=headers)

    # Set CORS headers for the actual request
    headers = {'Access-Control-Allow-Origin': '*'}

    # Ensure only POST requests are accepted
    if request.method != 'POST':
        return https_fn.Response("This endpoint only supports POST requests.", status=405, headers=headers)

    try:
        data = request.get_json()
        players = data.get('players', [])
        total_teams = int(data.get('total_teams', 1))
        locked_players = set(data.get('locked_players', []))
        favorite_players = set(data.get('favorite_players', []))
        total_batsman = int(data.get('total_batsman', 1))
        total_bowler = int(data.get('total_bowler', 1))
        total_alrounder = int(data.get('total_alrounder', 1))
        total_wk = int(data.get('total_wk', 1))

        # Validate the input data
        if not players or type(players) is not list or total_teams < 1:
            return https_fn.Response("Invalid data provided.", status=400, headers=headers)
    except Exception as e:
        return https_fn.Response(f"Error parsing request body: {str(e)}", status=400, headers=headers)

    all_teams = []
    previous_teams = []

    for team_no in range(total_teams):
        # Initialize optimization problem for each team
        prob = LpProblem(f"CricketLineupOptimizer_{team_no}", LpMaximize)
        player_vars = [LpVariable(f"player_{i}_{team_no}", cat='Binary') for i, _ in enumerate(players)]
        player_index = {i: p for i, p in enumerate(players)}

        # Adjust power rate for favorite players by increasing their power rate
        for i, p in player_index.items():
            if p["player_id"] in favorite_players:
                player_index[i]["power_rate"] *= 1.2

        # Objective function: Maximize total power rate
        prob += lpSum(player_vars[i] * player_index[i]["power_rate"] for i in range(len(players)))

        # Salary cap constraint
        prob += lpSum(player_vars[i] * player_index[i]["salary"] for i in range(len(players))) <= 100

        # Team composition constraints for roles
        prob += lpSum(player_vars[i] for i in range(len(players)) if player_index[i]["position"] == "BAT") >= total_batsman
        prob += lpSum(player_vars[i] for i in range(len(players)) if player_index[i]["position"] == "BOW") >= total_bowler
        prob += lpSum(player_vars[i] for i in range(len(players)) if player_index[i]["position"] == "WK") >= total_wk
        prob += lpSum(player_vars[i] for i in range(len(players)) if player_index[i]["position"] == "AR") >= total_alrounder

        # Constraint for exactly 11 players in a team
        prob += lpSum(player_vars) == 11

        # Locked players must always be selected
        for i, p in player_index.items():
            if p["player_id"] in locked_players:
                prob += player_vars[i] == 1

        # Ensure team diversity: each team must differ from any previous team by at least 25%
        if team_no > 0:
            for prev_team in previous_teams:
                prob += lpSum(player_vars[i] for i in prev_team) <= (len(prev_team) * 0.75)

        prob.solve()

        selected_players_indices = [i for i, var in enumerate(player_vars) if var.varValue > 0.5]
        selected_players = [player_index[i] for i in selected_players_indices]

        all_teams.append(selected_players)
        previous_teams.append(set(selected_players_indices))

    # Return the generated lineups in JSON format
    return https_fn.Response(json.dumps(all_teams), mimetype='application/json', headers=headers)