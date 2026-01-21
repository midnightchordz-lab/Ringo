"""
Test Pagination Feature for Content Library
Tests pagination for:
- /api/content-library/free-books
- /api/content-library/free-books/search
- /api/content-library/childrens-literature
- /api/content-library/search
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "pagination_test@example.com"
TEST_PASSWORD = "test123456"

class TestPaginationAPI:
    """Test pagination functionality across Content Library endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code} - {login_response.text}")
    
    # ==================== FREE BOOKS PAGINATION ====================
    
    def test_free_books_default_pagination(self):
        """Test free books endpoint returns pagination info with default params"""
        response = self.session.get(f"{BASE_URL}/api/content-library/free-books")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify pagination fields exist
        assert "books" in data, "Response should contain 'books' field"
        assert "total" in data, "Response should contain 'total' field"
        assert "page" in data, "Response should contain 'page' field"
        assert "per_page" in data, "Response should contain 'per_page' field"
        assert "total_pages" in data, "Response should contain 'total_pages' field"
        assert "has_next" in data, "Response should contain 'has_next' field"
        assert "has_prev" in data, "Response should contain 'has_prev' field"
        
        # Verify default values
        assert data["page"] == 1, "Default page should be 1"
        assert data["per_page"] == 50, "Default per_page should be 50"
        
        print(f"✅ Free books pagination: total={data['total']}, pages={data['total_pages']}, per_page={data['per_page']}")
    
    def test_free_books_page_1_has_50_items(self):
        """Test that page 1 returns up to 50 items"""
        response = self.session.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"page": 1, "per_page": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have 50 items on page 1 (since total is 62)
        assert len(data["books"]) == 50, f"Page 1 should have 50 books, got {len(data['books'])}"
        assert data["has_next"] == True, "Page 1 should have next page"
        assert data["has_prev"] == False, "Page 1 should not have previous page"
        
        print(f"✅ Page 1 has {len(data['books'])} books, has_next={data['has_next']}, has_prev={data['has_prev']}")
    
    def test_free_books_page_2_has_remaining_items(self):
        """Test that page 2 returns remaining items"""
        response = self.session.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"page": 2, "per_page": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Page 2 should have remaining items (62 - 50 = 12)
        expected_remaining = data["total"] - 50
        assert len(data["books"]) == expected_remaining, f"Page 2 should have {expected_remaining} books, got {len(data['books'])}"
        assert data["has_next"] == False, "Page 2 should not have next page (last page)"
        assert data["has_prev"] == True, "Page 2 should have previous page"
        
        print(f"✅ Page 2 has {len(data['books'])} books, has_next={data['has_next']}, has_prev={data['has_prev']}")
    
    def test_free_books_page_1_and_2_have_different_content(self):
        """Test that page 1 and page 2 return different books"""
        response1 = self.session.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"page": 1, "per_page": 50}
        )
        response2 = self.session.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"page": 2, "per_page": 50}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Get book IDs from both pages
        page1_ids = set(book["id"] for book in data1["books"])
        page2_ids = set(book["id"] for book in data2["books"])
        
        # Pages should have no overlapping books
        overlap = page1_ids.intersection(page2_ids)
        assert len(overlap) == 0, f"Pages should have different content, found overlap: {overlap}"
        
        print(f"✅ Page 1 and Page 2 have different content (no overlap)")
    
    def test_free_books_total_pages_calculation(self):
        """Test that total_pages is calculated correctly"""
        response = self.session.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"per_page": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Calculate expected total pages
        import math
        expected_pages = math.ceil(data["total"] / data["per_page"])
        
        assert data["total_pages"] == expected_pages, f"Expected {expected_pages} pages, got {data['total_pages']}"
        
        print(f"✅ Total pages calculation correct: {data['total']} items / {data['per_page']} per page = {data['total_pages']} pages")
    
    def test_free_books_custom_per_page(self):
        """Test pagination with custom per_page value"""
        response = self.session.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"page": 1, "per_page": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["books"]) == 10, f"Should return 10 books, got {len(data['books'])}"
        assert data["per_page"] == 10, "per_page should be 10"
        
        print(f"✅ Custom per_page=10 works correctly")
    
    def test_free_books_invalid_page_number(self):
        """Test that requesting a page beyond total returns empty books"""
        response = self.session.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"page": 100, "per_page": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty books array for page beyond total
        assert len(data["books"]) == 0, "Page beyond total should return empty books"
        
        print(f"✅ Page beyond total returns empty books array")
    
    # ==================== FREE BOOKS SEARCH PAGINATION ====================
    
    def test_free_books_search_pagination(self):
        """Test search endpoint returns pagination info"""
        response = self.session.get(
            f"{BASE_URL}/api/content-library/free-books/search",
            params={"query": "math", "page": 1, "per_page": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination fields
        assert "books" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data
        assert "has_next" in data
        assert "has_prev" in data
        assert "query" in data
        
        assert data["query"] == "math"
        
        print(f"✅ Search pagination works: found {data['total']} results for 'math'")
    
    # ==================== CHILDREN'S LITERATURE PAGINATION ====================
    
    def test_childrens_literature_pagination(self):
        """Test children's literature endpoint returns pagination info"""
        response = self.session.get(
            f"{BASE_URL}/api/content-library/childrens-literature",
            params={"page": 1, "per_page": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination fields
        assert "results" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data
        assert "has_next" in data
        assert "has_prev" in data
        
        print(f"✅ Children's literature pagination: total={data['total']}, pages={data['total_pages']}")
    
    # ==================== CONTENT LIBRARY SEARCH PAGINATION ====================
    
    def test_content_library_search_pagination(self):
        """Test general content library search returns pagination info"""
        response = self.session.get(
            f"{BASE_URL}/api/content-library/search",
            params={"query": "science", "page": 1, "per_page": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination fields
        assert "results" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data
        assert "has_next" in data
        assert "has_prev" in data
        
        print(f"✅ Content library search pagination: total={data['total']}, pages={data['total_pages']}")
    
    # ==================== EDGE CASES ====================
    
    def test_pagination_with_category_filter(self):
        """Test pagination works correctly with category filter"""
        response = self.session.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"category": "stories", "page": 1, "per_page": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned books should be in 'stories' category
        for book in data["books"]:
            assert book["category"] == "stories", f"Book {book['title']} should be in 'stories' category"
        
        # Total should reflect filtered count
        assert data["total"] <= 62, "Filtered total should be less than or equal to total books"
        
        print(f"✅ Pagination with category filter: {data['total']} stories found")
    
    def test_pagination_with_grade_filter(self):
        """Test pagination works correctly with grade filter"""
        response = self.session.get(
            f"{BASE_URL}/api/content-library/free-books",
            params={"grade": "elementary", "page": 1, "per_page": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned books should include 'elementary' grade level
        for book in data["books"]:
            assert "elementary" in book.get("grade_level", []), f"Book {book['title']} should include 'elementary' grade"
        
        print(f"✅ Pagination with grade filter: {data['total']} elementary books found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
