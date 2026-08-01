from locust import HttpUser, task, between
import os


class PetstoreUser(HttpUser):
    """Locust user class generated from Petstore 1.0.0."""
    wait_time = between(1.0, 3.0)
    host = "https://petstore.example.com/v1"

    def on_start(self):
        self.headers = {
            "Authorization": f"Bearer {os.environ.get('BEARERAUTH_TOKEN', os.environ.get('API_TOKEN', ''))}"
        }
        self.headers = self.headers if hasattr(self, "headers") else {}
        self.headers["X-API-Key"] = os.environ.get('APIKEYAUTH_KEY', os.environ.get('API_KEY', ''))
        return self.headers

    @task(3)
    def list_pets(self):
        """List all pets"""
        resp = self.client.get("/pets", params={"limit": None, "status": None})

    @task(2)
    def create_pet(self):
        """Create a pet"""
        resp = self.client.post("/pets", json={'name': '<string>', 'tag': '<string>'})

    @task(3)
    def get_pet_by_id(self):
        """Get a pet by ID"""
        resp = self.client.get(f"/pets/{pet_id}")

    @task(1)
    def delete_pet(self):
        """Delete a pet"""
        resp = self.client.delete(f"/pets/{pet_id}")
