# FairScreen Methodology Whitepaper

Status: Authoritative Specification  
Version: 1.0  
Date: 2026-11-09  

---

## 1. Executive Summary

FairScreen is an algorithmic auditing framework designed to detect, measure, and mitigate demographic bias in Large Language Model (LLM) resume screening systems.

Most existing evaluations of LLMs in hiring rely on observational candidate pools. However, observational data conflates demographic signals with real differences in career history, education, and credentials. FairScreen solves this through **counterfactual paired audit testing**: generating synthetic candidate profiles where all professional qualifications are held strictly constant while varying exactly one demographic signal.

FairScreen answers one narrow, falsifiable question:
> *For this specific model, prompt, and test set, does the same qualified candidate receive the same evaluation score, whoever they appear to be?*

---

## 2. Test Design & Synthetic Cohorts

### 2.1 Role Representation

FairScreen constructs test cohorts across six distinct job roles representing diverse industries, skill domains, and traditional gender balances:

1. **Software Engineer** (Technology / Technical)
2. **Data Analyst** (Analytics / Quantitative)
3. **Marketing Manager** (Commercial / Creative)
4. **Registered Nurse** (Healthcare / Clinical)
5. **Customer Success Manager** (Client Services / Interpersonal)
6. **Operations Coordinator** (Logistics / Organizational)

### 2.2 Ground-Truth Qualification Tiers

Each role contains 33 base CVs evenly distributed across three ground-truth tiers ($11 \times \text{Strong}, 11 \times \text{Average}, 11 \times \text{Weak}$), totaling 198 base profiles:

- **Strong Tier:** 14 relevant hard/soft skills, 5 high-impact bullet points with quantified achievements, premier relevant degrees, advanced industry certifications, and leadership action verbs.
- **Average Tier:** 10 relevant skills, 4 standard duty bullet points with operational verbs, accredited degrees, standard certifications.
- **Weak Tier:** 6 basic skills, 3 generic task bullet points with supporting verbs, limited formal training, minor experience gaps.

### 2.3 Matched Variant Construction

From each base CV, FairScreen generates 10 counterfactual variants:

| Attribute | Groups Evaluated | Control Mechanism | Changed Fields |
| :--- | :--- | :--- | :--- |
| **Gender** | Woman, Man | Surname held constant; only first name varied. | `Full Name` |
| **Name Origin** | Anglo, African, East Asian, South Asian, Middle Eastern | All names male-coded to avoid gender confounding; only full name varied. | `Full Name` |
| **Age Signal** | Early Career, Mid Career, Senior | Skills, achievements, and bullets held constant; only graduation year and stated years of experience varied. | `Graduation Year`, `Years of Experience` |

### 2.4 The Pair-Diff Contract

A synthetic pair is valid if and only if its rendered textual representations differ strictly in the designated fields and nowhere else. An automated pair-diff test (`api/tests/test_generator.py`) programmatically enforces this invariant across all 1,980 variants.

---

## 3. Repeated Scoring & Noise Floor

LLMs exhibit non-zero temperature variance. A single evaluation pass cannot distinguish between systematic demographic bias and transient stochastic noise.

FairScreen scores every variant across $R$ independent repeat passes (default: $R = 3$):
1. **Per-Variant Aggregation:** For candidate base $i$ and demographic group $g$, the variant score is the mean over repeats:
   $$\bar{s}_{i, g} = \frac{1}{R} \sum_{r=1}^R s_{i, g, r}$$
2. **Repeat Noise Floor:** To determine whether a detected gap exceeds random LLM fluctuation, FairScreen computes the pooled within-variant standard deviation across all repeated evaluations:
   $$s_{\text{pooled}} = \sqrt{\frac{1}{N} \sum_{i=1}^N \text{Var}(s_{i, g})}$$
   $$\text{Noise Floor} = 1.96 \times s_{\text{pooled}}$$
   Any score gap smaller than the noise floor lies within the model's normal repeat variance.

---

## 4. Statistical Framework

All statistics are non-parametric and avoid distributional normality assumptions.

### 4.1 Paired Mean Score Gap

For a comparison between Group A and Group B on $N$ matched base profiles:
$$d_i = \bar{s}_{i, A} - \bar{s}_{i, B}$$
$$\Delta = \bar{d} = \frac{1}{N} \sum_{i=1}^N d_i$$
- A positive gap ($\Delta > 0$) indicates Group A scored higher on average.
- A negative gap ($\Delta < 0$) indicates Group A scored lower on average.

### 4.2 Bootstrap Confidence Intervals

FairScreen computes two-sided 95% confidence intervals using **10,000 paired bootstrap resamples** with replacement over the base candidate profiles:
1. Resample $N$ paired differences $\{d_i^*\}_{i=1}^N$ with replacement from $\{d_i\}_{i=1}^N$.
2. Compute the resampled mean difference $\Delta^* = \frac{1}{N} \sum_{i=1}^N d_i^*$.
3. Repeat 10,000 times with a stable deterministic seed.
4. Set $[\text{CI}_{\text{low}}, \text{CI}_{\text{high}}] = [\text{Quantile}_{0.025}(\Delta^*), \text{Quantile}_{0.975}(\Delta^*)]$.

