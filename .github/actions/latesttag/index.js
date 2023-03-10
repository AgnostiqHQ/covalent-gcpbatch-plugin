const github = require("@actions/github");
const core = require("@actions/core");

// new action
(async()=>{

    const { owner ,repo } = github.context.repo

    const tokenInput = core.getInput("token");
    const branchInput = core.getInput("branch");
    const stableInput = core.getInput("stable");

    const octokit = github.getOctokit(tokenInput);
    
    let isStable = stableInput === "true"

    if(typeof stableInput !=='string' || !["true","false"].includes(stableInput)){
        throw new Error('There is an error in the stable input');
    }

    const { data: tags } = await octokit.rest.repos.listTags({
        owner: owner,
        repo: repo,
    });

    const SEMVER_RE = /^v?([0-9]+)\.([0-9]+)\.([0-9]+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+)?$/i;

    const latestTag = tags.find(({ name }) => {
        return tag.match(SEMVER_RE);
    })

    console.log('tags',tags)
    console.log('latest tag: ', latestTag)

})().catch(error => {
    core.setFailed(error.message);
});

// old commit
