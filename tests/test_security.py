import pytest
from app.core.security import validate_public_url, UnsafeURLError

@pytest.mark.parametrize("url", ["ftp://example.com", "file:///etc/passwd", "localhost", "http://127.0.0.1", "http://10.0.0.5", "http://[::1]"])
def test_rejects_unsafe_urls(url):
    with pytest.raises(UnsafeURLError):
        validate_public_url(url)

def test_requires_http_scheme():
    with pytest.raises(UnsafeURLError):
        validate_public_url("example.com")
