import os
import sys
import pickle
import time
import typing as t

import github
import pandas as pd
from github import Github, NamedUser, RateLimitExceededException, UnknownObjectException
from loguru import logger
from tqdm import tqdm

logger.remove()
logger.add(
    sys.stderr, format="<bold>{level:<10}</><green>{time}</> <yellow>{message}</>"
)


class DeveloperBase:
    def __init__(self, file_path: t.Union[None, os.PathLike] = None):
        self.developers = {}
        self.corrupted_user_names = []
        self.crawled_projects_for_contributors = set()
        self.crawled_projects_for_stargazers = set()
        self.crawled_projects_for_forkers = set()
        self.file_path = file_path

    def add(
        self,
        github_user: NamedUser.NamedUser,
        contributed_to: t.Set[str] = set(),
        forked: t.Set[str] = set(),
        stared: t.Set[str] = set(),
    ):
        """Add a GitHub User to the DeveloperBase.

        Args:
            github_user (NamedUser.NamedUser): GitHub user object.
            contributed_to (t.Set[str], optional): List of projects user has contributed
                to. Defaults to set().
            forked (t.Set[str], optional): List of projects user has forked. Defaults to
                set().
            stared (t.Set[str], optional): List of projects user stared. Defaults to
                set().
        """

        # check datatype
        assert (
            type(github_user) == NamedUser.NamedUser
        ), "`github_user` must be of type `github.NamedUser.NamedUser`!"
        assert type(contributed_to) == set, "`contributed_to` must be a set!"
        assert type(forked) == set, "`forked` must be a set!"
        assert type(stared) == set, "`stared` must be a set!"

        # key
        try:
            k = github_user.login

            # add entry in not there yet
            if k not in self.developers:
                self.developers[k] = {
                    "name": github_user.name,
                    "github_url": f"https://github.com/{k}",
                    "twitter_unsername": github_user.twitter_username,
                    "email": github_user.email,
                    "location": github_user.location,
                    "company": github_user.company,
                    "bio": github_user.bio,
                    "blog": github_user.blog,
                    "contributed_to": set(),
                    "stared": set(),
                    "forked": set(),
                }

            # add projects
            self.developers[k]["contributed_to"].update(contributed_to)
            self.developers[k]["forked"].update(forked)
            self.developers[k]["stared"].update(stared)
        except UnknownObjectException:
            self.corrupted_user_names.append(github_user.login)

    def get_all_projects(self) -> t.Set[str]:
        """Get all GitHub projects the DeveloperBase has crawled in some way (for
        contributors, stargazers or forkers).

        Returns:
            t.Set[str]: List of projects.
        """
        contributed_to = set()
        stared = set()
        forked = set()

        for k, v in self.developers.items():
            contributed_to.update(v["contributed_to"])
            stared.update(v["stared"])
            forked.update(v["forked"])

        return contributed_to.union(stared).union(forked)

    def save(self):
        """Serialize itself."""
        if self.file_path:
            with open(self.file_path, "wb") as f:
                pickle.dump(self, f)
            logger.info(f"Saved DeveloperBase to {self.file_path}")

    def __len__(self) -> int:
        """Length of the DeveloperBase.

        Returns:
            int: Length of the DeveloperBase.
        """
        return len(self.developers)

    def rank_developers(
        self,
        score_contributed: int = 5,
        score_forked: int = 2,
        score_stared: int = 1,
        exclude_miussing_email: bool = True,
    ) -> pd.DataFrame:
        """Rank all the developers in the DeveloperBase according to their interaction
        with the crawled GitHub Projects. The final score will be the some of the
        scores. You can weigh the different contributions to the overall score. Per
        default a developers gains 5 points for each project she contributed to, 2
        points for each projects that she forked and 1 point for each project that she
        stared.

        Args:
            score_contributed (int, optional): Score for each project the developer
                contributed to. Defaults to 5.
            score_forked (int, optional): Score for each forked project. Defaults to 2.
            score_stared (int, optional): Score for each stared project. Defaults to 1.
            exclude_miussing_email (bool, optional): Enable if you want to exclude the
                developer without the information of an email adress. Defaults to True.

        Returns:
            pd.DataFrame: DataBase of ranked developers.
        """
        df = pd.DataFrame.from_dict(self.developers, orient="index")
        n_before = len(df)
        if exclude_miussing_email:
            df = df[~pd.isna(df.email)]
            n_after = len(df)
            logger.info(
                f"DeveloperBase shrinked from {n_before} to {n_after} after removing developers without email adresses."
            )
        df["score"] = (
            score_contributed * df.contributed_to.str.len()
            + score_forked * df.forked.str.len()
            + score_stared * df.stared.str.len()
        )
        return df.sort_values(by="score", ascending=False)

    def print_status(self, n_remaining_projects: t.Union[None, int] = None):
        """Print the status of the current developer search.

        Args:
            n_remaining_projects (t.Union[None, int], optional): Number of projects left
            to be crawled. Defaults to None.
        """

        n1 = len(self.crawled_projects_for_contributors)
        n2 = len(self.crawled_projects_for_stargazers)
        n3 = len(self.crawled_projects_for_forkers)
        n4 = len(self.developers)

        logger.info("+{}+".format("-" * 45))
        logger.info(f"| Projects crawled for contributors: {n1:<8} |")
        logger.info(f"| Projects crawled for stargazers:   {n2:<8} |")
        logger.info(f"| Projects crawled for forkers:      {n3:<8} |")
        logger.info(f"| Developers found:                  {n4:<8} |")
        if n_remaining_projects is not None:
            logger.info(
                f"| Projects remaining:                {n_remaining_projects:<8} |"
            )
        logger.info("+{}+".format("-" * 45))

    def add_contributors(self, repo: github.Repository.Repository, dt: float = 0):
        """Add all the contributors of a certain repository.

        Args:
            repo (github.Repository.Repository): GitHub Repo object.
            dt (float): Waiting time between requests.
        """
        if repo.full_name in self.crawled_projects_for_contributors:
            logger.info(f"Skipping {repo.full_name} (already crawled for contributors)")
            return

        contributors = repo.get_contributors()

        for contributor in tqdm(contributors, total=contributors.totalCount):
            self.add(contributor, contributed_to={repo.full_name})
            time.sleep(dt)
        self.crawled_projects_for_contributors.add(repo.full_name)

    def add_stargazers(self, repo: github.Repository.Repository, dt: float = 0):
        """Add all the stargazers of a certain repository.

        Args:
            repo (github.Repository.Repository): GitHub Repo object.
            dt (float): Waiting time between requests.
        """

        if repo.full_name in self.crawled_projects_for_stargazers:
            logger.info(f"Skipping {repo.full_name} (already crawled for stargazers)")
            return

        stargazers = repo.get_stargazers()
        for stargazer in tqdm(stargazers, total=stargazers.totalCount):
            self.add(stargazer, stared={repo.full_name})
            time.sleep(dt)
        self.crawled_projects_for_stargazers.add(repo.full_name)

    def add_forkers(
        self, repo: github.Repository.Repository, dt: float = 0
    ) -> t.List[str]:
        """Add all the forkers for a given GitHub project.

        Args:
            repo (github.Repository.Repository): GitHub Repo object.
            dt (float): Waiting time between requests.

        Returns:
            t.List[str]: List of forked projects. Can be used for recursive search.
        """
        if repo.full_name in self.crawled_projects_for_forkers:
            logger.info(f"Skipping {repo.full_name} (already crawled for forkers)")
            return []

        forks = repo.get_forks()

        forked_projects = []
        for fork in tqdm(forks, total=forks.totalCount):
            forker = fork.owner
            self.add(forker, forked={repo.full_name})
            forked_projects.append(fork.full_name)
            time.sleep(dt)
        self.crawled_projects_for_forkers.add(repo.full_name)

        return forked_projects

    def find_developers(
        self,
        gh_token: str,
        projects: t.List[str],
        go_recursive: bool = False,
        ignore_contributors: bool = False,
        ignore_forkers: bool = False,
        ignore_stargazers: bool = False,
        ignore_rate_limiting: bool = False,
    ):
        """Find and add all the developers given a list of projects on GitHub.

        Args:
            gh_token (str): GitHub Access Token.
            projects (t.List[str]): List of Projects, e.g. `["mlflow/mlflow",
                "apache/airflow"]`
            go_recursive (bool, optional): Enable if you want recursivly also search
                through the forked repos. Be careful however, this might take a very
                long time. Defaults to False.
            ignore_contributors (bool, optional): Ignore contributors. Defaults to
                False.
            ignore_forkers (bool, optional): Ingore forkers. Defaults to False.
            ignore_stargazers (bool, optional): Ignore stargazers. Defaults to False.
            ignore_rate_limiting (bool, optional): If truned off the method takes of
                not running into a rate limiting issue. Defaults to False.
        """
        G = Github(gh_token)

        # rate limits
        if ignore_rate_limiting:
            dt = 0.0
        else:
            n_request_remaining, n_requests_total = G.rate_limiting
            logger.info(
                f"{n_requests_total} total requests per hour ({n_request_remaining} remaining)."
            )
            dt = 1.01 * n_requests_total / 3600
            if n_requests_total < 5000:
                logger.warning(
                    "It seems that you are requesting the GitHub API with an unauthenticated user."
                )

        # database
        projects = set(projects)

        while len(projects):

            try:
                # get repository
                project = projects.pop()
                repo = G.get_repo(project)

                # get contributors
                if not ignore_contributors:
                    logger.info(f"Crawling contributors from {project}...")
                    self.add_contributors(repo, dt=dt)
                    self.save()
                    self.print_status(n_remaining_projects=len(projects))
                    logger.info("")

                # get stargazers
                if not ignore_stargazers:
                    logger.info(f"Crawling stargazers from {project}...")
                    self.add_stargazers(repo, dt=dt)
                    self.save()
                    self.print_status(n_remaining_projects=len(projects))
                    logger.info("")

                # get forkers
                if not ignore_forkers:
                    logger.info(f"Crawling forkers from {project}")
                    forked_projects = self.add_forkers(repo, dt=dt)
                    self.save()
                    self.print_status(n_remaining_projects=len(projects))
                    logger.info("")

                # if you want to go recursive
                if go_recursive:
                    projects.update(forked_projects)

            except RateLimitExceededException:
                G = Github(gh_token)
                dt_wait = G.rate_limiting_resettime - int(time.time()) + 10
                logger.warning(
                    f"We ran into GitHub's rate Limit, which restes in {int(dt_wait/60)} minutes..."
                )
                projects.add(project)
                time.sleep(dt_wait)
