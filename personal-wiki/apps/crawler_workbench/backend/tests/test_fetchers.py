import httpx
import pytest

from crawler_workbench.fetchers import fetcher_for
from crawler_workbench.fetchers import web as web_module
from crawler_workbench.fetchers.arxiv import ArxivFetcher
from crawler_workbench.fetchers.base import ResilientHttpClient
from crawler_workbench.fetchers.github import GitHubFetcher
from crawler_workbench.fetchers.rss import RssFetcher
from crawler_workbench.fetchers.web import WebFetcher


def client_for(status_code: int, text: str, headers: dict[str, str] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=text, headers=headers or {})

    return httpx.Client(transport=httpx.MockTransport(handler))


def bytes_client_for(status_code: int, content: bytes, headers: dict[str, str] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=content, headers=headers or {})

    return httpx.Client(transport=httpx.MockTransport(handler))


def routing_client(routes: dict[str, httpx.Response]) -> tuple[httpx.Client, list[str]]:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requests.append(url)
        return routes.get(url, httpx.Response(404, text="not found"))

    return httpx.Client(transport=httpx.MockTransport(handler)), requests


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


def test_resilient_http_client_retries_non_github_connection_errors_without_env_proxy():
    calls: list[tuple[bool, str]] = []

    class Client:
        def __init__(self, trust_env=True):
            self.trust_env = trust_env

        def get(self, url, **kwargs):
            calls.append((self.trust_env, url))
            if self.trust_env:
                raise httpx.ConnectError("proxy failed")
            return httpx.Response(200, text="ok")

        def close(self):
            pass

    client = ResilientHttpClient(client_factory=Client)

    response = client.get("https://developer.nvidia.com/blog/feed/")

    assert response.status_code == 200
    assert calls == [
        (True, "https://developer.nvidia.com/blog/feed/"),
        (False, "https://developer.nvidia.com/blog/feed/"),
    ]


def test_resilient_http_client_defaults_to_follow_redirects():
    kwargs_seen = []

    class Client:
        def __init__(self, trust_env=True):
            self.trust_env = trust_env

        def get(self, url, **kwargs):
            kwargs_seen.append(kwargs)
            return httpx.Response(200, text="ok")

        def close(self):
            pass

    client = ResilientHttpClient(client_factory=Client)

    client.get("https://example.com/feed")

    assert kwargs_seen == [{"follow_redirects": True, "timeout": 60}]


def test_resilient_http_client_does_not_retry_github_without_env_proxy():
    calls: list[tuple[bool, str]] = []

    class Client:
        def __init__(self, trust_env=True):
            self.trust_env = trust_env

        def get(self, url, **kwargs):
            calls.append((self.trust_env, url))
            raise httpx.ConnectError("direct github blocked")

        def close(self):
            pass

    client = ResilientHttpClient(client_factory=Client)

    with pytest.raises(httpx.ConnectError):
        client.get("https://github.com/NVIDIA/nccl/releases.atom")

    assert calls == [(True, "https://github.com/NVIDIA/nccl/releases.atom")]


def test_resilient_http_client_retries_empty_non_github_5xx_without_env_proxy():
    calls: list[tuple[bool, str]] = []

    class Client:
        def __init__(self, trust_env=True):
            self.trust_env = trust_env

        def get(self, url, **kwargs):
            calls.append((self.trust_env, url))
            if self.trust_env:
                return httpx.Response(502, text="")
            return httpx.Response(200, text="ok")

        def close(self):
            pass

    client = ResilientHttpClient(client_factory=Client)

    response = client.get("http://export.arxiv.org/api/query?search_query=all:nccl")

    assert response.status_code == 200
    assert calls == [
        (True, "http://export.arxiv.org/api/query?search_query=all:nccl"),
        (False, "http://export.arxiv.org/api/query?search_query=all:nccl"),
    ]


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


@pytest.mark.parametrize(
    ("url", "headers"),
    [
        ("https://example.com/report", {"content-type": "application/pdf", "etag": "pdf-etag"}),
        ("https://example.com/report.pdf?download=1", {"content-type": "application/octet-stream"}),
    ],
)
def test_web_fetcher_extracts_pdf_text_and_attaches_original_bytes(monkeypatch, url, headers):
    pdf_bytes = b"%PDF-1.4\n<title>Not HTML</title>\n%%EOF"
    extracted_payloads = []

    def fake_extract_pdf_text(payload):
        extracted_payloads.append(payload)
        return "Extracted PDF text", None

    monkeypatch.setattr(web_module, "_extract_pdf_text", fake_extract_pdf_text, raising=False)
    fetcher = WebFetcher(client=bytes_client_for(200, pdf_bytes, headers))

    results = fetcher.fetch({"url": url, "name": "GPU Report"})

    assert extracted_payloads == [pdf_bytes]
    assert len(results) == 1
    assert results[0].title == "GPU Report"
    assert "Extracted PDF text" in results[0].content
    assert "<title>Not HTML</title>" not in results[0].content
    assert results[0].attachment_bytes == pdf_bytes
    assert results[0].attachment_extension == ".pdf"
    assert results[0].attachment_content_type == "application/pdf"
    assert results[0].etag == headers.get("etag")


