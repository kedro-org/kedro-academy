# Triangular workflow

Configure a triangular git workflow and add yourself to the list of participants of the course.

![Triangular workflow](https://github.blog/wp-content/uploads/2015/07/5dcdcae4-354a-11e5-9f82-915914fad4f7.png?resize=2000%2C951)

(Source: https://github.blog/2015-07-29-git-2-5-including-multiple-worktrees-and-triangular-workflows/)

## Steps

### Configure Gitpod

1. Fork the `https://github.com/kedro-org/kedro-academy/` repository to your personal GitHub account, the resulting URL will be `https://github.com/{username}/kedro-academy`
2. Open your fork on Gitpod, by creating a new workspace or alternatively navigating to `https://gitpod.io/#https://github.com/{username}/kedro-academy/`
3. Make sure your name and email are configured on Gitpod, by running `git config user.name "{Name}"` and `git config user.email "{email@domain.com}"` (replace by your actual name and email)
4. Switch to a new branch by running `git switch --create {first-name-last-name}` (replace by your first name and last name)
5. Create a file in the `participants` directory called `first-name-last-name.md` (replace by your first name and last name) containing your name and job title (or any dummy text)
6. Commit the file running `git add first-name-last-name.md` and then `git commit -s -m 'Add myself'` (note the `-s` flag so that commits are signed)
7. Push the changes to your fork doing `git push -u origin first-name-last-name` (note `-u` so that the remote branch is tracked automatically)

At this point, Gitpod might warn you that you don't have write permissions. If so, follow the steps to configure it.

### Submit the pull request

7. Open a pull request on the GitHub interface

### Finish configuring your triangular workflow

In the meantime, you can finish configuring your triangular workflow:

8. Go to your Gitpod workspace and configure a new remote location pointing to the official repository, by running `git remote add upstream https://github.com/kedro-org/kedro-academy/`
9. Fetch the changes from `upstream` by running `git fetch upstream`
10. Switch back to main by running `git switch main`
11. Set `main` to track the official repository, by running `git branch --set-upstream-to=upstream/main`
12. If necessary, go back to your branch to address the feedback from the pull request

### Get up to speed with upstream changes

13. When your pull request is merged, pull the changes from `upstream` again by running `git fetch upstream`
14. Switch back to main running `git switch main`, and then update the branch with `git merge --ff-only`
13. Delete your old branch by running `git fetch -p fork` (`-p` for "prune" old remote branches) and `git branch -d first-name-last-name`

If you've made it this far, congratulations! You're ready to start working on the next feature.

If you got stuck or you messed up, you are not alone! Getting out of a git mess can seem daunting, but it's almost always feasible:

![git flow chart](http://justinhileman.info/article/git-pretty/git-pretty.png)
