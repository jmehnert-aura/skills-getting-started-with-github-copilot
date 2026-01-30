"""
Test suite for Mergington High School Activities API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Reset participants for all activities
    activities["Soccer Team"]["participants"] = []
    activities["Basketball Club"]["participants"] = []
    activities["Drama Club"]["participants"] = []
    activities["Art Workshop"]["participants"] = []
    activities["Math Olympiad"]["participants"] = []
    activities["Science Club"]["participants"] = []
    activities["Chess Club"]["participants"] = ["michael@mergington.edu", "daniel@mergington.edu"]
    activities["Programming Class"]["participants"] = ["emma@mergington.edu", "sophia@mergington.edu"]
    activities["Gym Class"]["participants"] = ["john@mergington.edu", "olivia@mergington.edu"]
    yield


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_index(self, client):
        """Test that root path redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all available activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Soccer Team" in data
        assert "Basketball Club" in data
        assert "Chess Club" in data
        
    def test_activities_have_required_fields(self, client):
        """Test that each activity has all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
            
    def test_chess_club_has_initial_participants(self, client):
        """Test that Chess Club has pre-registered participants"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert len(chess_club["participants"]) == 2
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Soccer%20Team/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Soccer Team"]["participants"]
        
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
        
    def test_signup_duplicate_participant(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        # First signup
        response1 = client.post(
            "/activities/Drama%20Club/signup?email=test@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Second signup (should fail)
        response2 = client.post(
            "/activities/Drama%20Club/signup?email=test@mergington.edu"
        )
        assert response2.status_code == 400
        
        data = response2.json()
        assert data["detail"] == "Student already signed up for this activity"
        
    def test_signup_multiple_students(self, client):
        """Test multiple students signing up for the same activity"""
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(
                f"/activities/Basketball%20Club/signup?email={email}"
            )
            assert response.status_code == 200
            
        # Verify all participants were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        basketball_participants = activities_data["Basketball Club"]["participants"]
        
        assert len(basketball_participants) == 3
        for email in emails:
            assert email in basketball_participants


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_successful(self, client):
        """Test successful unregistration from an activity"""
        # First, sign up
        client.post("/activities/Art%20Workshop/signup?email=test@mergington.edu")
        
        # Then unregister
        response = client.delete(
            "/activities/Art%20Workshop/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Art Workshop" in data["message"]
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" not in activities_data["Art Workshop"]["participants"]
        
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistering from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
        
    def test_unregister_participant_not_registered(self, client):
        """Test unregistering a participant who is not registered"""
        response = client.delete(
            "/activities/Math%20Olympiad/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert data["detail"] == "Student not registered for this activity"
        
    def test_unregister_pre_registered_participant(self, client):
        """Test unregistering a participant who was pre-registered"""
        # Chess Club has pre-registered participants
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        chess_participants = activities_data["Chess Club"]["participants"]
        
        assert "michael@mergington.edu" not in chess_participants
        assert "daniel@mergington.edu" in chess_participants  # Other participant still there


class TestIntegrationScenarios:
    """Integration tests for complex scenarios"""
    
    def test_signup_and_unregister_flow(self, client):
        """Test complete flow of signing up and unregistering"""
        email = "integration@mergington.edu"
        activity = "Science Club"
        
        # Initial state: verify not registered
        response = client.get("/activities")
        initial_participants = response.json()[activity]["participants"]
        assert email not in initial_participants
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity.replace(' ', '%20')}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify registered
        response = client.get("/activities")
        after_signup = response.json()[activity]["participants"]
        assert email in after_signup
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity.replace(' ', '%20')}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistered
        response = client.get("/activities")
        after_unregister = response.json()[activity]["participants"]
        assert email not in after_unregister
        
    def test_multiple_activities_per_student(self, client):
        """Test that a student can sign up for multiple activities"""
        email = "multitask@mergington.edu"
        activities_list = ["Soccer Team", "Drama Club", "Programming Class"]
        
        for activity in activities_list:
            response = client.post(
                f"/activities/{activity.replace(' ', '%20')}/signup?email={email}"
            )
            assert response.status_code == 200
            
        # Verify student is in all activities
        response = client.get("/activities")
        all_activities = response.json()
        
        for activity in activities_list:
            assert email in all_activities[activity]["participants"]
