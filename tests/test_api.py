import os
import tempfile
import unittest

# 1. Create a temporary file for the database
temp_db_fd, temp_db_path = tempfile.mkstemp()

# 2. Patch db.DB_PATH before app is imported so app uses the temp db
from server import db
db.DB_PATH = temp_db_path

# 3. Import app. It will call db.init_db() on the temp db automatically.
from app import app

class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['PROPAGATE_EXCEPTIONS'] = True
        cls.app = app

    @classmethod
    def tearDownClass(cls):
        os.close(temp_db_fd)
        try:
            os.unlink(temp_db_path)
        except OSError:
            pass
        
    def setUp(self):
        self.client = self.app.test_client()

    def login(self, username, password):
        return self.client.post('/api/auth/login', json={
            "username": username,
            "password": password
        })

    # Auth endpoints
    def test_auth_login(self):
        resp = self.login("admin", "password123")
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertIn("user", data)
        self.assertEqual(data["user"]["username"], "admin")

    def test_auth_logout(self):
        self.login("admin", "password123")
        resp = self.client.post('/api/auth/logout')
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_auth_me(self):
        self.login("admin", "password123")
        resp = self.client.get('/api/auth/me')
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertEqual(data["username"], "admin")

    # Child endpoints
    def test_child_list(self):
        self.login("admin", "password123")
        resp = self.client.get('/api/children')
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_child_registration(self):
        self.login("admin", "password123")
        ccis_resp = self.client.get('/api/ccis')
        cci_id = ccis_resp.get_json()[0]['id']

        child_data = {
            "name": "Test Child",
            "gender": "Female",
            "date_of_birth": "2015-01-01",
            "admission_date": "2023-01-01",
            "cci_id": cci_id
        }
        resp = self.client.post('/api/children', json=child_data)
        self.assertEqual(resp.status_code, 201, resp.data)
        data = resp.get_json()
        self.assertIn("id", data)

        child_id = data["id"]
        resp_get = self.client.get(f'/api/children/{child_id}')
        self.assertEqual(resp_get.status_code, 200, resp_get.data)

    def test_child_status_update(self):
        self.login("admin", "password123")
        children = self.client.get('/api/children').get_json()
        child_id = children[0]['id']
        
        resp = self.client.put(f'/api/children/{child_id}/status', json={
            "legal_status": "adopted"
        })
        self.assertEqual(resp.status_code, 200, resp.data)
        
        resp_hist = self.client.get(f'/api/children/{child_id}/history')
        self.assertEqual(resp_hist.status_code, 200, resp_hist.data)
        hist = resp_hist.get_json()
        self.assertTrue(any('Legally Free for Adoption' in h.get('description', '') for h in hist))

    # Hearings endpoints
    def test_hearings_list(self):
        self.login("admin", "password123")
        resp = self.client.get('/api/hearings')
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertIsInstance(data, list)

    def test_hearings_schedule(self):
        self.login("admin", "password123")
        children = self.client.get('/api/children').get_json()
        child_id = children[0]['id']
        
        hearing_data = {
            "child_id": child_id,
            "hearing_date": "2024-01-01T10:00",
            "purpose": "First Review"
        }
        resp = self.client.post('/api/hearings', json=hearing_data)
        self.assertEqual(resp.status_code, 201, resp.data)
        data = resp.get_json()
        self.assertIn("id", data)

    # Orders endpoints
    def test_orders_generation(self):
        self.login("admin", "password123")
        children = self.client.get('/api/children').get_json()
        child_id = children[0]['id']

        hearings = self.client.get('/api/hearings').get_json()
        hearing_id = hearings[0]['id'] if hearings else None
        
        order_data = {
            "child_id": child_id,
            "hearing_id": hearing_id,
            "order_type": "restoration",
            "order_body": "Test order body",
            "order_date": "2024-01-01"
        }
        resp = self.client.post('/api/orders', json=order_data)
        self.assertEqual(resp.status_code, 201, resp.data)
        data = resp.get_json()
        self.assertIn("id", data)

    # Dashboards and Reports endpoints
    def test_dashboard_stats(self):
        self.login("admin", "password123")
        resp = self.client.get('/api/dashboard/stats')
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_dashboard_alerts(self):
        self.login("admin", "password123")
        resp = self.client.get('/api/dashboard/alerts')
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_reports_monthly(self):
        self.login("admin", "password123")
        resp = self.client.get('/api/reports/monthly?month=1&year=2024')
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertIn("admissions", data)

if __name__ == '__main__':
    unittest.main()