def test_web_fetcher_records_pdf_text_extraction_errors(monkeypatch):
    pdf_bytes = b"%PDF-1.4\n%%EOF"

    def fake_extract_pdf_text(payload):
        return "", "pdftotext failed"

    monkeypatch.setattr(web_module, "_extract_pdf_text", fake_extract_pdf_text, raising=False)
    fetcher = WebFetcher(client=bytes_client_for(200, pdf_bytes, {"content-type": "application/pdf"}))

    results = fetcher.fetch({"url": "https://example.com/report.pdf", "name": "GPU Report"})

    assert results[0].attachment_bytes == pdf_bytes
    assert results[0].metadata["pdf_extract_error"] == "pdftotext failed"
    assert "PDF text extraction failed: pdftotext failed" in results[0].content


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


def test_rss_fetcher_filters_entries_by_keywords_before_fetching_articles():
    rss = """<?xml version="1.0"?><rss><channel><title>Feed</title><item><title>NCCL update</title><link>https://example.com/nccl</link><description>Collective communication</description></item><item><title>Unrelated</title><link>https://example.com/other</link><description>Storage news</description></item></channel></rss>"""
    client, requests = routing_client(
        {
            "https://example.com/feed.xml": httpx.Response(200, text=rss),
            "https://example.com/nccl": httpx.Response(200, text="<html><article>NCCL article body</article></html>"),
            "https://example.com/other": httpx.Response(200, text="<html><article>Other article body</article></html>"),
        }
    )
    fetcher = RssFetcher(client=client)

    results = fetcher.fetch(
        {
            "url": "https://example.com/feed.xml",
            "name": "Feed",
            "include_keywords": ["NCCL"],
            "fetch_article_body": True,
        }
    )

    assert [result.title for result in results] == ["NCCL update"]
    assert requests == ["https://example.com/feed.xml", "https://example.com/nccl"]


def test_rss_fetcher_limits_entries_after_keyword_filtering():
    rss = """<?xml version="1.0"?><rss><channel><title>Feed</title><item><title>NCCL one</title><link>https://example.com/1</link><description>NCCL</description></item><item><title>NCCL two</title><link>https://example.com/2</link><description>NCCL</description></item><item><title>NCCL three</title><link>https://example.com/3</link><description>NCCL</description></item></channel></rss>"""
    fetcher = RssFetcher(client=client_for(200, rss))

    results = fetcher.fetch({"url": "https://example.com/feed.xml", "name": "Feed", "include_keywords": ["NCCL"], "max_entries": 2})

    assert [result.title for result in results] == ["NCCL one", "NCCL two"]


def test_rss_fetcher_fetches_article_body_and_records_feed_metadata():
    rss = """<?xml version="1.0"?><rss><channel><title>Feed</title><item><title>One</title><link>https://example.com/1</link><guid>entry-1</guid><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate><description>RSS summary</description></item></channel></rss>"""
    client, _ = routing_client(
        {
            "https://example.com/feed.xml": httpx.Response(200, text=rss),
            "https://example.com/1": httpx.Response(
                200,
                text="<html><title>Article</title><body><nav>Nav</nav><article><h1>One</h1><p>NCCL article body</p></article></body></html>",
                headers={"content-type": "text/html; charset=utf-8", "last-modified": "Tue, 02 Jan 2024 00:00:00 GMT"},
            ),
        }
    )
    fetcher = RssFetcher(client=client)

    results = fetcher.fetch({"url": "https://example.com/feed.xml", "name": "Feed", "fetch_article_body": True})

    assert len(results) == 1
    assert "RSS Summary:" in results[0].content
    assert "RSS summary" in results[0].content
    assert "Article Body:" in results[0].content
    assert "NCCL article body" in results[0].content
    assert "Nav" not in results[0].content
    assert results[0].metadata["feed_url"] == "https://example.com/feed.xml"
    assert results[0].metadata["entry_url"] == "https://example.com/1"
    assert results[0].metadata["entry_id"] == "entry-1"
    assert results[0].metadata["published"] == "Mon, 01 Jan 2024 00:00:00 GMT"
    assert results[0].metadata["article_fetch_method"] == "http"
    assert results[0].metadata["article_fetch_status"] == 200
    assert results[0].metadata["article_content_type"] == "text/html; charset=utf-8"
    assert results[0].last_modified == "Tue, 02 Jan 2024 00:00:00 GMT"


def test_rss_fetcher_falls_back_to_summary_when_article_fetch_fails():
    rss = """<?xml version="1.0"?><rss><channel><title>Feed</title><item><title>One</title><link>https://example.com/1</link><description>RSS summary</description></item></channel></rss>"""
    client, _ = routing_client(
        {
            "https://example.com/feed.xml": httpx.Response(200, text=rss),
            "https://example.com/1": httpx.Response(503, text="unavailable"),
        }
    )
    fetcher = RssFetcher(client=client)

    results = fetcher.fetch({"url": "https://example.com/feed.xml", "name": "Feed", "fetch_article_body": True})

    assert "RSS summary" in results[0].content
    assert results[0].metadata["article_fetch_method"] == "summary"
    assert results[0].metadata["article_fetch_status"] == 503
    assert "article_fetch_error" in results[0].metadata


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
    def __init__(self, **kwargs) -> None:
        self.closed = False
        self.kwargs = kwargs

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

    def build_client(**kwargs) -> CloseTrackingClient:
        client = CloseTrackingClient(**kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(httpx, "Client", build_client)
    with fetcher_cls() as fetcher:
        assert fetcher.client is not clients[0]
    assert [client.kwargs for client in clients] == [{}, {"trust_env": False}]
    assert [client.closed for client in clients] == [True, True]


def test_registry_fetchers_are_closeable():
    fetcher = fetcher_for("web")
    fetcher.close()
