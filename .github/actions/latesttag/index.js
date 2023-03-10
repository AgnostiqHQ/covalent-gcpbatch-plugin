const github = require("@actions/github");
const core = require("@actions/core");

// new action
(async()=>{

    const { owner ,repo } = github.context.repo

    const tokenInput = core.getInput("token");
    const branchInput = core.getInput("branch");
    const stableInput = core.getInput("stable");

    const octokit = github.getOctokit(tokenInput);
    
    let isStable

    if(typeof stableInput !=='string' || !["true","false"].includes(stableInput)){
        throw new Error('There is an error in the stable input');
    }
    else {
       isStable = stableInput === "true"
    }

    const response = await octokit.rest.repos.listTags({
        owner: owner,
        repo: repo,
    });

    console.log('tags response',response)
})().catch(error => {
    core.setFailed(error.message);
});

// old commit
