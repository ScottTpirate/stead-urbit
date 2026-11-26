# How Stead works

## Why put these things together?

Say the ticket is in Jira, the visitor guide is in Confluence, and the site that publishes the guide is in Git. You can paste links between all three. A month later someone still has to work out which version the ticket referred to, who approved the change and whether the published text actually says the same thing.

I’d like to answer those questions by opening the project. In Stead, Work holds the request and its discussion. The guide has an address and a saved revision. If a change also touches software, Code can show the exact file at a particular commit. A team organizing an event can stop at the guide. A software team can follow the change into the repository.

## Follow a change

Say the Monday meeting moves to Wednesday. In **Work**, one item records the request, the discussion and what a reviewer needs to check. In **Docs**, the visitor guide has its own saved revision. A relationship connects them. Someone can open the task from its supporting page and see why that sentence changed. If the meeting time also changes while you are editing, the revision matters.

When you save, the browser sends a request to the project’s **Home** with the revision you started from. Home checks your current access and that revision. If both checks pass, it records the change and returns a receipt. If somebody else saved first, you can open the current version, compare the two and decide what to keep. A request ID lets Home recognize a retry after an interrupted connection.

## What Urbit does here

A ship is a personal Urbit server with its own network identity. In the private pilot, one ship hosts Stead Home and another can approve a member’s browser sign-in. The member approves the request on their identity ship. Urbit tells Home which ship actually sent the approval. Home matches that sender to an enrolled member and applies the project’s permissions. The team can operate its own workspace while members keep their own identities. That’s how two people looking at the same project link can have different access.

Home is a Hoon application running under Gall, Urbit’s application system. It processes changes in order and keeps its state across restarts. That gives the team one place to settle what was accepted, even when several browsers or workers are involved. Reading a page sends the authorized content to your browser. Other members’ ships don’t need a copy of the whole project. [How Gall applications keep state](https://docs.urbit.org/build-on-urbit/userspace)

## What lives in Git, and what lives in Home

| When you open | What you are reading |
| --- | --- |
| A Work item | A structured record in Home. The title, assignment, state and discussion belong to the project. Project and personal views refer to the same item. |
| A Docs page | Markdown with a revision in an authorized collection. The collection’s exported history can be opened and checked with Git tools. |
| A repository file | The bytes at a path in a Git commit. A branch can advance. The commit ID identifies the exact version you read. |
| Project access or a receipt | Home’s record of who may act or which change it accepted. A Git clone carries repository content and history. Restoring the team’s memberships and work requires a Home backup as well. |

There’s a practical reason for keeping the writing in ordinary files. If you move away from Stead, you can recover a Docs collection, open its Markdown in another editor and inspect its history with Git. If you want to restore the whole workspace, you also need the Home state that explains who had access and why the team did the work.

On the private pilot, the Git worker serves a repository snapshot that Home has accepted. A member used ordinary Git to clone it, check its object history and fetch again. That same commit can be inspected in **Code**. For a team that just needs tasks and pages, **Work** and **Docs** stand on their own.

## Where agents fit

The design gives a worker a specific task, the input revisions it may read and a bounded way to propose a result. A local or hosted model can supply the reasoning. Home and the reviewer still decide what enters the project. For the meeting change, a useful result is the proposed Markdown edit against the exact page the worker read.

The pilot already supports member sign-in, project Work and Docs, and reading an accepted Git repository. The full agent handoff is still being tested. A model describing the right edit in a trial left the saved page untouched. The next milestone is a reviewer opening an actual proposal, checking the change and accepting it into the page’s history.
