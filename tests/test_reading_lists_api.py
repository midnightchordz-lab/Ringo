"""
Reading Lists API Tests
Tests for CRUD operations on reading lists feature:
- POST /api/reading-lists - Create reading list
- GET /api/reading-lists - Get user's reading lists
- GET /api/reading-lists/{id} - Get specific reading list
- PUT /api/reading-lists/{id} - Update reading list
- DELETE /api/reading-lists/{id} - Delete reading list
- POST /api/reading-lists/{id}/books - Add book to list
- DELETE /api/reading-lists/{id}/books/{book_id} - Remove book from list
- POST /api/reading-lists/{id}/copy - Copy a reading list
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "apitester@test.com"
TEST_PASSWORD = "TestPass123!"


class TestReadingListsAuth:
    """Test authentication for reading lists"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_login_success(self):
        """Test login with test credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print(f"SUCCESS: Login successful for {TEST_EMAIL}")


class TestReadingListsCRUD:
    """Test CRUD operations for reading lists"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_reading_lists(self, auth_headers):
        """Test GET /api/reading-lists - Get user's reading lists"""
        response = requests.get(
            f"{BASE_URL}/api/reading-lists",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "reading_lists" in data
        assert "total" in data
        assert isinstance(data["reading_lists"], list)
        print(f"SUCCESS: Got {data['total']} reading lists")
    
    def test_get_reading_lists_with_public(self, auth_headers):
        """Test GET /api/reading-lists?include_public=true"""
        response = requests.get(
            f"{BASE_URL}/api/reading-lists",
            headers=auth_headers,
            params={"include_public": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert "reading_lists" in data
        print(f"SUCCESS: Got {data['total']} reading lists (including public)")
    
    def test_create_reading_list(self, auth_headers):
        """Test POST /api/reading-lists - Create a new reading list"""
        unique_name = f"TEST_List_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": unique_name,
            "description": "Test reading list for automated testing",
            "grade_level": "elementary",
            "subject": "stories",
            "is_public": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/reading-lists",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert "reading_list" in data
        assert data["reading_list"]["name"] == unique_name
        assert data["reading_list"]["grade_level"] == "elementary"
        assert data["reading_list"]["subject"] == "stories"
        assert data["reading_list"]["is_public"] == False
        assert data["reading_list"]["book_count"] == 0
        assert "id" in data["reading_list"]
        
        # Store for cleanup
        TestReadingListsCRUD.created_list_id = data["reading_list"]["id"]
        print(f"SUCCESS: Created reading list '{unique_name}' with ID: {data['reading_list']['id']}")
        return data["reading_list"]["id"]
    
    def test_get_specific_reading_list(self, auth_headers):
        """Test GET /api/reading-lists/{id} - Get specific reading list"""
        # Use the existing test list ID
        list_id = "7177d627-a1fe-4bee-ab50-e30a88f01bb7"
        
        response = requests.get(
            f"{BASE_URL}/api/reading-lists/{list_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "reading_list" in data
        assert data["reading_list"]["id"] == list_id
        assert data["reading_list"]["name"] == "Grade 3 Stories"
        print(f"SUCCESS: Got reading list '{data['reading_list']['name']}'")
    
    def test_update_reading_list(self, auth_headers):
        """Test PUT /api/reading-lists/{id} - Update reading list"""
        # First create a list to update
        unique_name = f"TEST_Update_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/reading-lists",
            headers=auth_headers,
            json={"name": unique_name, "description": "Original description"}
        )
        assert create_response.status_code == 200
        list_id = create_response.json()["reading_list"]["id"]
        
        # Update the list
        update_payload = {
            "name": f"{unique_name}_Updated",
            "description": "Updated description",
            "grade_level": "middle",
            "is_public": True
        }
        
        response = requests.put(
            f"{BASE_URL}/api/reading-lists/{list_id}",
            headers=auth_headers,
            json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["reading_list"]["name"] == f"{unique_name}_Updated"
        assert data["reading_list"]["description"] == "Updated description"
        assert data["reading_list"]["grade_level"] == "middle"
        assert data["reading_list"]["is_public"] == True
        
        # Cleanup - delete the test list
        requests.delete(f"{BASE_URL}/api/reading-lists/{list_id}", headers=auth_headers)
        print(f"SUCCESS: Updated reading list '{list_id}'")
    
    def test_delete_reading_list(self, auth_headers):
        """Test DELETE /api/reading-lists/{id} - Delete reading list"""
        # First create a list to delete
        unique_name = f"TEST_Delete_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/reading-lists",
            headers=auth_headers,
            json={"name": unique_name}
        )
        assert create_response.status_code == 200
        list_id = create_response.json()["reading_list"]["id"]
        
        # Delete the list
        response = requests.delete(
            f"{BASE_URL}/api/reading-lists/{list_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Reading list deleted"
        
        # Verify deletion
        get_response = requests.get(
            f"{BASE_URL}/api/reading-lists/{list_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
        print(f"SUCCESS: Deleted reading list '{list_id}'")


class TestReadingListBooks:
    """Test adding/removing books from reading lists"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_list(self, auth_headers):
        """Create a test list for book operations"""
        unique_name = f"TEST_Books_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/reading-lists",
            headers=auth_headers,
            json={"name": unique_name, "description": "Test list for book operations"}
        )
        assert response.status_code == 200
        list_data = response.json()["reading_list"]
        yield list_data
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reading-lists/{list_data['id']}", headers=auth_headers)
    
    def test_add_book_to_list(self, auth_headers, test_list):
        """Test POST /api/reading-lists/{id}/books - Add book to list"""
        book_payload = {
            "book_id": f"test-book-{uuid.uuid4().hex[:8]}",
            "title": "Test Book Title",
            "author": "Test Author",
            "category": "stories",
            "cover": "https://example.com/cover.jpg",
            "formats": {"pdf": "https://example.com/book.pdf"}
        }
        
        response = requests.post(
            f"{BASE_URL}/api/reading-lists/{test_list['id']}/books",
            headers=auth_headers,
            json=book_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert "book" in data
        assert data["book"]["title"] == "Test Book Title"
        assert data["book"]["author"] == "Test Author"
        
        # Verify book was added
        get_response = requests.get(
            f"{BASE_URL}/api/reading-lists/{test_list['id']}",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        list_data = get_response.json()["reading_list"]
        assert list_data["book_count"] == 1
        assert len(list_data["books"]) == 1
        print(f"SUCCESS: Added book to reading list")
    
    def test_add_duplicate_book_fails(self, auth_headers, test_list):
        """Test that adding duplicate book returns 400"""
        # Get the existing book from the list
        get_response = requests.get(
            f"{BASE_URL}/api/reading-lists/{test_list['id']}",
            headers=auth_headers
        )
        if get_response.status_code == 200:
            list_data = get_response.json()["reading_list"]
            if list_data.get("books"):
                existing_book = list_data["books"][0]
                
                # Try to add the same book again
                book_payload = {
                    "book_id": existing_book["book_id"],
                    "title": existing_book["title"],
                    "author": existing_book["author"],
                    "category": existing_book["category"]
                }
                
                response = requests.post(
                    f"{BASE_URL}/api/reading-lists/{test_list['id']}/books",
                    headers=auth_headers,
                    json=book_payload
                )
                assert response.status_code == 400
                print("SUCCESS: Duplicate book correctly rejected")
    
    def test_remove_book_from_list(self, auth_headers, test_list):
        """Test DELETE /api/reading-lists/{id}/books/{book_id} - Remove book from list"""
        # First add a book to remove
        book_id = f"test-remove-{uuid.uuid4().hex[:8]}"
        book_payload = {
            "book_id": book_id,
            "title": "Book to Remove",
            "author": "Test Author",
            "category": "stories"
        }
        
        add_response = requests.post(
            f"{BASE_URL}/api/reading-lists/{test_list['id']}/books",
            headers=auth_headers,
            json=book_payload
        )
        assert add_response.status_code == 200
        
        # Now remove the book
        response = requests.delete(
            f"{BASE_URL}/api/reading-lists/{test_list['id']}/books/{book_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Book removed from reading list"
        print(f"SUCCESS: Removed book from reading list")


class TestReadingListCopy:
    """Test copying reading lists"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_copy_reading_list(self, auth_headers):
        """Test POST /api/reading-lists/{id}/copy - Copy a reading list"""
        # Use the existing test list
        list_id = "7177d627-a1fe-4bee-ab50-e30a88f01bb7"
        
        response = requests.post(
            f"{BASE_URL}/api/reading-lists/{list_id}/copy",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "reading_list" in data
        assert "(Copy)" in data["reading_list"]["name"]
        assert data["reading_list"]["is_public"] == False  # Copies start as private
        assert data["reading_list"]["copied_from"] == list_id
        
        # Cleanup - delete the copied list
        copied_id = data["reading_list"]["id"]
        requests.delete(f"{BASE_URL}/api/reading-lists/{copied_id}", headers=auth_headers)
        print(f"SUCCESS: Copied reading list, new ID: {copied_id}")


class TestReadingListValidation:
    """Test validation and error handling"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_create_list_without_name_fails(self, auth_headers):
        """Test that creating list without name fails"""
        response = requests.post(
            f"{BASE_URL}/api/reading-lists",
            headers=auth_headers,
            json={"description": "No name provided"}
        )
        assert response.status_code == 422  # Validation error
        print("SUCCESS: Creating list without name correctly rejected")
    
    def test_get_nonexistent_list_returns_404(self, auth_headers):
        """Test that getting nonexistent list returns 404"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/reading-lists/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("SUCCESS: Nonexistent list correctly returns 404")
    
    def test_unauthorized_access_fails(self):
        """Test that accessing without auth fails"""
        response = requests.get(f"{BASE_URL}/api/reading-lists")
        assert response.status_code == 401
        print("SUCCESS: Unauthorized access correctly rejected")


class TestExistingReadingList:
    """Test the existing 'Grade 3 Stories' reading list"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_existing_grade3_stories_list(self, auth_headers):
        """Test the existing 'Grade 3 Stories' list has correct data"""
        list_id = "7177d627-a1fe-4bee-ab50-e30a88f01bb7"
        
        response = requests.get(
            f"{BASE_URL}/api/reading-lists/{list_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        reading_list = data["reading_list"]
        
        # Verify list properties
        assert reading_list["name"] == "Grade 3 Stories"
        assert reading_list["grade_level"] == "elementary"
        assert reading_list["subject"] == "stories"
        
        # Verify it has the Alice book
        assert reading_list["book_count"] >= 1
        assert len(reading_list["books"]) >= 1
        
        # Check for Alice's Adventures in Wonderland
        alice_book = next(
            (b for b in reading_list["books"] if b["book_id"] == "gutenberg-11"),
            None
        )
        assert alice_book is not None, "Alice's Adventures in Wonderland should be in the list"
        assert "Alice" in alice_book["title"]
        
        print(f"SUCCESS: Verified 'Grade 3 Stories' list with {reading_list['book_count']} book(s)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