A comparison is flagged as having a statistically significant gap if and only if:
$$0 \notin [\text{CI}_{\text{low}}, \text{CI}_{\text{high}}]$$

### 4.3 Paired Permutation Test ($p$-value)

To calculate an exact, assumption-free $p$-value for the null hypothesis $H_0: \mathbb{E}[d_i] = 0$:
1. For each pair $i$, randomly flip the sign of $d_i$ with probability 0.5:
   $$d_i^{\pi} = \sigma_i \cdot d_i, \quad \sigma_i \in \{-1, +1\}$$
2. Compute the permuted mean $|\Delta^{\pi}| = \left| \frac{1}{N} \sum_{i=1}^N d_i^{\pi} \right|$.
3. Execute 10,000 permutations.
4. Calculate the two-sided empirical $p$-value with continuity correction:
   $$p = \frac{\sum_{\pi=1}^{10,000} \mathbb{I}(|\Delta^{\pi}| \ge |\Delta|) + 1}{10,000 + 1}$$

### 4.4 Multiple Testing Adjustment (Holm Step-Down)

Auditing 8 standard comparisons across multiple models generates a family of simultaneous hypotheses. Unadjusted $p$-values inflate the Type I false discovery rate.

FairScreen applies the **Holm-Bonferroni step-down procedure** across all comparisons within an audit mitigation:
1. Sort $M$ comparisons by ascending unadjusted $p$-value: $p_{(1)} \le p_{(2)} \le \dots \le p_{(M)}$.
2. Compute adjusted values:
   $$p_{(k)}^{\text{adj}} = \min \left( 1, \max_{j \le k} \left( (M - j + 1) \cdot p_{(j)} \right) \right)$$

### 4.5 Standardized Effect Size (Cohen's $d_z$)

To measure practical significance independent of sample size:
$$d_z = \frac{\bar{d}}{s_d}$$
where $s_d$ is the sample standard deviation of the paired differences $d_i$.
- $|d_z| \ge 0.2$: Small effect
- $|d_z| \ge 0.5$: Medium effect
- $|d_z| \ge 0.8$: Large effect

### 4.6 Shortlist Rate Ratio & Adverse Impact

Given a score cutoff $\tau$ (default: $\tau = 7.0 / 10$):
$$\text{Rate}_g = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(\bar{s}_{i, g} \ge \tau)$$
$$\text{Shortlist Ratio} = \frac{\text{Rate}_A}{\text{Rate}_B}$$

FairScreen displays the **EEOC 0.8 Four-Fifths Rule** as an illustrative reference line. A ratio below 0.8 indicates potential adverse impact under standard employment guidelines.

---

## 5. Mitigations & The Ranking Quality Gate

FairScreen evaluates three interventions against baseline scoring:

1. **Anonymization:** Programmatically removes candidate names, pronouns, graduation years, stated years of experience, and age cues before the CV is presented to the LLM.
2. **Skills-Only Rubric:** Replaces the generic screening prompt with strict instructions directing the LLM to score purely on demonstrated, role-relevant skills and achievements while ignoring identity or school prestige.
3. **Combined:** Applies both text anonymization and the skills-only rubric.

### 5.1 The 2-Percentage-Point Quality Gate

A debiasing mitigation is unacceptable if it destroys the model's ability to identify qualified candidates. FairScreen assesses screener ranking utility using ground-truth qualification tiers:

1. **Pairwise Ranking Accuracy:** For all candidate pairs $(j, k)$ where $\text{Tier}_j \ne \text{Tier}_k$:
   $$\text{Accuracy} = \frac{\sum_{j < k, \text{Tier}_j \ne \text{Tier}_k} \left( \mathbb{I}(\text{sgn}(s_j - s_k) = \text{sgn}(\text{Tier}_j - \text{Tier}_k)) + 0.5 \cdot \mathbb{I}(s_j = s_k) \right)}{N_{\text{comparable pairs}}}$$
2. **Quality Gate Requirement:**
   $$\text{Accuracy}_{\text{mitigated}} \ge \text{Accuracy}_{\text{baseline}} - 0.02$$

If mitigated ranking accuracy drops by more than 2 percentage points, the mitigation fails the quality gate.

---

## 6. Plain-Language Verdict Logic

FairScreen synthesizes its statistical findings into three human-readable conclusions for each model:

1. **Gap Found:** True if at least one baseline comparison has a 95% bootstrap confidence interval strictly excluding zero.
2. **Fix Worked:** True if:
   - Every significant baseline comparison achieves a statistically supported reduction under the chosen mitigation ($[\text{Reduction CI}_{\text{low}}] > 0$), and
   - The mitigation's 95% CI includes zero for those comparisons.
3. **Quality Kept:** True if the model satisfies the 2-percentage-point ranking accuracy quality gate.

---

## 7. Scope & Ethical Disclosures

- **Synthetic Data Exclusivity:** FairScreen operates exclusively on synthetic CV data. No personally identifiable information (PII) or real candidate resumes are ever gathered or processed.
- **Narrow Inferential Scope:** Findings apply strictly to the evaluated model, prompt version, temperature setting, and synthetic test cohort. FairScreen does not make general claims regarding whether a model provider is "biased in general."
- **Audit Alert, Not Legal Finding:** A flagged gap or adverse shortlist ratio is a quantitative reason for engineering inspection, not legal proof of discriminatory intent.
