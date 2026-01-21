"""
Backend API Tests for ContentFlow - Free Books Feature
Tests: Free Books endpoints, search, category filters
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ccclipmaker.preview.emergentagent.com')

# Test credentials
TEST_USER_EMAIL = "apitester@test.com"
TEST_USER_PASSWORD = "TestPass123!"


class TestFreeBooksAPI:
    """Test Free Books endpoints (requires authentication)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_free_books_without_auth(self):
        """Free books endpoint without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/content-library/free-books")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Unauthenticated free-books correctly rejected")
    
    def test_free_books_returns_books(self):
        """Free books endpoint should return list of books"""
        response = requests.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"limit": 10},
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "books" in data
        assert "total" in data
        assert "categories" in data
        assert "grades" in data
        assert len(data["books"]) > 0, "Expected at least one book"
        print(f"✅ Free books returned {len(data['books'])} books (total: {data['total']})")
        
        # Validate book structure
        book = data["books"][0]
        assert "id" in book
        assert "title" in book
        assert "author" in book
        assert "category" in book
        assert "grade_level" in book
        assert "formats" in book
        assert "license" in book
        print(f"✅ First book: {book['title']} by {book['author']}")
    
    def test_free_books_category_filter_stories(self):
        """Free books with category=stories should return only stories"""
        response = requests.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"category": "stories", "limit": 20},
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["books"]) > 0, "Expected at least one story"
        
        # Verify all books are stories
        for book in data["books"]:
            assert book["category"] == "stories", f"Expected stories, got {book['category']}"
        print(f"✅ Stories filter returned {len(data['books'])} books")
    
    def test_free_books_category_filter_poetry(self):
        """Free books with category=poetry should return only poetry"""
        response = requests.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"category": "poetry", "limit": 20},
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["books"]) > 0, "Expected at least one poetry book"
        
        for book in data["books"]:
            assert book["category"] == "poetry", f"Expected poetry, got {book['category']}"
        print(f"✅ Poetry filter returned {len(data['books'])} books")
    
    def test_free_books_category_filter_grammar(self):
        """Free books with category=grammar should return only grammar books"""
        response = requests.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"category": "grammar", "limit": 20},
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["books"]) > 0, "Expected at least one grammar book"
        
        for book in data["books"]:
            assert book["category"] == "grammar", f"Expected grammar, got {book['category']}"
        print(f"✅ Grammar filter returned {len(data['books'])} books")
    
    def test_free_books_category_filter_math(self):
        """Free books with category=math should return only math books"""
        response = requests.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"category": "math", "limit": 20},
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["books"]) > 0, "Expected at least one math book"
        
        for book in data["books"]:
            assert book["category"] == "math", f"Expected math, got {book['category']}"
        print(f"✅ Math filter returned {len(data['books'])} books")
    
    def test_free_books_category_filter_science(self):
        """Free books with category=science should return only science books"""
        response = requests.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"category": "science", "limit": 20},
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["books"]) > 0, "Expected at least one science book"
        
        for book in data["books"]:
            assert book["category"] == "science", f"Expected science, got {book['category']}"
        print(f"✅ Science filter returned {len(data['books'])} books")
    
    def test_free_books_search_without_auth(self):
        """Free books search without auth should return 401"""
        response = requests.get(
            f"{BASE_URL}/api/content-library/free-books/search",
            params={"query": "alice"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Unauthenticated free-books search correctly rejected")
    
    def test_free_books_search_by_title(self):
        """Free books search should find books by title"""
        response = requests.get(
            f"{BASE_URL}/api/content-library/free-books/search",
            params={"query": "alice"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "books" in data
        assert "total" in data
        assert "query" in data
        assert data["query"] == "alice"
        assert len(data["books"]) > 0, "Expected at least one result for 'alice'"
        
        # Verify search result contains 'alice' in title
        found_alice = False
        for book in data["books"]:
            if "alice" in book["title"].lower():
                found_alice = True
                break
        assert found_alice, "Expected to find 'Alice' in search results"
        print(f"✅ Search for 'alice' returned {len(data['books'])} books")
    
    def test_free_books_search_by_author(self):
        """Free books search should find books by author"""
        response = requests.get(
            f"{BASE_URL}/api/content-library/free-books/search",
            params={"query": "dickens"},
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["books"]) > 0, "Expected at least one result for 'dickens'"
        
        # Verify search result contains 'dickens' in author
        found_dickens = False
        for book in data["books"]:
            if "dickens" in book["author"].lower():
                found_dickens = True
                break
        assert found_dickens, "Expected to find 'Dickens' in search results"
        print(f"✅ Search for 'dickens' returned {len(data['books'])} books")
    
    def test_free_books_search_no_results(self):
        """Free books search with non-matching query should return empty"""
        response = requests.get(
            f"{BASE_URL}/api/content-library/free-books/search",
            params={"query": "xyznonexistent123"},
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 0, "Expected no results for non-matching query"
        assert len(data["books"]) == 0
        print("✅ Search for non-existent term returned 0 results")
    
    def test_free_books_book_structure(self):
        """Verify book data structure has all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"limit": 1},
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        book = data["books"][0]
        
        # Required fields
        required_fields = ["id", "title", "author", "category", "grade_level", "description", "formats", "license"]
        for field in required_fields:
            assert field in book, f"Missing required field: {field}"
        
        # Verify formats structure
        assert "pdf" in book["formats"] or "epub" in book["formats"] or "html" in book["formats"], \
            "Book should have at least one format"
        
        # Verify grade_level is a list
        assert isinstance(book["grade_level"], list), "grade_level should be a list"
        
        # Verify license is public-domain
        assert book["license"] == "public-domain", f"Expected public-domain license, got {book['license']}"
        
        print(f"✅ Book structure validated: {book['title']}")


class TestDiscoverVideos:
    """Test video discovery endpoint (requires authentication)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_discover_returns_cached_videos(self):
        """Discover endpoint should return cached videos"""
        response = requests.get(
            f"{BASE_URL}/api/discover",
            params={"query": "tutorial", "max_results": 10},
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "videos" in data
        assert "total" in data
        
        # May return cached results due to quota exceeded
        if data.get("cached"):
            print(f"✅ Discover returned {data['total']} cached videos (quota exceeded)")
        else:
            print(f"✅ Discover returned {data['total']} videos")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
