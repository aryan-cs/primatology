# primatology — style guide

this document covers the aesthetic and structural conventions of the primatology project. all experiments (part 1, part 2, part 3, and beyond) should follow these guidelines for consistency.

---

## code style

### general
- use lowercase filenames with underscores: `base_agent.py`, `part_1.py`
- keep imports at the top of the file, except for provider-specific sdk imports inside `BaseAgent` methods (lazy imports — only load what you use)
- move shared imports (`csv`, `os`, `json`, `datetime`) to the top of the file, not inside functions
- use `uv` for dependency management; all dependencies live in `pyproject.toml`

### naming
- constants in `UPPER_SNAKE_CASE`: `PAYOFFS`, `ACTION_COLOR`
- functions and variables in `lower_snake_case`: `build_prompt`, `game_history`
- classes in `PascalCase`: `BaseAgent`
- align assignment operators vertically when initializing related variables:
  ```python
  scores       = {A.id: 0, B.id: 0}
  game_history = []
  ```

### functions
- type-annotate function signatures:
  ```python
  def prisoners_dilemma(A: BaseAgent, B: BaseAgent, rounds: int = 10) -> dict:
  ```
- use inner functions (defined inside the experiment function) for helpers that are tightly scoped to that experiment, like `build_prompt`, `parse_action`, and `query_until_valid`
- always provide defaults for optional parameters; prefer `False` as the default for feature flags like `history` and `show_rounds`

### robustness
- never use fallbacks, defaults, or fake data — this is production-quality research; bad data is worse than no data
- always wrap `json.loads` in a try/except; on failure, log a `[WARN]` with the attempt number and immediately retry
- `query_until_valid` retries indefinitely until a valid response is received — no `max_retries` cap, no early exit:
  ```python
  def query_until_valid(agent: BaseAgent, prompt: str) -> tuple[str, str]:
      attempt = 0
      while True:
          attempt += 1
          response = agent.query(prompt, json_mode=True)
          result   = parse_action(response)
          if result is not None:
              return result
          console.print(f"  [yellow][WARN] Agent {agent.id} attempt {attempt} failed. Retrying...[/yellow]")
  ```
- the attempt counter in the warning makes persistent model misbehavior easy to spot

---

## agent style

### BaseAgent
- agents are identified by a short string id (`'A'`, `'B'`, `'society_1'`, etc.)
- `__str__` should return `[Agent {id} ({provider}/{model})]`
- `__init__` should print `[AGENT {id} ({provider}/{model})] Hello, World!`
- `query(prompt, json_mode=False)` is the standard interface; all experiments call this
- provider-specific logic lives in private methods (`_query_gemini`, etc.) dispatched via a dict

### JSON mode
- always use native json mode (`json_mode=True`) rather than prompting the model to return json
- the standard response schema for binary-choice experiments is:
  ```json
  {"reasoning": "<step-by-step reasoning>", "action": "<ACTION>"}
  ```
- for experiments with more complex responses, extend the schema but always include a `reasoning` field

---

## prompt style

- address the agent by its id: `"You are Agent {agent.id}"`
- state the context clearly upfront, then list payoffs or rules as a structured block
- always ask the model to reason step-by-step before committing to an action
- end every prompt with the exact json schema expected:
  ```
  Respond in JSON with this exact schema:
  {"reasoning": "<your step-by-step reasoning>", "action": "<ACTION>"}
  ```
- history (when enabled) should be presented from the agent's own perspective — "you played X, opponent played Y"

---

## output style

all terminal output uses `rich`. no raw `print()` calls for experiment output (only for module-level hello world banners).

### colors
| element         | color     |
|-----------------|-----------|
| Agent A         | cyan      |
| Agent B         | magenta   |
| COOPERATE       | green     |
| DEFECT          | red       |
| warnings        | yellow    |
| errors          | red       |
| success/saved   | green     |
| neutral/borders | white     |

for experiments with more than two agents, extend this palette consistently. avoid reusing the same color for different agents.

### panels
- every agent's reasoning goes in its own `Panel` with a colored border matching the agent's color
- decisions/outcomes go in a white-bordered `Panel` titled `Decision`
- summary statistics (scores, classifications) go in their own `Panel`
- file save confirmations go in a green-bordered `Panel` titled `Results Saved`
- all panels should `expand=True` (full terminal width) by default

### rules
- use `console.rule()` to separate rounds: `Round {n} / {total}`
- use a bolder/differently-labeled rule to separate games: `Game {n} / {total}`
- use a rule before the final results section: `Final Results`

### tables
- all tables use `box=box.ROUNDED` and `expand=True` (full terminal width)
- header style: `bold`
- all columns `justify="center"`
- use `add_section()` to visually separate summary rows (totals, averages, classifications) from per-round or per-game data
- summary rows should be bolded

### classifications
agent behavior classifications are based on action rates over the full experiment:

| cooperation rate | label                  | color  |
|------------------|------------------------|--------|
| ≥ 60%            | Largely Cooperative    | green  |
| ≤ 40%            | Largely Defective      | red    |
| 41–59%           | Largely Neutral        | white  |

adapt thresholds and labels for experiments where "cooperation" is not the relevant axis (e.g. trading behavior, resource use).

### header panel
every experiment should open with a summary panel using `box=box.DOUBLE`:
```
[experiment name]
[Agent A] vs [Agent B]
Key params: rounds, games, history, etc.
```

---

## results & data

### csv output
- saved to `results/{experiment-name}/YYYYMMDD_HHMMSS.csv`
- always include a `game` column (even if `games=1`) and a `round` column
- always include running totals as the last columns
- column names follow the pattern `agent_{id}_action`, `agent_{id}_payoff`, `agent_{id}_total`

### return value
experiment functions always return a dict with at minimum:
```python
{
    'history':      ...,  # full log of all games and rounds
    'total_scores': ...,  # cumulative scores keyed by agent id
    'csv':          ...,  # path to saved csv
}
```

---

## file structure

```
primatology/
├── base_agent.py       # BaseAgent class
├── part_1.py           # part 1 experiments (simple games)
├── part_2.py           # part 2 experiments (society simulations)
├── part_3.py           # part 3 experiments (public rating)
├── STYLE.md            # this file
├── pyproject.toml      # uv dependencies
├── .env                # api keys (never committed)
└── results/
    ├── prisoners-dilemma/
    ├── chicken/
    ├── battle-of-the-sexes/
    ├── stag-hunt/
    └── society/
```

each experiment gets its own subdirectory under `results/`.

---

## hello world banners

every module prints a hello world banner on import/run:
```python
print("[MODULE NAME] Hello, World!")
```
this makes it easy to trace which modules are loaded and in what order during a run.
