const github = require("@actions/github");
const core = require("@actions/core");

// new action
(async()=>{
    const tokenInput = core.getInput("token");
    const stableInput = core.getInput("stable");
    const legacyInput = core.getInput("legacy");

    let isStable = stableInput === "true"
    let isLegacy = legacyInput === "true"

    const { owner ,repo } = github.context.repo

    if(typeof stableInput !=='string' || !["true","false"].includes(stableInput)){
        throw new Error(`There is an error in the provided stable input: ${stableInput}`);
    }
    if(typeof legacyInput !=='string' || !["true","false"].includes(legacyInput)){
        throw new Error(`There is an error in the provided legacy input: ${legacyInput}`);
    }
    
    if(isLegacy){
        return legacyAction();
    }

    const octokit = github.getOctokit(tokenInput);

    if(typeof stableInput !=='string' || !["true","false"].includes(stableInput)){
        throw new Error('There is an error in the stable input');
    }

    const { data: tags } = await octokit.rest.repos.listTags({
        owner: owner,
        repo: repo,
    });

    console.log('Fetched Tags:', tags.map(({name})=>name));

    const SEMVER_RE = /^v?([0-9]+)\.([0-9]+)\.([0-9]+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+)?$/i;

    const latestTag = tags.find(({ name }) => {
        return name.match(SEMVER_RE) && !(tags[i].name.match("rc") && isStable)
    });

    if(!latestTag || !latestTag?.name){
        throw new Error("The action couldn't find a matching recent tag. Did you create your branch from a release tag?")
    }

    console.log('Latest Tag',latestTag)
    core.setOutput("tag", latestTag.name);

})().catch(error => {
    core.setFailed(error.message);
});

// old action

async function legacyAction() {
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
    const { data: tags } = await octokit.rest.repos.listTags({
      owner: owner,
      repo: repo,
    });
    const re = /\d+\.\d+\.\d+(-\d+)*?/;
    let latestTag, i;
    while (latestTag == null) {
      i = 0;
      while (i < tags.length && latestTag == null) {
        if (
          commit === tags[i].commit.sha &&
          (!tags[i].name.match("rc") || !stable) &&
          tags[i].name.match(re)
        )
          latestTag = tags[i].name;
        i++;
      }
      if (latestTag == null) {
        const { data: data } = await octokit.rest.repos.getCommit({
          owner: owner,
          repo: repo,
          ref: commit,
        });
        if (data.parents.length !== 1) {
          core.setFailed(
            "Branch history is not linear. Try squashing your commits."
          );
          return;
        } else {
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
