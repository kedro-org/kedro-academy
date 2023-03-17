# Warmup exercise

Configure a triangular git workflow and add yourself to the list of participants of the course.

![Triangular workflow](https://github.blog/wp-content/uploads/2015/07/5dcdcae4-354a-11e5-9f82-915914fad4f7.png?resize=2000%2C951)

(Source: https://github.blog/2015-07-29-git-2-5-including-multiple-worktrees-and-triangular-workflows/)

## Steps

1. Fork the `https://github.com/kedro-org/kedro-academy/` repository to your personal GitHub account, and note the URL
2. Go to your Gitpod workspace and configure a new remote location pointing to your fork, by running `git remote add fork {fork_url}`
3. Make sure your name and email are configured on Gitpod, by running `git config user.name "{Name}"` and `git config user.email "{email@domain.com}"` (replace by your actual name and email)
4. Switch to a new branch by running `git switch --create {first-name-last-name}` (replace by your first name and last name)
5. Create a file in this directory called `first-name-last-name.md` (replace by your first name and last name) containing your name and job title
6. Commit the file running `git add first-name-last-name.md` and then `git commit -s -m 'Add myself'` (note the `-s` flag so that commits are signed) and push the changes to your fork doing `git push -u fork first-name-last-name` (note `-u` so that the remote branch is tracked automatically)
7. Open a pull request on the GitHub interface and wait for it to be merged
8. In the meantime, verify that another remote called `origin` is already pointing to the official repository by running `git remote show origin`
9. Fetch the changes from `origin` by running `git fetch origin`
10. Switch to the `main` branch again by running `git switch main`
11. When your pull request is merged, pull the changes from `origin` again by running `git fetch upstream`, and then update your branch with `git merge --ff-only`
12. Delete your old branch by running `git fetch -p fork` (`-p` for "prune" old branches) and `git branch -d first-name-last-name`
13. Create another branch, make a small modification to your file, add & commit the result, and open a _second_ pull request.

If you've made it this far, congratulations! You're ready to start working on the next feature.

If you got stuck or you messed up, you are not alone! Getting out of a git mess can seem daunting, but it's almost always feasible:

![git flow chart](http://justinhileman.info/article/git-pretty/git-pretty.png)
