const github = require("@actions/github");
const core = require("@actions/core");

const run = async () => {
  const token = core.getInput("token");
  const branch = core.getInput("branch");
  let stable = core.getInput("stable");
  if (stable === "true") stable = true;
  else if (stable === "false") stable = false;
  else core.setFailed("There is an error in the stable input");
  const octokit = github.getOctokit(token);
  const {owner:owner,repo:repo} = github.context.repo
  let {
    data: {
      object: { sha: commit },
    },
  } = await octokit.rest.git.getRef({
    owner: owner,
    repo: repo,
    ref: `heads/${branch.replace("refs/heads/", "")}`,
  });
  console.log(`Current commit SHA: ${commit}`)
  const { data: tags } = await octokit.rest.repos.listTags({
    owner: owner,
    repo: repo,
  });
  console.log(`Tags:`, tags)
  const re = /\d+\.\d+\.\d+(-\d+)*?/;
  let latestTag, i;
  while (latestTag == null) {
    i = 0;
    console.log(`Current latest tag: ${latestTag}`);
    while (i < tags.length && latestTag == null) {
      console.log(`Tag name #${i}: ${tags[i].name} | ${commit}==${tags[i].commit.sha} && ${tags[i].name.match(re)}`)
      if (
        commit === tags[i].commit.sha &&
        (!tags[i].name.match("rc") || !stable) &&
        tags[i].name.match(re)
      ){
        latestTag = tags[i].name;
        console.log(`Matched latest tag: ${latestTag}`)
      } 
      i++;
    }
    if (latestTag == null) {
      const { data: data } = await octokit.rest.repos.getCommit({
        owner: owner,
        repo: repo,
        ref: commit,
      });
      console.log(`Commit parents:`, data.parents)
      if (data.parents.length !== 1) {
        core.setFailed(
          "Branch history is not linear. Try squashing your commits."
        );
        return;
      } else {
        console.log(`Setting a new commit: ${data.parents[0].sha} from commit ${commit}`);
        commit = data.parents[0].sha;
      }
    }
  }
  if (latestTag == null) {
    core.setFailed(
      "The action couldn't find a matching recent tag. Did you create your branch from a release tag?"
    );
    return;
  } else {
    core.setOutput("tag", latestTag);
  }
};

run()
  .catch(error => {
    core.setFailed(error.message);
  });
