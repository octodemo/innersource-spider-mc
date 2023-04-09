#!/usr/bin/env python

import json
import os
from base64 import b64decode
from os.path import dirname, join

import github3
import repo_activity.score
from dotenv import load_dotenv

if __name__ == "__main__":

    # Load env variables from file
    dotenv_path = join(dirname(__file__), ".env")
    load_dotenv(dotenv_path)

    # Auth to GitHub.com
    ghe = os.getenv("GH_ENTERPRISE_URL", default="").strip()
    if ghe:
        gh = github3.github.GitHubEnterprise(ghe, token=os.getenv("GH_TOKEN"))
    else:
        gh = github3.login(token=os.getenv("GH_TOKEN"))

    # Set the topic
    topic = os.getenv("TOPIC")
    # Split topics by comma and strip each topic
    topics = [t.strip() for t in topic.split(',')]
    organization = os.getenv("ORGANIZATION")

    # Get all repos from organization
    repo_list = []
    # Set for repos that have already been added to all_repos
    repo_set = set()
    for topic in topics:
        search_string = "org:{} topic:{}".format(organization, topic)
        all_repos = gh.search_repositories(search_string)

        for repo in all_repos:
            if repo is not None and repo.repository.full_name not in repo_set:
                repo_set.add(repo.repository.full_name)
                print("{0}".format(repo.repository))

                innersource_repo = repo.as_dict()
                innersource_repo["_InnerSourceMetadata"] = {}

                # fetch innersource.json
                try:
                    content = repo.repository.file_contents("/innersource.json").content
                    metadata = json.loads(b64decode(content))

                    innersource_repo["_InnerSourceMetadata"] = metadata
                except github3.exceptions.NotFoundError:
                    # innersource.json not found in repository, but it's not required
                    pass

                # fetch repository participation
                participation = repo.repository.weekly_commit_count()
                innersource_repo["_InnerSourceMetadata"]["participation"] = participation[
                    "all"
                ]

                # fetch contributing guidelines
                try:
                    # if CONTRIBUTING.md exists in the repository, link to that instead of repo root
                    content = repo.repository.file_contents("/CONTRIBUTING.md").content
                    innersource_repo["_InnerSourceMetadata"][
                        "guidelines"
                    ] = "CONTRIBUTING.md"
                except github3.exceptions.NotFoundError:
                    # CONTRIBUTING.md not found in repository, but it's not required
                    pass

                # fetch repository topics
                repo_topics = repo.repository.topics()
                innersource_repo["_InnerSourceMetadata"]["topics"] = repo_topics.names

                # calculate score
                innersource_repo["score"] = repo_activity.score.calculate(innersource_repo)

                repo_list.append(innersource_repo)

    # Write each repository to a repos.json file
    with open("repos.json", "w") as f:
        json.dump(repo_list, f, indent=4)
