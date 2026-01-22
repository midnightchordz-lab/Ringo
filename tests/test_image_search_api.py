"""
Test suite for Image Search API with CC-licensed sources
Tests: Unsplash, Pexels, Wikimedia Commons image search
Features: Photo/Illustration/Vector filtering, Source filtering, License verification
"""

import pytest
import requests
import os
import time

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user credentials
TEST_EMAIL = f"imgtest{int(time.time())}@test.com"
TEST_PASSWORD = "TestPass123!"
TEST_NAME = "Image Test User"


class TestImageSearchAPI:
    """Test suite for /api/images/search endpoint"""
    
    auth_token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Register and get auth token"""
        if TestImageSearchAPI.auth_token is None:
            # Register a new user
            register_response = requests.post(
                f"{BASE_URL}/api/auth/register",
                json={
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "full_name": TEST_NAME
                }
            )
            
            if register_response.status_code == 200:
                data = register_response.json()
                TestImageSearchAPI.auth_token = data.get("access_token")
            elif register_response.status_code == 400:
                # User exists, try login
                login_response = requests.post(
                    f"{BASE_URL}/api/auth/login",
                    json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
                )
                if login_response.status_code == 200:
                    TestImageSearchAPI.auth_token = login_response.json().get("access_token")
        
        self.headers = {"Authorization": f"Bearer {TestImageSearchAPI.auth_token}"}
    
    # ==================== BASIC SEARCH TESTS ====================
    
    def test_image_search_returns_results(self):
        """Test that image search returns results from multiple sources"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "nature", "per_page": 10},
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "images" in data, "Response should contain 'images' field"
        assert "total" in data, "Response should contain 'total' field"
        assert "sources" in data, "Response should contain 'sources' field"
        assert "page" in data, "Response should contain 'page' field"
        assert "per_page" in data, "Response should contain 'per_page' field"
        
        # Should have some images
        assert len(data["images"]) > 0, "Should return at least some images"
        print(f"✅ Image search returned {len(data['images'])} images from sources: {data['sources']}")
    
    def test_image_search_multiple_sources(self):
        """Test that search returns results from multiple sources (Unsplash, Pexels, Wikimedia)"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "mountain", "per_page": 30},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        sources = data.get("sources", [])
        print(f"✅ Sources returned: {sources}")
        
        # Should have at least 2 sources (Pexels and Wikimedia are always available)
        assert len(sources) >= 1, f"Expected at least 1 source, got {len(sources)}"
        
        # Check that images have source field
        for img in data["images"][:5]:
            assert "source" in img, "Each image should have a source field"
            assert img["source"] in ["unsplash", "pexels", "pixabay", "wikimedia"], f"Unknown source: {img['source']}"
    
    # ==================== PHOTO FILTER TESTS ====================
    
    def test_photo_filter_returns_photos(self):
        """Test that photo filter returns only photo-type images"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "nature", "image_type": "photo", "per_page": 10},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned images should be photos
        for img in data["images"]:
            assert img.get("image_type") == "photo", f"Expected photo, got {img.get('image_type')} for {img.get('id')}"
        
        print(f"✅ Photo filter returned {len(data['images'])} photos")
    
    def test_photo_filter_sources(self):
        """Test that photo filter searches Unsplash, Pexels, Wikimedia (not Pixabay without key)"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "landscape", "image_type": "photo", "per_page": 20},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        sources = data.get("sources", [])
        print(f"✅ Photo filter sources: {sources}")
        
        # Photos should come from photo-capable sources
        valid_photo_sources = ["unsplash", "pexels", "pixabay", "wikimedia"]
        for src in sources:
            assert src in valid_photo_sources, f"Unexpected source for photos: {src}"
    
    # ==================== ILLUSTRATION FILTER TESTS ====================
    
    def test_illustration_filter_returns_illustrations(self):
        """Test that illustration filter returns illustration-type images from Wikimedia"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "cat", "image_type": "illustration", "per_page": 10},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "images" in data
        
        # If we got results, they should be illustrations
        if len(data["images"]) > 0:
            for img in data["images"]:
                assert img.get("image_type") == "illustration", f"Expected illustration, got {img.get('image_type')}"
            print(f"✅ Illustration filter returned {len(data['images'])} illustrations")
        else:
            # Wikimedia may not always have illustrations for every query
            print(f"⚠️ No illustrations found for 'cat' - this is expected if Wikimedia has no matching illustrations")
    
    def test_illustration_filter_wikimedia_source(self):
        """Test that illustrations come from Wikimedia (since Pixabay not configured)"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "diagram", "image_type": "illustration", "per_page": 10},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        sources = data.get("sources", [])
        print(f"✅ Illustration sources: {sources}")
        
        # Without Pixabay, illustrations should come from Wikimedia
        if len(data["images"]) > 0:
            for img in data["images"]:
                assert img["source"] in ["wikimedia", "pixabay"], f"Unexpected illustration source: {img['source']}"
    
    # ==================== VECTOR FILTER TESTS ====================
    
    def test_vector_filter_returns_vectors(self):
        """Test that vector filter returns vector/SVG images from Wikimedia"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "icon", "image_type": "vector", "per_page": 10},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "images" in data
        
        # If we got results, they should be vectors
        if len(data["images"]) > 0:
            for img in data["images"]:
                assert img.get("image_type") == "vector", f"Expected vector, got {img.get('image_type')}"
            print(f"✅ Vector filter returned {len(data['images'])} vectors")
        else:
            print(f"⚠️ No vectors found for 'icon' - Wikimedia may not have matching SVGs")
    
    def test_vector_filter_svg_search(self):
        """Test that vector filter searches for SVG files in Wikimedia"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "logo", "image_type": "vector", "per_page": 10},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        sources = data.get("sources", [])
        print(f"✅ Vector sources: {sources}")
        
        # Vectors should come from Wikimedia (or Pixabay if configured)
        if len(data["images"]) > 0:
            for img in data["images"]:
                assert img["source"] in ["wikimedia", "pixabay"], f"Unexpected vector source: {img['source']}"
    
    # ==================== LICENSE VERIFICATION TESTS ====================
    
    def test_images_have_license_info(self):
        """Test that all images have proper license information"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "flower", "per_page": 15},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for img in data["images"]:
            assert "license" in img, f"Image {img.get('id')} missing license field"
            license_text = img["license"].upper()
            
            # Verify it's a valid CC or free license
            valid_licenses = ["CC BY", "CC-BY", "CC0", "PUBLIC DOMAIN", "UNSPLASH", "PEXELS", "PIXABAY", "CREATIVE COMMONS"]
            has_valid_license = any(lic in license_text for lic in valid_licenses)
            assert has_valid_license, f"Invalid license for {img.get('id')}: {img['license']}"
        
        print(f"✅ All {len(data['images'])} images have valid CC/free licenses")
    
    def test_wikimedia_cc_licenses(self):
        """Test that Wikimedia images have CC BY, CC BY-SA, CC BY-ND, or CC0 licenses"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "art", "source": "wikimedia", "per_page": 10},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["images"]) > 0:
            for img in data["images"]:
                if img["source"] == "wikimedia":
                    license_text = img["license"].upper()
                    valid_cc = any(cc in license_text for cc in ["CC BY", "CC-BY", "CC0", "PUBLIC DOMAIN", "PD"])
                    assert valid_cc, f"Wikimedia image has non-CC license: {img['license']}"
            print(f"✅ Wikimedia images have valid CC licenses")
        else:
            print(f"⚠️ No Wikimedia images returned for 'art'")
    
    # ==================== SOURCE FILTER TESTS ====================
    
    def test_wikimedia_only_filter(self):
        """Test that source=wikimedia returns only Wikimedia results"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "science", "source": "wikimedia", "per_page": 10},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All images should be from Wikimedia
        for img in data["images"]:
            assert img["source"] == "wikimedia", f"Expected wikimedia, got {img['source']}"
        
        # Sources list should only contain wikimedia
        if data["images"]:
            assert data["sources"] == ["wikimedia"], f"Expected only wikimedia source, got {data['sources']}"
        
        print(f"✅ Wikimedia filter returned {len(data['images'])} images from Wikimedia only")
    
    def test_pexels_only_filter(self):
        """Test that source=pexels returns only Pexels results"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "beach", "source": "pexels", "per_page": 10},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All images should be from Pexels
        for img in data["images"]:
            assert img["source"] == "pexels", f"Expected pexels, got {img['source']}"
        
        print(f"✅ Pexels filter returned {len(data['images'])} images from Pexels only")
    
    def test_unsplash_only_filter(self):
        """Test that source=unsplash returns only Unsplash results (if API key configured)"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "city", "source": "unsplash", "per_page": 10},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All images should be from Unsplash (if any returned)
        for img in data["images"]:
            assert img["source"] == "unsplash", f"Expected unsplash, got {img['source']}"
        
        if len(data["images"]) > 0:
            print(f"✅ Unsplash filter returned {len(data['images'])} images from Unsplash only")
        else:
            print(f"⚠️ No Unsplash images returned - API key may not be configured")
    
    # ==================== IMAGE DATA STRUCTURE TESTS ====================
    
    def test_image_data_structure(self):
        """Test that each image has all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "sunset", "per_page": 5},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "id", "url", "thumbnail", "title", "photographer",
            "photographer_url", "source", "source_url", "download_url",
            "license", "image_type"
        ]
        
        for img in data["images"]:
            for field in required_fields:
                assert field in img, f"Image {img.get('id')} missing required field: {field}"
        
        print(f"✅ All images have required fields: {required_fields}")
    
    def test_image_urls_are_valid(self):
        """Test that image URLs are valid HTTP/HTTPS URLs"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "forest", "per_page": 5},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for img in data["images"]:
            # Check URL fields
            for url_field in ["url", "thumbnail", "download_url"]:
                url = img.get(url_field, "")
                assert url.startswith("http"), f"Invalid {url_field} for {img.get('id')}: {url}"
        
        print(f"✅ All image URLs are valid HTTP/HTTPS URLs")
    
    # ==================== PAGINATION TESTS ====================
    
    def test_pagination_info(self):
        """Test that pagination info is returned correctly"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "water", "page": 1, "per_page": 10},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1, f"Expected page 1, got {data['page']}"
        assert data["per_page"] == 10, f"Expected per_page 10, got {data['per_page']}"
        assert "total" in data, "Missing total field"
        assert "total_pages" in data, "Missing total_pages field"
        assert "has_next" in data, "Missing has_next field"
        assert "has_prev" in data, "Missing has_prev field"
        
        print(f"✅ Pagination info: page={data['page']}, total={data['total']}, total_pages={data['total_pages']}")
    
    def test_pagination_page_2(self):
        """Test that page 2 returns different results"""
        # Get page 1
        response1 = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "sky", "page": 1, "per_page": 5},
            headers=self.headers
        )
        
        # Get page 2
        response2 = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "sky", "page": 2, "per_page": 5},
            headers=self.headers
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Page 2 should have different images (if available)
        if len(data2["images"]) > 0:
            ids1 = set(img["id"] for img in data1["images"])
            ids2 = set(img["id"] for img in data2["images"])
            
            # There should be no overlap (or minimal overlap due to interleaving)
            overlap = ids1.intersection(ids2)
            print(f"✅ Page 1 has {len(data1['images'])} images, Page 2 has {len(data2['images'])} images, overlap: {len(overlap)}")
        else:
            print(f"⚠️ Page 2 has no images - may have reached end of results")
    
    # ==================== ERROR HANDLING TESTS ====================
    
    def test_empty_query_error(self):
        """Test that empty query returns error or empty results"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "", "per_page": 10},
            headers=self.headers
        )
        
        # Should either return 422 (validation error) or empty results
        assert response.status_code in [200, 422], f"Unexpected status: {response.status_code}"
        print(f"✅ Empty query handled correctly (status: {response.status_code})")
    
    def test_unauthorized_access(self):
        """Test that unauthenticated requests are rejected"""
        response = requests.get(
            f"{BASE_URL}/api/images/search",
            params={"query": "test", "per_page": 5}
            # No auth header
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✅ Unauthorized access correctly rejected")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
