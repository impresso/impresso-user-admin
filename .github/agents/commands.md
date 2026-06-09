# Agent: Commands

This guide is for creating, editing, and testing Django management commands in the impresso-user-admin project. The goal is to keep command code small, readable, and safe to run in production-like environments.

Management commands in this repository should feel operationally clear. Their output should separate the different kinds of records they touch, use whitespace generously, and include enough context for an operator to understand what will happen before any data changes are made.

## When To Create A Command

Create a management command when the behavior is operational, repeatable, and tied to a project workflow rather than to a request/response view. Good examples are bulk updates, audits, cleanup jobs, admin helpers, and data inspection tools.

If the behavior needs to run on a schedule, make the command a thin orchestration layer and let Celery tasks or model methods do the actual work. The command should read like a control panel, not a second implementation of business logic.

## How To Structure A Command

Start by looking for the closest existing command in `impresso/management/commands/`. Reuse its tone, output style, and options when the new command belongs to the same operational family.

A command should usually follow this shape:

- a short `help` string
- explicit arguments in `add_arguments()`
- a `handle()` method that orchestrates the work
- helper methods only when they improve readability
- logging or stdout messages that tell the operator what is happening

Keep the command focused. If you need data classification, formatting, URL generation, or status transitions, prefer small private helper methods over one long `handle()` body.

## Editing A Command

Before changing a command, read the command itself and the nearest test file. If the command touches existing side effects, also read the related model, signal, or task code so you do not duplicate logic accidentally.

When editing, preserve the command’s existing operational style. If the command prints section headers, banners, or indented blocks, keep that visual language consistent. In this repository, command output should have space and air: blank lines are intentional, and they help operators scan the result quickly.

If the command creates or mutates records, make sure it does so through the normal model save path when side effects are expected. Avoid bulk updates unless you are certain no signals, tasks, or audit behavior must run.

## Output Style

Prefer output that is easy to scan in a terminal. A good command output usually separates records into visual categories, such as “needs action”, “already valid”, and “cannot process”. For each record, include the most useful identifiers first, then the reason it was selected, then a link or reference that lets the operator jump to the relevant admin record.

Paragraph form is useful for the summary at the top and the conclusion at the bottom. Inside the record listing, short labeled blocks are often better than a single dense sentence.

A practical pattern is:

- one short intro paragraph
- a summary line with counts
- grouped record sections with blank lines between them
- a closing paragraph that says what was skipped or what still needs implementation

## Output Template

Use this as a starting point for operator-facing commands that inspect and optionally mutate records:

```python
self.stdout.write(
	"\n"
	f"{self.ANSI_BOLD}Command Title{self.ANSI_RESET}\n"
	f"  - Dry run: {self.ANSI_BOLD}{dry_run}{self.ANSI_RESET}\n"
)

self.stdout.write(
	"\n"
	f"{self.ANSI_BOLD}Summary{self.ANSI_RESET}\n"
	f"  - REVOCATION NEEDED: {self.ANSI_YELLOW}{needed_count}{self.ANSI_RESET}\n"
	f"  - ACTIVE: {self.ANSI_GREEN}{active_count}{self.ANSI_RESET}\n"
	f"  - ACTIVE (NON-REVOKABLE): {self.ANSI_RED}{non_revokable_count}{self.ANSI_RESET}\n"
)

self._write_section("REVOCATION NEEDED", self.ANSI_YELLOW, needed_blocks)
self._write_section("ACTIVE", self.ANSI_GREEN, active_blocks)
self._write_section(
	"ACTIVE (NON-REVOKABLE)",
	self.ANSI_RED,
	non_revokable_blocks,
)

self.stdout.write(
	self.style.NOTICE(
		f"Dry run completed: {needed_count} revocations need implementation."
	)
)
```

Inside each record block, keep stable parsing tokens plain text (`Request ID: <id>`) and place visual emphasis in section headers and labels.

## Testing A Command

Every command change should have a focused test module under `impresso/tests/management/commands/`. Use the nearest existing command test as a template and keep the tests aligned with the output wording.

Test both behavior and output. For a command that mutates data, verify the database state after running the command. If the command should trigger existing side effects, assert those too. For dry-run mode, verify that nothing changes and that the output still explains what would have happened.

A useful command test usually covers:

- dry-run behavior
- the main mutation path
- a non-mutating or skip path
- a missing-data or invalid-metadata path
- any user-visible admin links or references in the output

When the test depends on Celery behavior, remember that this project runs tasks eagerly in the test runner. Do not wait for real time-based scheduling unless the test is specifically about the scheduler. If you only need to verify that a task would be queued, patch the enqueue call and assert the arguments.

## Recommended Workflow

1. Read the nearest command and test file.
2. Identify the exact record selection rule and side effects.
3. Edit the command in the smallest possible slice.
4. Add or update the focused test module.
5. Run the targeted test command first.
6. Only broaden validation if the focused test exposes a wider problem.

## Example Validation Commands

```bash
ENV=test pipenv run python manage.py test impresso.tests.management.commands.test_revokemembershipaccess
ENV=test pipenv run python manage.py test impresso.tests.management.commands.test_checktemporarymemberships
ENV=dev pipenv run ./manage.py revokemembershipaccess --dry-run
```

## Practical Rules

- Prefer readable terminal output over terse output.
- For operator-facing commands, use visual spacing intentionally: add blank lines between phases and between record groups so the output can be scanned quickly under pressure.
- Use ANSI emphasis consistently for terminal UX, inspired by updatespecialmembership patterns: bold for key actions or identifiers, color-coded section headers/status labels (for example needed action, active, non-processable), but keep machine-asserted tokens like `Request ID: <id>` plain when tests parse exact substrings.
- Use `IMPRESSO_BASE_URL` for absolute admin links when you want the operator to open the edited record quickly.
- Keep command-specific logic inside the command unless it clearly belongs in a shared helper.
- Do not add new Celery tasks unless the command truly needs asynchronous execution.
- Keep tests narrow and deterministic.

## Final Check

Before you finish a command change, ask whether the operator can understand three things from the output alone: what was found, what needs action, and what was actually changed. If the answer is no, improve the formatting before you add more logic.
