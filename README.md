Cricket Lineup Optimizer API
This repository provides an API to generate optimized cricket lineups based on player data and team constraints using Linear Programming.

Overview
Function: generate_lineups
Request Method: POST
Content-Type: JSON

Request Parameters
players: List of player objects (each with player_id, power_rate, salary, position).
total_teams: Number of teams to generate.
locked_players: Player IDs to be included in the lineup.
favorite_players: Player IDs whose power rates are boosted.
total_batsman, total_bowler, total_alrounder, total_wk: Minimum counts for each role.

Features
CORS Support: Handles preflight requests and allows cross-origin requests.
Optimization: Maximizes total power rate while adhering to constraints like salary cap and team composition.
Constraints: Ensures team uniqueness and includes locked/favorite players as specified.

Error Handling
405: Non-POST requests.
400: Invalid or improperly formatted data.
Deploy the API using a suitable platform that supports https_fn and required libraries.
