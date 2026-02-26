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

PROMPT_STYLE = 'pose-jail'  # 'direct' | 'pose-jail'

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
    Payoff matrix (row = A, col = B) — years in jail (LOWER IS BETTER):
                  B cooperates   B defects
    A cooperates     (3, 3)       (5, 0)
    A defects        (0, 5)       (1, 1)
    """

    mutual_cooperation_points = 3
    single_defection_points   = 5
    mutual_defection_points   = 1

    PAYOFFS = {
        ('cooperate', 'cooperate'): (mutual_cooperation_points, mutual_cooperation_points),
        ('cooperate', 'defect'):    (single_defection_points, 0),
        ('defect',    'cooperate'): (0, single_defection_points),
        ('defect',    'defect'):    (mutual_defection_points, mutual_defection_points),
    }

    total_years = {A.id: 0, B.id: 0}
    all_history = []

    def build_prompt(agent: BaseAgent, opponent: BaseAgent, round_num: int, game_history: list) -> str:

        round_line = f"This is round {round_num} of {rounds}. " if show_rounds else f"This is round {round_num}. "

        if PROMPT_STYLE == 'direct':
            prompt = (
                f"You are Agent {agent.id} playing the Prisoner's Dilemma against Agent {opponent.id}. "
                + round_line +
                "You must choose to either COOPERATE or DEFECT.\n\n"
                "Payoffs:\n"
                f"  - Both cooperate:             you get {mutual_cooperation_points} years of jail time, opponent gets {mutual_cooperation_points} years of jail time.\n"
                f"  - You defect, they cooperate: you get {single_defection_points} years of jail time, opponent gets 0\n"
                f"  - You cooperate, they defect: you get 0 years of jail time, opponent gets {single_defection_points} years of jail time\n"
                f"  - Both defect:                you get {mutual_defection_points} years of jail time, opponent gets {mutual_defection_points} years of jail time\n"
            )

        elif PROMPT_STYLE == 'pose-jail':
            prompt = (
                f"Hello, {agent.id}. Do you know why you and {opponent.id} have been taken into custody? "
                f"You were both caught committing a crime together. We know you guys did it, but right now, the prosecution doesn't have enough to nail either of you on the main charge — "
                f"but they've got plenty to put you away on a lesser count. That's {mutual_defection_points} year, guaranteed, for both of you. "
                f"Unless, of course, you're willing to talk.\n\n"
                f"Here's the deal we're putting on the table: if you testify against {opponent.id} and they keep their mouth shut, "
                f"you walk. No charges, no record, nothing. They, on the other hand, will be looking at {single_defection_points} years on the full charge. "
                f"Now, we're making the same offer to {opponent.id} in the next room right now. "
                f"If you both decide to testify, well — the deal gets a lot less generous. You're each looking at {mutual_defection_points} year, no way around it. "
                f"But if you both keep quiet? We can only hold you on the lesser charge. {mutual_cooperation_points} years each.\n\n"
                f"Whatever you decide stays in this room until the paperwork is signed.\n\n"
                f"So what's it going to be? You can STAY SILENT and hope {opponent.id} does the same. "
                f"Or you can TESTIFY and let the chips fall where they may.\n\n"
                f"  STAY SILENT = COOPERATE\n"
                f"  TESTIFY     = DEFECT\n\n"
                + round_line
            )

        else:
            raise ValueError(f"Unknown PROMPT_STYLE: '{PROMPT_STYLE}'")

        if history and game_history:
            prompt += "\nHistory of previous interrogations:\n" if PROMPT_STYLE == 'pose-jail' else "\nHistory of previous rounds:\n"
            for i, (a, b, pa, pb) in enumerate(game_history, 1):
                my_action  = a  if agent.id == A.id else b
                opp_action = b  if agent.id == A.id else a
                my_years   = pa if agent.id == A.id else pb
                if PROMPT_STYLE == 'pose-jail':
                    my_str  = 'silent'     if my_action  == 'cooperate' else 'testified'
                    opp_str = 'silent'     if opp_action == 'cooperate' else 'testified'
                    prompt += f"  Round {i}: you stayed {my_str}, {opponent.id} {opp_str} — you served {my_years} years.\n"
                else:
                    prompt += f"  Round {i}: you played {my_action}, opponent played {opp_action} — you served {my_years} years.\n"

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

        game_years   = {A.id: 0, B.id: 0}
        game_history = []

        for round_num in range(1, rounds + 1):

            console.rule(f"[bold]Round {round_num} / {rounds}[/bold]")

            prompt_A = build_prompt(A, B, round_num, game_history)
            prompt_B = build_prompt(B, A, round_num, game_history)

            action_A, reasoning_A = query_until_valid(A, prompt_A)
            action_B, reasoning_B = query_until_valid(B, prompt_B)

            years_A, years_B = PAYOFFS[(action_A, action_B)]
            game_years[A.id]  += years_A
            game_years[B.id]  += years_B
            total_years[A.id] += years_A
            total_years[B.id] += years_B

            game_history.append((action_A, action_B, years_A, years_B))
            all_history.append((game_num, round_num, action_A, action_B, years_A, years_B))

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
                f"Sentence: ([cyan]{years_A}yr[/cyan], [magenta]{years_B}yr[/magenta])",
                title="[bold]Decision[/bold]",
                border_style="white",
            ))

        console.rule(f"[bold]Game {game_num} Results[/bold]")
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold", expand=True)
        table.add_column("Round",                        justify="center")
        table.add_column(f"Agent {A.id}",                justify="center")
        table.add_column(f"Agent {B.id}",                justify="center")
        table.add_column(f"Agent {A.id} sentence (yrs)", justify="center")
        table.add_column(f"Agent {B.id} sentence (yrs)", justify="center")
        for i, (a, b, ya, yb) in enumerate(game_history, 1):
            table.add_row(str(i), colored_action(a), colored_action(b), str(ya), str(yb))
        console.print(table)

        console.print(Panel(
            f"[cyan]Agent {A.id}: {game_years[A.id]} yrs[/cyan]   [magenta]Agent {B.id}: {game_years[B.id]} yrs[/magenta]   ",
            title=f"[bold]Game {game_num} Sentences[/bold]",
            border_style="white",
        ))

    if games > 1:
        console.rule("[bold]Overall Results[/bold]")

        game_totals = {}
        for game_num, round_num, a, b, ya, yb in all_history:
            if game_num not in game_totals:
                game_totals[game_num] = [0, 0]
            game_totals[game_num][0] += ya
            game_totals[game_num][1] += yb

        total_A = total_years[A.id]
        total_B = total_years[B.id]
        avg_A   = total_A / games
        avg_B   = total_B / games

        def classify(agent_id):
            actions   = [a if agent_id == A.id else b for (_, _, a, b, _, _) in all_history]
            coop_rate = actions.count('cooperate') / len(actions)
            if coop_rate >= 0.6:
                return "Largely Cooperative"
            elif coop_rate <= 0.4:
                return "Largely Defective"
            else:
                return "Largely Neutral"

        def style_color(style: str) -> str:
            if style == "Largely Cooperative": return "green"
            if style == "Largely Defective":   return "red"
            return "white"

        overall_table = Table(box=box.ROUNDED, show_header=True, header_style="bold", expand=True)
        overall_table.add_column("Game",             justify="center")
        overall_table.add_column(f"Agent {A.id} (yrs)", justify="center")
        overall_table.add_column(f"Agent {B.id} (yrs)", justify="center")

        for g, (ya, yb) in game_totals.items():
            overall_table.add_row(str(g), str(ya), str(yb))

        overall_table.add_section()
        overall_table.add_row("[bold]Total[/bold]",   f"[bold]{total_A}[/bold]",       f"[bold]{total_B}[/bold]")
        overall_table.add_section()
        overall_table.add_row("[bold]Average[/bold]", f"[bold]{avg_A:.1f}[/bold]",     f"[bold]{avg_B:.1f}[/bold]")
        overall_table.add_section()

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
            f"agent_{A.id}_action",       f"agent_{B.id}_action",
            f"agent_{A.id}_years",        f"agent_{B.id}_years",
            f"agent_{A.id}_total_years",  f"agent_{B.id}_total_years",
        ])
        for (gn, rn, a, b, ya, yb) in all_history:
            running_A += ya
            running_B += yb
            writer.writerow([gn, rn, a, b, ya, yb, running_A, running_B])

    console.print(Panel(
        f"[green]{os.path.abspath(csv_path)}[/green]",
        title="[bold]Results Saved[/bold]",
        border_style="green",
    ))

    return {
        'history':      all_history,
        'total_years':  total_years,
        'csv':          csv_path,
    }


player_A = BaseAgent(id_='A')
player_B = BaseAgent(id_='B')
results  = prisoners_dilemma(player_A,
                             player_B,
                             rounds=5,
                             games=3,
                             history=True,
                             show_rounds=True)