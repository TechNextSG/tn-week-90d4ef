# Working in this repository

This repository publishes one page: a week-by-week schedule that the client reads on their phone.
`README.md` is written for a person; this file is the same ground rules for an agent.

**This repository is public.** Anything committed here is readable by anyone with the link,
including every name on the page. Never add internal notes, ticket or requirement references,
tooling names, or anything written for our side rather than theirs.

## The source of truth is `tracks/*.md`

Five files, one per track, one table row per session. Editing a row **is** editing the schedule.

```
tracks/accounting.md   tracks/pms.md   tracks/trackc.md   tracks/unified.md   tracks/joint_walk.md
```

`roster.md` maps the short person tokens to real names. `week.md` holds the five day headings and
the "what we need from you" cards. `page.template.html` is the page's layout.

`index.html` and `schedule.json` are **generated and not tracked** — they are built from `tracks/`
on every push and served from the build. Do not create them, commit them, or edit them; if you
find them in the working tree they are local build output.

## Rules, in the order they cause damage when broken

1. **Never change or renumber the `id` column.** The page's done-ticks in `status.json` are keyed
   to it. A changed id does not error — the tick silently stops showing, and nobody notices. If a
   session is genuinely gone, delete its whole row *and* its `status.json` entry.
2. **Never add a row with an empty `casa` column.** A session with nobody from the client in it is
   internal, and internal sessions do not belong in a public repository. The build refuses this,
   deliberately.
3. **Only use person tokens that exist in `roster.md`.** A token that is not there fails the
   build, which is the point — a typo must not quietly drop someone from a session.
4. **Write the `say` column for the client, not for us.** It is the sentence they read. Plain
   language, their vocabulary, no internal shorthand.
5. **Do not edit `status.json` to make a build pass.** It records what has actually happened. If
   the build complains that a tick has no session, the row was wrong, not the tick.

## Before you commit

```bash
python build.py --check          # validates and writes nothing; exit 0 = good, 2 = refused
```

If you changed `build.py` itself, also run:

```bash
python build.py --self-test      # proves each check still fires on input designed to break it
```

`--self-test` exists because every check reports problems by adding to a list, so a check that
stopped working would report an empty list and read as "nothing wrong". Run it after touching the
validator, and do not trust a green `--check` from a validator you just edited without it.

## Committing

Commit **straight to `main`**. Do not create a branch and do not open a pull request — there is no
review step here by design, and a PR just parks the change waiting for someone who is not
expecting it.

Commit only the paths you meant to change; several people work in this tree.

## What happens after you push

A workflow validates, builds, and deploys. If validation fails **nothing is deployed** and the
page people are looking at stays exactly as it was, with a red mark against the commit. That is
what makes committing to `main` without review safe.

Two things the build reports but never blocks:

- **Two sessions needing the same person at once.** Genuinely new ones are named in the run
  output; ones already known about are listed in `baseline-clashes.json` and stay quiet. Deciding
  who moves is a judgement, not a mistake.
- Nothing else. Every other finding refuses the build.

## What the build cannot catch

It checks that a row is *well-formed*, not that it is *right*. A time that is valid but wrong, a
sentence that reads well but describes the wrong session, the wrong person in the room — all build
cleanly and publish. If you changed times or attendees, say so plainly in your reply so a human
can check the thing a machine cannot.
