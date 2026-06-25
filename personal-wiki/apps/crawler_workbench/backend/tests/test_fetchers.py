import httpx
import pytest

from crawler_workbench.fetchers import fetcher_for
from crawler_workbench.fetchers.arxiv import ArxivFetcher
from crawler_workbench.fetchers.github import GitHubFetcher
from crawler_workbench.fetchers.rss import RssFetcher
from crawler_workbench.fetchers.web import WebFetcher


def client_for(status_code: int, text: str, headers: dict[str, str] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=text, headers=headers or {})

    return httpx.Client(transport=httpx.MockTransport(handler))


def recording_github_client() -> tuple[httpx.Client, list[str]]:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.path.endswith("/issues"):
            payload = (
                '[{"html_url":"https://github.com/o/r/issues/1","title":"Issue","state":"closed",'
                '"number":1,"labels":[{"name":"bug"}],"closed_at":"2024-01-01T00:00:00Z",'
                '"pull_request":null,"body":"fixed"},'
                '{"html_url":"https://github.com/o/r/pull/2","title":"PR From Issues","state":"closed",'
                '"number":2,"pull_request":{"url":"x"},"body":"ignore from issues"}]'
            )
            return httpx.Response(200, text=payload)
        if request.url.path.endswith("/pulls"):
            payload = (
                '[{"html_url":"https://github.com/o/r/pull/2","title":"PR","state":"closed",'
                '"number":2,"merged_at":"2024-01-02T00:00:00Z","pull_request":{"url":"x"},"body":"merged"}]'
            )
            return httpx.Response(200, text=payload)
        return httpx.Response(404, text="not found")

    return httpx.Client(transport=httpx.MockTransport(handler)), requests


def github_header_client() -> tuple[httpx.Client, list[str | None]]:
    authorizations: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        authorizations.append(request.headers.get("authorization"))
        payload = '[{"html_url":"https://github.com/o/r/issues/1","title":"Issue","state":"closed","body":"fixed"}]'
        return httpx.Response(200, text=payload)

    return httpx.Client(transport=httpx.MockTransport(handler)), authorizations


def test_web_fetcher_returns_markdownish_result():
    fetcher = WebFetcher(client=client_for(200, "<html><title>Doc</title><body><h1>Hello</h1></body></html>", {"etag": "abc"}))
    results = fetcher.fetch({"url": "https://example.com/doc", "name": "Doc"})
    assert len(results) == 1
    assert results[0].title == "Doc"
    assert "Hello" in results[0].content
    assert results[0].etag == "abc"


def test_web_fetcher_canonicalizes_url():
    fetcher = WebFetcher(client=client_for(200, "<html><title>Doc</title><body>Hello</body></html>"))
    results = fetcher.fetch({"url": "HTTPS://Example.COM:443/doc?utm_source=x&z=1#section", "name": "Doc"})
    assert results[0].canonical_url == "https://example.com/doc?z=1"


def test_rss_fetcher_returns_entries():
    rss = """<?xml version="1.0"?><rss><channel><title>Feed</title><item><title>One</title><link>https://example.com/1</link><description>Body</description></item></channel></rss>"""
    fetcher = RssFetcher(client=client_for(200, rss))
    results = fetcher.fetch({"url": "https://example.com/feed.xml", "name": "Feed"})
    assert [result.title for result in results] == ["One"]
    assert results[0].canonical_url == "https://example.com/1"


def test_rss_fetcher_canonicalizes_links_and_prefers_id_for_linkless_entries():
    rss = """<?xml version="1.0"?><rss><channel><title>Feed</title><item><title>Linked</title><link>HTTPS://Example.COM:443/1?utm_source=x&amp;z=1#frag</link><description>Body</description></item><item><title>Linkless</title><guid>HTTPS://Example.COM:443/guid?utm_medium=x&amp;a=1#frag</guid><description>Body</description></item></channel></rss>"""
    fetcher = RssFetcher(client=client_for(200, rss))
    results = fetcher.fetch({"url": "https://example.com/feed.xml", "name": "Feed"})
    assert [result.canonical_url for result in results] == [
        "https://example.com/1?z=1",
        "https://example.com/guid?a=1",
    ]


def test_github_fetcher_base_repo_requests_issues_and_pulls_without_duplicate_prs():
    client, requests = recording_github_client()
    fetcher = GitHubFetcher(client=client)
    results = fetcher.fetch({"url": "https://api.github.com/repos/o/r", "name": "Repo"})
    assert [result.title for result in results] == ["Issue", "PR"]
    assert results[0].metadata["github_kind"] == "issue"
    assert results[1].metadata["github_kind"] == "pull_request"
    assert requests == [
        "https://api.github.com/repos/o/r/issues?state=closed&per_page=100",
        "https://api.github.com/repos/o/r/pulls?state=closed&per_page=100",
    ]


def test_github_fetcher_base_repo_preserves_query_for_issues_and_pulls():
    client, requests = recording_github_client()
    fetcher = GitHubFetcher(client=client)

    fetcher.fetch({"url": "https://api.github.com/repos/o/r?sort=updated&direction=desc", "name": "Repo"})

    assert requests == [
        "https://api.github.com/repos/o/r/issues?sort=updated&direction=desc&state=closed&per_page=100",
        "https://api.github.com/repos/o/r/pulls?sort=updated&direction=desc&state=closed&per_page=100",
    ]


