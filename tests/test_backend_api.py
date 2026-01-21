"""
Backend API Tests for ContentFlow - YouTube CC Content Discovery App
Tests: Auth (login, register, verify-email), Video Discovery, Stats, Clear Videos
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ccclipmaker.preview.emergentagent.com')

# Test credentials
TEST_USER_EMAIL = "testuser123@test.com"
TEST_USER_PASSWORD = "Test123456"


class TestHealthAndStats:
    """Test public endpoints - Stats API"""
    
    def test_stats_endpoint_returns_200(self):
        """Stats endpoint should return 200 and valid data structure"""
        response = requests.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "total_videos_discovered" in data
        assert "total_clips_generated" in data
        assert "total_posts_published" in data
        assert "top_videos" in data
        assert "recent_posts" in data
        print(f"✅ Stats: {data['total_videos_discovered']} videos, {data['total_clips_generated']} clips, {data['total_posts_published']} posts")


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_success(self):
        """Login with valid credentials should return token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == TEST_USER_EMAIL
        print(f"✅ Login successful for {data['user']['email']}")
        return data["access_token"]
    
    def test_login_invalid_password(self):
        """Login with wrong password should return 400"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": "WrongPassword123"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✅ Invalid password correctly rejected")
    
    def test_login_nonexistent_user(self):
        """Login with non-existent email should return 400"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "SomePassword123"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✅ Non-existent user correctly rejected")
    
    def test_register_duplicate_email(self):
        """Register with existing email should return 400"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_USER_EMAIL,
            "password": "NewPassword123",
            "full_name": "Duplicate User"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "already registered" in data.get("detail", "").lower()
        print("✅ Duplicate email registration correctly rejected")
    
    def test_verify_email_invalid_token(self):
        """Verify email with invalid token should return 400"""
        response = requests.get(f"{BASE_URL}/api/auth/verify-email?token=invalid_token_12345")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✅ Invalid verification token correctly rejected")
    
    def test_get_me_without_token(self):
        """Get /auth/me without token should return 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Unauthenticated /auth/me correctly rejected")
    
    def test_get_me_with_valid_token(self):
        """Get /auth/me with valid token should return user data"""
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        token = login_response.json()["access_token"]
        
        # Now get user info
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["email"] == TEST_USER_EMAIL
        print(f"✅ /auth/me returned user: {data['email']}")


class TestVideoDiscovery:
    """Test video discovery endpoints (requires authentication)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_discover_without_auth(self):
        """Discover endpoint without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/discover")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Unauthenticated discover correctly rejected")
    
    def test_discover_with_auth(self):
        """Discover endpoint with auth should return videos"""
        response = requests.get(
            f"{BASE_URL}/api/discover",
            params={"query": "music", "max_results": 5, "min_views": 1000},
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "videos" in data
        assert "total" in data
        print(f"✅ Discover returned {data['total']} videos")
        
        # Validate video structure if videos exist
        if data["videos"]:
            video = data["videos"][0]
            assert "id" in video
            assert "title" in video
            assert "viral_score" in video
            print(f"✅ First video: {video['title'][:50]}... (score: {video['viral_score']})")
    
    def test_discover_with_empty_query(self):
        """Discover with empty query should still work"""
        response = requests.get(
            f"{BASE_URL}/api/discover",
            params={"query": "", "max_results": 10},
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ Empty query discover works")


class TestClearVideos:
    """Test clear videos endpoint (requires authentication)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_clear_videos_without_auth(self):
        """Clear videos without auth should return 401"""
        response = requests.post(f"{BASE_URL}/api/clear-videos")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Unauthenticated clear-videos correctly rejected")
    
    def test_clear_videos_with_auth(self):
        """Clear videos with auth should succeed"""
        response = requests.post(
            f"{BASE_URL}/api/clear-videos",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True
        assert "deleted_count" in data
        print(f"✅ Clear videos succeeded: {data['deleted_count']} videos deleted")


class TestVideoDetails:
    """Test video details endpoint (requires authentication)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_video_details_without_auth(self):
        """Get video details without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/videos/dQw4w9WgXcQ")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Unauthenticated video details correctly rejected")


class TestClipGeneration:
    """Test clip generation endpoint (requires authentication)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_generate_clip_without_auth(self):
        """Generate clip without auth should return 401"""
        response = requests.post(f"{BASE_URL}/api/clips/generate", json={
            "video_id": "test123",
            "start_time": 0,
            "duration": 30
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Unauthenticated clip generation correctly rejected")


class TestHistory:
    """Test history endpoint (public)"""
    
    def test_get_history(self):
        """Get post history should return 200"""
        response = requests.get(f"{BASE_URL}/api/history")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "posts" in data
        assert "total" in data
        print(f"✅ History returned {data['total']} posts")


class TestSettings:
    """Test settings endpoints (public)"""
    
    def test_get_api_keys(self):
        """Get API keys should return 200 with masked keys"""
        response = requests.get(f"{BASE_URL}/api/settings/api-keys")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ Get API keys works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
