# PR Review Checklist

Context
- PR link: {PR_LINK}
- Work Item: {WORK_ITEM_LINK}
- Base: {BASE_BRANCH}
- Head: {FEATURE_BRANCH}
- Changed files: [diffs/changed-files.txt](diffs/changed-files.txt)

How to use
- Prepare artifacts: [diffs/](diffs/), [changes/](changes/), [base/](base/).
- Work through sections and check items that apply.
- Record scores and verdict at the end.
- See SOP: [SKILL.md](.ai/skills/pr-review/SKILL.md).

Preparation
- [ ] Repo cloned and refs fetched (origin/{BASE_BRANCH}, origin/{FEATURE_BRANCH})
- [ ] Workspace directories exist and populated
- [ ] Authentication handled safely (no PATs written to disk)
- [ ] Large binaries excluded from export

Scope
- [ ] Change description clear and complete
- [ ] Related work and dependencies identified
- [ ] Risk level stated and justified
- [ ] Breaking changes documented
- [ ] Config or feature flags noted

Code quality
- [ ] Readability and maintainability acceptable
- [ ] Dead code and TODOs removed or ticketed
- [ ] Naming, structure, and layering consistent
- [ ] Small focused commits or rationale provided
- [ ] Defensive programming where appropriate

Correctness
- [ ] Logic matches requirements
- [ ] Edge cases covered
- [ ] Error handling and retries appropriate
- [ ] Concurrency and async safe
- [ ] Data consistency and invariants preserved

Security
- [ ] No secrets or credentials committed
- [ ] Input validation adequate
- [ ] Output encoding where required
- [ ] Authorization checks at boundaries
- [ ] Dependencies reviewed for known CVEs

Performance
- [ ] Hot paths considered; no obvious inefficiencies
- [ ] Algorithms and complexity appropriate
- [ ] I/O and data access optimized or justified
- [ ] Caching or batching opportunities evaluated
- [ ] Memory and allocation patterns reasonable

Testing
- [ ] Unit tests updated or added
- [ ] Integration tests updated or added
- [ ] Regression tests for fixed issues
- [ ] Negative and edge case tests
- [ ] Coverage adequate for risk

Operations
- [ ] Migrations safe and reversible
- [ ] Rollback strategy documented
- [ ] Config and feature flags documented
- [ ] Logging, metrics, tracing updated
- [ ] Alerts and dashboards considered

Documentation
- [ ] README or service docs updated
- [ ] Changelog entry prepared if needed
- [ ] Inline comments describe non-obvious logic
- [ ] Developer runbooks updated

Diff walkthrough
- Review changed files: [diffs/changed-files.txt](diffs/changed-files.txt)
- Inspect patches under [diffs/](diffs/) and compare with [changes/](changes/) and [base/](base/).
- Note additions, removals, renames, and migrations.

Scoring rubric per dimension 0..5
- 0: unacceptable; critical issues
- 1: poor; multiple issues; needs major changes
- 2: fair; notable issues; changes required
- 3: good; minor issues; acceptable with comments
- 4: very good; small nits
- 5: excellent; meets or exceeds standards

Scores
- Correctness: 
- Quality: 
- Security: 
- Testing: 
- Operations: 
- Performance: 
- Documentation: 
- Overall (avg or weighted): 

Decision
- [ ] Approve
- [ ] Approve with comments
- [ ] Request changes

Rationale
- Summary of key reasons for decision.

Follow-ups
- [ ] Blocking items (must-fix before merge)
- [ ] Non-blocking items (post-merge tasks)

References
- SOP: [SKILL.md](.ai/skills/pr-review/SKILL.md)
- PR: {PR_LINK}
- Repository: {REPO_NAME} ({PROJECT_NAME})

Reviewer notes
- Use consistent terminology.
- Prefer explicitness over implicit assumptions.
- Document any uncertainties or ambiguities.
- Capture test evidence where relevant.