def test_github_fetcher_issues_endpoint_with_query_makes_one_preserved_query_request():
    client, requests = recording_github_client()
    fetcher = GitHubFetcher(client=client)
    results = fetcher.fetch({"url": "https://api.github.com/repos/o/r/issues?labels=bug", "name": "Issues"})
    assert [result.title for result in results] == ["Issue"]
    assert len(requests) == 1
    assert requests[0].startswith("https://api.github.com/repos/o/r/issues?")
    assert "labels=bug" in requests[0]
    assert "state=closed" in requests[0]
    assert "per_page=100" in requests[0]


def test_github_fetcher_pulls_endpoint_with_query_makes_one_preserved_query_request():
    client, requests = recording_github_client()
    fetcher = GitHubFetcher(client=client)
    results = fetcher.fetch({"url": "https://api.github.com/repos/o/r/pulls?state=closed", "name": "Pulls"})
    assert [result.title for result in results] == ["PR"]
    assert len(requests) == 1
    assert requests[0].startswith("https://api.github.com/repos/o/r/pulls?")
    assert "state=closed" in requests[0]
    assert "per_page=100" in requests[0]


def test_github_fetcher_canonicalizes_html_url():
    payload = '[{"html_url":"HTTPS://github.com:443/O/R/issues/1?utm_source=x#frag","title":"Issue","state":"closed","pull_request":null,"body":"fixed"}]'
    fetcher = GitHubFetcher(client=client_for(200, payload))
    results = fetcher.fetch({"url": "https://api.github.com/repos/o/r/issues", "name": "Repo"})
    assert results[0].canonical_url == "https://github.com/O/R/issues/1"


def test_github_fetcher_does_not_send_env_token_without_explicit_auth(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    client, authorizations = github_header_client()
    fetcher = GitHubFetcher(client=client)

    fetcher.fetch({"url": "https://api.github.com/repos/o/r/issues", "name": "Repo", "auth_required": False})

    assert authorizations == [None]


def test_github_fetcher_sends_env_token_for_explicit_github_api_auth(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    client, authorizations = github_header_client()
    fetcher = GitHubFetcher(client=client)

    fetcher.fetch(
        {
            "url": "https://api.github.com/repos/o/r/issues",
            "name": "Repo",
            "auth_required": True,
            "auth_method": "env_token",
            "auth_ref": "GITHUB_TOKEN",
        }
    )

    assert authorizations == ["Bearer secret-token"]


def test_github_fetcher_does_not_send_env_token_to_non_api_host(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    client, authorizations = github_header_client()
    fetcher = GitHubFetcher(client=client)

    fetcher.fetch(
        {
            "url": "https://example.com/repos/o/r/issues",
            "name": "Repo",
            "auth_required": True,
            "auth_method": "env_token",
            "auth_ref": "GITHUB_TOKEN",
        }
    )

    assert authorizations == [None]


def test_arxiv_fetcher_returns_papers():
    atom = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2401.00001v1</id><title>Paper Title</title><summary>Paper summary</summary><published>2024-01-01T00:00:00Z</published></entry></feed>"""
    fetcher = ArxivFetcher(client=client_for(200, atom))
    results = fetcher.fetch({"url": "http://export.arxiv.org/api/query?search_query=all:test", "name": "Papers"})
    assert results[0].title == "Paper Title"
    assert "Paper summary" in results[0].content


def test_arxiv_fetcher_canonicalizes_id_url():
    atom = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>HTTP://ARXIV.ORG:80/abs/2401.00001v1?utm_source=x#frag</id><title>Paper Title</title><summary>Paper summary</summary></entry></feed>"""
    fetcher = ArxivFetcher(client=client_for(200, atom))
    results = fetcher.fetch({"url": "http://export.arxiv.org/api/query?search_query=all:test", "name": "Papers"})
    assert results[0].canonical_url == "http://arxiv.org/abs/2401.00001v1"


class CloseTrackingClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize("fetcher_cls", [WebFetcher, RssFetcher, GitHubFetcher, ArxivFetcher])
def test_fetchers_do_not_close_injected_clients(fetcher_cls):
    client = CloseTrackingClient()
    fetcher = fetcher_cls(client=client)
    fetcher.close()
    assert client.closed is False


@pytest.mark.parametrize("fetcher_cls", [WebFetcher, RssFetcher, GitHubFetcher, ArxivFetcher])
def test_fetchers_close_owned_clients_and_support_context_manager(monkeypatch, fetcher_cls):
    clients: list[CloseTrackingClient] = []

    def build_client() -> CloseTrackingClient:
        client = CloseTrackingClient()
        clients.append(client)
        return client

    monkeypatch.setattr(httpx, "Client", build_client)
    with fetcher_cls() as fetcher:
        assert fetcher.client is clients[0]
    assert clients[0].closed is True


def test_registry_fetchers_are_closeable():
    fetcher = fetcher_for("web")
    fetcher.close()
