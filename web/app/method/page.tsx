"use client";

import { useDashboard } from "@/components/DashboardProvider";
import { Badge, Card, PageHeader } from "@/components/ui";

const comparisons = [
  ["Gender", "Woman minus man"],
  ["Name origin", "African minus Anglo"],
  ["Name origin", "East Asian minus Anglo"],
  ["Name origin", "South Asian minus Anglo"],
  ["Name origin", "Middle Eastern minus Anglo"],
  ["Age signal", "Senior minus mid career"],
  ["Age signal", "Senior minus early career"],
  ["Age signal", "Mid career minus early career"],
];

export default function MethodPage() {
  const { data } = useDashboard();

  return (
    <>
      <PageHeader
        eyebrow="Method"
        title="How FairScreen reaches a verdict"
        description="The audit asks one narrow question: for this model, this prompt and this test set, does the same qualified candidate get the same score, whoever they appear to be?"
      >
        <div className="flex flex-wrap gap-2">
          <Badge tone="neutral">Matched synthetic CVs</Badge>
          <Badge tone="neutral">Seeded and repeatable</Badge>
          <Badge tone="neutral">Scoped result</Badge>
        </div>
      </PageHeader>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="text-xl text-ink">Test design</h2>
          <div className="mt-3 space-y-3 text-sm leading-6 text-muted">
            <p>
              Six roles are covered: Software Engineer, Data Analyst, Marketing Manager,
              Registered Nurse, Customer Success Manager and Operations Coordinator.
            </p>
            <p>
              Each role has 33 base CVs, balanced across strong, average and weak tiers. Every
              CV is synthetic and generated from a fixed seed.
            </p>
            <p>
              Each base CV produces ten variants: two gender-coded names, five name origins and
              three age signals. Gender and origin variants differ only in the full name line.
              Age variants differ only in graduation year and stated years of experience.
            </p>
            <p>
              The pair-diff test enforces that contract. If any other line changes, the test
              fails.
            </p>
            {data ? (
              <p className="rounded-lg border border-line bg-canvas/60 p-3 text-ink">
                This run has {data.run.variants.toLocaleString()} variants and{" "}
                {data.run.scores.toLocaleString()} scores across {data.run.repeats} repeats.
                Each comparison uses up to{" "}
                {Math.max(0, ...data.audits.map((row) => row.n_pairs))} matched pairs.
              </p>
            ) : null}
          </div>
        </Card>

        <Card>
          <h2 className="text-xl text-ink">Comparisons</h2>
          <p className="mt-2 text-sm leading-6 text-muted">
            A positive gap means the first group scores higher. Origin comparisons use Anglo as
            the reference group to avoid a combinatorial explosion of pairwise tests.
          </p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[28rem] border-collapse text-left text-sm">
              <thead className="bg-surface-2 text-xs uppercase tracking-[0.08em] text-muted">
                <tr>
                  <th className="px-3 py-2 font-semibold">Attribute</th>
                  <th className="px-3 py-2 font-semibold">Comparison</th>
                </tr>
              </thead>
              <tbody>
                {comparisons.map(([attribute, comparison]) => (
                  <tr key={`${attribute}-${comparison}`} className="border-t border-line">
                    <td className="px-3 py-2 text-muted">{attribute}</td>
                    <td className="px-3 py-2 font-medium text-ink">{comparison}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card>
          <h2 className="text-xl text-ink">Statistics</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-muted">
            <li>
              <strong className="text-ink">Mean gap:</strong> for each base CV, average the
              repeated scores for group A and group B, subtract B from A, then average across
              base CVs.
            </li>
            <li>
              <strong className="text-ink">Bootstrap CI:</strong> 10,000 resamples of base CVs
              with replacement, seeded for reproducibility.
            </li>
            <li>
              <strong className="text-ink">Paired permutation test:</strong> 10,000 random sign
              flips, two-sided, seeded.
            </li>
            <li>
              <strong className="text-ink">Effect size:</strong> Cohen&apos;s dz, the mean paired
              difference divided by its standard deviation.
            </li>
            <li>
              <strong className="text-ink">Holm correction:</strong> applied across all
              comparisons for a mitigation, pooling attributes and models.
            </li>
            <li>
              <strong className="text-ink">Noise floor:</strong> 1.96 times the pooled
              within-variant repeat standard deviation. This describes a single score, not the
              mean gap.
            </li>
            <li>
              <strong className="text-ink">Shortlist ratio:</strong> rate A divided by rate B at
              the cutoff. The 0.8 marker is a reference, not a legal conclusion.
            </li>
            <li>
              <strong className="text-ink">Ranking accuracy:</strong> pairwise tier accuracy,
              with ties counting as half. AUC is the same quantity.
            </li>
          </ul>
        </Card>

        <Card>
          <h2 className="text-xl text-ink">Verdict rules</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-muted">
            <li>
              <strong className="text-ink">Gap found:</strong> at least one baseline comparison
              has a 95 percent confidence interval excluding zero.
            </li>
            <li>
              <strong className="text-ink">Fix worked:</strong> every significant baseline
              comparison has a supported reduction under the chosen mitigation, and that
              mitigation&apos;s interval includes zero.
            </li>
            <li>
              <strong className="text-ink">Quality kept:</strong> ranking accuracy after the
              chosen mitigation drops by 2 percentage points or less versus baseline.
            </li>
            <li>
              <strong className="text-ink">Chosen mitigation:</strong> combined when present,
              otherwise the mitigation with the smallest mean absolute gap.
            </li>
          </ul>
        </Card>

        <Card className="lg:col-span-2">
          <h2 className="text-xl text-ink">Limits and ethics</h2>
          <div className="mt-3 grid gap-4 text-sm leading-6 text-muted md:grid-cols-2">
            <div>
              <p className="font-semibold text-ink">What this can show</p>
              <p>
                A repeatable association between a protected signal and a score change on
                matched synthetic CVs, for one model, prompt and test set. It can also show
                whether a named mitigation reduces the gap without destroying ranking quality.
              </p>
            </div>
            <div>
              <p className="font-semibold text-ink">What this cannot show</p>
              <p>
                It cannot prove a vendor is biased in general, predict outcomes for real
                applicants, or establish legal compliance. Synthetic CVs cannot capture every
                real-world signal, intersection, or hiring context.
              </p>
            </div>
            <div>
              <p className="font-semibold text-ink">Data handling</p>
              <p>
                No real applicant data is used. The demo runs on mock models with no API keys.
                Real provider adapters read keys only from environment variables and are not
                used in the seeded demo.
              </p>
            </div>
            <div>
              <p className="font-semibold text-ink">Responsible use</p>
              <p>
                Treat results as a diagnostic, not an approval. A passing model is not certified
                fair. A failing model needs a better mitigation or a different screening design
                before it is used on people.
              </p>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}
