# 🏸 Badminton Tournament Tracker

Players register themselves (or their pre-formed pair) for tournament groups straight from the
website. Before the tournament, the admin hits one button and all remaining unpaired players are
randomly paired **within their group**.

Hierarchy: **Tournament → Groups** (Mens/Womens/Boys/Girls/Kids Singles, Mens/Womens/Mixed/Boys/Girls/Kids Doubles).

## How it works (same pattern as the worldcup tracker)

- Static site on **GitHub Pages** — `index.html` + `data.json`, no backend.
- The website submits changes by triggering the **`Submit` workflow** (`submit.yml`) via the
  GitHub API. The workflow runs `scripts/apply_action.py`, which validates and updates
  `data.json`, commits, and pushes.
- The push triggers **`deploy.yml`**, which republishes the site. Changes appear in ~1–2 minutes;
  the page polls automatically after you submit.
- Admin actions (create tournament, random pairing, lock/unlock, remove entry) require a PIN that
  the workflow checks against the **`ADMIN_PIN`** repository secret. Plain registrations need no PIN.

## Setup (one-time, ~10 minutes)

### 1. Create the repository
Create a new **public** repo (e.g. in a throwaway org, like the worldcup one). Don't initialise with files.

### 2. Push this code
```bash
cd ~/badminton
git remote add origin https://github.com/YOUR_ORG/badminton.git
git branch -M main
git push -u origin main
```

### 3. Enable GitHub Pages
Repo → **Settings → Pages** → Source: **GitHub Actions**.

### 4. Set the admin PIN
Repo → **Settings → Secrets and variables → Actions → New repository secret**
- Name: `ADMIN_PIN`
- Value: any PIN you'll remember (e.g. `4271`)

### 5. Create the dispatch token
The page needs a token to trigger the Submit workflow on visitors' behalf:

1. Go to https://github.com/settings/personal-access-tokens/new (Fine-grained token)
2. Resource owner: the org that owns this repo
3. Repository access: **Only select repositories → this repo**
4. Permissions: **Actions → Read and write** (nothing else)
5. Expiration: pick something past your tournament season

### 6. Configure `index.html`
At the top of the `<script>` block in `index.html`, set:
```js
const OWNER  = "YOUR_ORG";
const REPO   = "badminton";
const TOKEN_A = "github_pat_FIRST_HALF";   // split the token in two —
const TOKEN_B = "SECOND_HALF";             // GitHub revokes tokens it finds whole in public repos
```
Commit and push — the site redeploys automatically.

### 7. Use it
- Share the Pages URL in the WhatsApp group. Players tap **Join** on a group, enter their name
  (and optionally their partner's name for doubles).
- If a partner registered alone earlier, entering their name pairs you with them.
- Before the tournament: open **Admin** (bottom of page), enter the PIN, and tap
  **🎲 Randomly pair remaining players** — every doubles group's leftovers get shuffled into pairs.
  An odd player out stays listed as "waiting for partner".
- Also in Admin: create tournaments (pick which groups to include), lock/unlock registrations,
  and remove entries (✕ next to each name).

## Security trade-offs (fine for a friends group, know them anyway)

- The dispatch token is visible in the page source. It can **only** trigger Actions on this one
  repo — worst case someone spams workflow runs. The split into `TOKEN_A`/`TOKEN_B` just stops
  GitHub's secret scanner auto-revoking it.
- `workflow_dispatch` inputs (including the admin PIN) are visible in the public repo's Action
  run logs. If that ever bothers you, make the repo private (Pages on private repos needs GitHub Pro)
  or rotate the PIN after each tournament.
- Anyone with the link can register names. The admin can remove junk entries.

## File structure
```
badminton/
├── index.html                  ← Single-page app (registration + admin)
├── data.json                   ← All tournament data (committed by the workflow)
├── scripts/
│   └── apply_action.py         ← Validates & applies register/pair/admin actions
└── .github/workflows/
    ├── deploy.yml              ← Publishes to GitHub Pages on every push
    └── submit.yml              ← workflow_dispatch handler the website calls
```
