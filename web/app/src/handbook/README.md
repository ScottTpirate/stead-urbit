# Working with Git in Stead

Open a software project and choose **Code** beside **Docs**. The file list shows the snapshot that Home has accepted. Use the branch or tag picker to choose a version. A root README appears below the file list. Choose its filename to open it, or browse another folder or file. For a Markdown file, **Read** shows the formatted page and **Raw** shows its exact text.

## Clone a project

1. In the project's **Code** view, expand **Clone**. Copy the **Clone URL**.
2. Choose **Create read credential** if your Home offers it. Copy the credential while it is visible and note when it expires.
3. In a terminal, run the command below with your copied URL in place of `CLONE_URL`. When Git asks, enter `stead` as the username and paste the Git credential at the password prompt.

```sh
git clone CLONE_URL my-project
cd my-project
git log -1 --oneline
```

The characters you paste at the password prompt may stay invisible. Keep the credential out of URLs, shell commands, issues and screenshots. Your Urbit sign-in approves your browser session. The Git credential gives your Git client access to this repository.

## Check which version you have

In your clone, fetch updated references and inspect the latest commit on the remote branch. Substitute your branch name if the project uses a different one.

```sh
git fetch origin
git log -1 --oneline origin/main
```

Compare that commit with the one shown in **Code** for the same branch. Fetching leaves your working files alone. A branch can move when a new change is accepted. A commit ID identifies one exact version.

## Share a change

A read credential covers clone and fetch. You can still edit files and commit in your local clone. Ask the project maintainer which remote and review process accept contributions before pushing. The private pilot has verified clone and fetch. An authorized review and merge can be claimed only when the Home confirms them.

## If Git stops working

For an authentication error, check the username, the credential's expiry and your current project access. Your Git client may have cached an older password for this repository. For a connection error on the private pilot, check the private connection first. A project shows **Code** when it has a repository you can access.

This Handbook README is a reading example. Get the clone URL and credential from the project whose files you want.
