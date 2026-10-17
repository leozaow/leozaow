# Metrics & Calculation Methodology

This document defines the mathematical, temporal, and operational rules governing GitHub contribution calculations in `leozaow/leozaow`.

---

## 1. Core Terminology & Distinctions

To avoid misleading profile statistics, we maintain strict conceptual boundaries:

- **GitHub Contribution Event**: An activity recognized by GitHub's contribution system (commits to default/gh-pages branches, opening issues, submitting pull requests, reviewing pull requests).
- **Git Commit**: A specific commit object in a Git repository. A single contribution event may encompass multiple commits, or vice-versa.
- **Qualifying Day**: A calendar day $d$ on which `contributionCount(d) >= 1`.
- **Rolling Year (Last 365 Days)**: The 365 calendar days ending on the reference date: $[d_{\text{today}} - 364, d_{\text{today}}]$.
- **All-Time Scope**: The complete set of records from account registration ($d_{\text{created}}$) to $d_{\text{today}}$.

---

## 2. Daily Streak Formulation

### 2.1 Current Daily Streak & Grace Period

Let $C(d)$ denote the contribution count on calendar day $d$, and let $T$ be the reference date (today).

1. **Active Day $T$**:
   $$\text{If } C(T) > 0: \quad d_{\text{end}} = T$$
   The streak length is the number of consecutive calendar days counting backwards from $T$ where each day satisfies $C(d) > 0$.

2. **Unfinished Day Grace Period**:
   $$\text{If } C(T) == 0 \text{ and } C(T - 1) > 0: \quad d_{\text{end}} = T - 1$$
   Because a calendar day in progress may not yet have recorded activity, the streak is considered unbroken if yesterday qualified. The streak ends on yesterday ($T - 1$).

3. **Broken Streak**:
   $$\text{If } C(T) == 0 \text{ and } C(T - 1) == 0: \quad \text{Length} = 0, \quad d_{\text{start}} = \text{None}, \quad d_{\text{end}} = \text{None}$$
   No fabricated dates or inverted intervals ($d_{\text{start}} > d_{\text{end}}$) are ever emitted.

### 2.2 Longest Daily Streak

The longest daily streak is the maximal contiguous subsequence of qualifying days across the retrieved dataset:
$$\max |[d_s, d_e]| \quad \text{such that} \quad \forall d \in [d_s, d_e], \, C(d) \ge 1 \text{ and } d_{i+1} = d_i + 1\text{ day}$$

**Tie-Breaking Policy**:
When multiple streaks share the maximum length, the algorithm deterministically selects the **most recent** interval (`tie_breaker="most_recent"`). Consequently, when the current streak equals the all-time record, the longest streak displays the current streak's exact interval.

---

## 3. Weekly Streak Formulation

Weekly metrics are calculated using ISO 8601 week definitions (Monday through Sunday):

1. **Active Week**: A week $W$ is active if:
   $$\exists d \in W \quad \text{such that} \quad C(d) \ge 1$$
2. **Current Weekly Streak**:
   - If the current unfinished week (Monday through $T$) has activity, it is included.
   - If the current week has zero activity so far, but the preceding week was active, the grace rule preserves the streak ending on the preceding Sunday.
   - Otherwise, the weekly streak is 0.
3. **Usage**: Weekly metrics provide diagnostic insight into broad regularity and are recorded in `stats.json`. Daily streaks remain the headline metric on the visual card to prevent conflation with continuous daily activity.

---

## 4. Timezone & Temporal Consistency

GitHub's GraphQL `contributionCalendar` indexes days using ISO calendar strings (`YYYY-MM-DD`) derived from GitHub's internal UTC timeline.

- **Reference Date Determination**: The reference date $T$ is derived from the latest date in the GitHub calendar payload or specified via `--reference-date YYYY-MM-DD`.
- **Local Time vs UTC**: The scheduled runner executes daily at 06:20 UTC (03:20 BRT). This schedule ensures the previous UTC day has concluded while allowing morning freshness in local time (`America/Sao_Paulo`).

---

## 5. Recent Activity Series (35-Day Window)

The visual card includes a 35-day daily volume bar chart:
- **Window Range**: $[T - 34\text{ days}, T]$ (exactly 35 discrete calendar days).
- **Date Membership Highlight**: A bar for day $d$ is highlighted with the streak accent color (`#fb8c00` / `#d97706`) if and only if:
  $$d_{\text{start}} \le d \le d_{\text{end}} \quad \text{and} \quad C(d) \ge 1$$
  This eliminates the flaw of index-based highlighting where zero-activity grace days were mistakenly colored orange.
- **Normalization**: Bar heights scale linearly between 7 px and 56 px based on $C(d) / \max_{i} C(d_i)$. Inactive days are rendered as subtle 3.5 px baseline markers.
