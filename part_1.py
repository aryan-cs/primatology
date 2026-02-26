# print("[PART 1] Hello, World!")

import csv
import os
import json
from datetime import datetime
from base_agent import BaseAgent
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

ACTION_COLOR = {
    'cooperate': 'green',
    'defect':    'red',
}

def colored_action(action: str) -> str:
    color = ACTION_COLOR.get(action, 'white')
    return f"[{color}]{action.upper()}[/{color}]"

def prisoners_dilemma(A: BaseAgent,
                      B: BaseAgent,
                      rounds: int = 10,
                      games:  int = 1,
                      history: bool = False,
                      show_rounds: bool = False):
    
    """
    Payoff matrix (row = A, col = B):
                B cooperates    B defects
    A cooperates    (3, 3)        (0, 5)
    A defects       (5, 0)        (1, 1)
    """
    
    mutual_cooperation_points = 3
    single_defection_points   = 5
    mutual_defection_points   = 1
    
    PAYOFFS = {
        ('cooperate', 'cooperate'): (mutual_cooperation_points, mutual_cooperation_points),
        ('cooperate', 'defect'):    (0, single_defection_points),
        ('defect',    'cooperate'): (single_defection_points, 0),
        ('defect',    'defect'):    (mutual_defection_points, mutual_defection_points),
    }
    
    total_scores = {A.id: 0, B.id: 0}
    all_history  = []

    def build_prompt(agent: BaseAgent, opponent: BaseAgent, round_num: int, game_history: list) -> str:
        prompt = (
            f"You are Agent {agent.id} playing the Prisoner's Dilemma against Agent {opponent.id}. "
            + (f"This is round {round_num} of {rounds}. " if show_rounds else f"This is round {round_num}. ") +
            "You must choose to either COOPERATE or DEFECT.\n\n"
            "Payoffs:\n"
            f"  - Both cooperate:             you get {mutual_cooperation_points} years of jail time, opponent gets {mutual_cooperation_points} years of jail time.\n"
            f"  - You defect, they cooperate: you get {single_defection_points} years of jail time, opponent gets 0\n"
            f"  - You cooperate, they defect: you get 0 years of jail time, opponent gets {single_defection_points} years of jail time\n"
            f"  - Both defect:                you get {mutual_defection_points} years of jail time, opponent gets {mutual_defection_points} years of jail time\n"
        )
        if history and game_history:
            prompt += "\nHistory of previous rounds:\n"
            for i, (a, b, pa, pb) in enumerate(game_history, 1):
                my_action  = a  if agent.id == A.id else b
                opp_action = b  if agent.id == A.id else a
                my_payoff  = pa if agent.id == A.id else pb
                prompt += f"  Round {i}: you played {my_action}, opponent played {opp_action}, you went to jail for {my_payoff} years.\n"
        prompt += (
            "\nThink through your decision carefully, then respond in JSON with this exact schema:\n"
            '{"reasoning": "<your step-by-step reasoning>", "action": "<COOPERATE or DEFECT>"}'
        )
        return prompt

    def parse_action(response: str) -> tuple[str, str] | None:
        try:
            data      = json.loads(response)
            action    = data["action"].strip().upper()
            reasoning = data.get("reasoning", "")
            if action not in ("COOPERATE", "DEFECT"):
                raise ValueError(f"Unexpected action value: {action}")
            return action.lower(), reasoning
        except Exception as e:
            console.print(f"  [yellow][WARN] Failed to parse response as JSON ({e}). Retrying...[/yellow]")
            return None

    def query_until_valid(agent: BaseAgent, prompt: str) -> tuple[str, str]:
        attempt = 0
        while True:
            attempt += 1
            response = agent.query(prompt, json_mode=True)
            result   = parse_action(response)
            if result is not None:
                return result
            console.print(f"  [yellow][WARN] Agent {agent.id} attempt {attempt} failed. Retrying...[/yellow]")

    console.print(Panel(
        f"[bold]Prisoner's Dilemma[/bold]\n"
        f"[cyan]{A}[/cyan] vs [magenta]{B}[/magenta]\n"
        f"Games: {games}  |  Rounds per game: {rounds}  |  History: {history}",
        box=box.DOUBLE,
    ))

    for game_num in range(1, games + 1):

        console.rule(f"[bold white]Game {game_num} / {games}[/bold white]")

        game_scores  = {A.id: 0, B.id: 0}
        game_history = []

        for round_num in range(1, rounds + 1):

            console.rule(f"[bold]Round {round_num} / {rounds}[/bold]")

            prompt_A = build_prompt(A, B, round_num, game_history)
            prompt_B = build_prompt(B, A, round_num, game_history)

            action_A, reasoning_A = query_until_valid(A, prompt_A)
            action_B, reasoning_B = query_until_valid(B, prompt_B)

            payoff_A, payoff_B = PAYOFFS[(action_A, action_B)]
            game_scores[A.id]  += payoff_A
            game_scores[B.id]  += payoff_B
            total_scores[A.id] += payoff_A
            total_scores[B.id] += payoff_B

            game_history.append((action_A, action_B, payoff_A, payoff_B))
            all_history.append((game_num, round_num, action_A, action_B, payoff_A, payoff_B))

            console.print(Panel(
                Markdown(reasoning_A),
                title=f"[cyan]Agent {A.id} reasoning[/cyan]",
                border_style="cyan",
            ))
            console.print(Panel(
                Markdown(reasoning_B),
                title=f"[magenta]Agent {B.id} reasoning[/magenta]",
                border_style="magenta",
            ))
            console.print(Panel(
                f"[cyan]A[/cyan] → {colored_action(action_A)}   "
                f"[magenta]B[/magenta] → {colored_action(action_B)}   "
                f"Payoffs: ([cyan]{payoff_A}[/cyan], [magenta]{payoff_B}[/magenta])",
                title="[bold]Decision[/bold]",
                border_style="white",
            ))

        console.rule(f"[bold]Game {game_num} Results[/bold]")
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold", expand=True)
        table.add_column("Round",                       justify="center")
        table.add_column(f"Agent {A.id} action",        justify="center")
        table.add_column(f"Agent {B.id} action",        justify="center")
        table.add_column(f"Agent {A.id} payoff",        justify="center")
        table.add_column(f"Agent {B.id} payoff",        justify="center")
        for i, (a, b, pa, pb) in enumerate(game_history, 1):
            table.add_row(str(i), colored_action(a), colored_action(b), str(pa), str(pb))
        console.print(table)

        console.print(Panel(
            f"[cyan]Agent {A.id}: {game_scores[A.id]}[/cyan]   [magenta]Agent {B.id}: {game_scores[B.id]}[/magenta]",
            title=f"[bold]Game {game_num} Scores[/bold]",
            border_style="white",
        ))

    if games > 1:
        console.rule("[bold]Overall Results[/bold]")

        game_totals = {}
        for game_num, round_num, a, b, pa, pb in all_history:
            if game_num not in game_totals:
                game_totals[game_num] = [0, 0]
            game_totals[game_num][0] += pa
            game_totals[game_num][1] += pb

        total_A    = total_scores[A.id]
        total_B    = total_scores[B.id]
        avg_A      = total_A / games
        avg_B      = total_B / games

        def classify(agent_id):
            actions    = [a if agent_id == A.id else b for (_, _, a, b, _, _) in all_history]
            coop_rate  = actions.count('cooperate') / len(actions)
            if coop_rate >= 0.6:
                return "Largely Cooperative"
            elif coop_rate <= 0.4:
                return "Largely Defective"
            else:
                return "Largely Neutral"

        overall_table = Table(box=box.ROUNDED, show_header=True, header_style="bold", expand=True)
        overall_table.add_column("Game",      justify="center")
        overall_table.add_column(f"Agent {A.id}", justify="center")
        overall_table.add_column(f"Agent {B.id}", justify="center")

        for g, (sa, sb) in game_totals.items():
            overall_table.add_row(str(g), str(sa), str(sb))

        overall_table.add_section()
        overall_table.add_section()
        overall_table.add_row("[bold]Total[/bold]",   f"[bold]{total_A}[/bold]",        f"[bold]{total_B}[/bold]")
        overall_table.add_section()
        overall_table.add_row("[bold]Average[/bold]", f"[bold]{avg_A:.1f}[/bold]",      f"[bold]{avg_B:.1f}[/bold]")
        overall_table.add_section()

        def style_color(style: str) -> str:
            if style == "Largely Cooperative": return "green"
            if style == "Largely Defective":   return "red"
            return "white"

        style_A, style_B = classify(A.id), classify(B.id)
        overall_table.add_row(
            "[bold]Style[/bold]",
            f"[bold {style_color(style_A)}]{style_A}[/bold {style_color(style_A)}]",
            f"[bold {style_color(style_B)}]{style_B}[/bold {style_color(style_B)}]",
        )
        console.print(overall_table)

    timestamp = datetime.now().strftime("%m-%d-%Y_%H:%M:%S")
    csv_dir   = os.path.join("results", "prisoners-dilemma")
    os.makedirs(csv_dir, exist_ok=True)
    csv_path  = os.path.join(csv_dir, f"{timestamp}.csv")
    running_A, running_B = 0, 0
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "game", "round",
            f"agent_{A.id}_action", f"agent_{B.id}_action",
            f"agent_{A.id}_payoff", f"agent_{B.id}_payoff",
            f"agent_{A.id}_total",  f"agent_{B.id}_total",
        ])
        for (gn, rn, a, b, pa, pb) in all_history:
            running_A += pa
            running_B += pb
            writer.writerow([gn, rn, a, b, pa, pb, running_A, running_B])

    console.print(Panel(
        f"[green]{os.path.abspath(csv_path)}[/green]",
        title="[bold]Results Saved[/bold]",
        border_style="green",
    ))

    return {
        'history':      all_history,
        'total_scores': total_scores,
        'csv':          csv_path,
    }


player_A = BaseAgent(id_='A')
player_B = BaseAgent(id_='B')
results  = prisoners_dilemma(player_A, 
                             player_B, 
                             rounds=20,         # how many rounds per game
                             games=10,          # how many games to play
                             history=True,      # should models be able to see the history of the player's decisions when making their next decision?
                             show_rounds=True)  # should models know how many rounds are in the game?